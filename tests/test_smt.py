# ruff: noqa: Q000

import z3

from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse
from omni_compiler.smt import render_counterexample, verify_contracts


def _verify(code):
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    return verify_contracts(ast, symbol_table)


def test_provable_require_ensure():
    code = """
fn add(a: Number, b: Number) -> Number:
    require a is 2
    require b is 3
    ensure result is 5
    return a + b
end
"""
    results = _verify(code)
    assert len(results) == 1
    result = results[0]
    assert result['function'] == 'add'
    assert result['status'] == 'verified'
    assert result['counterexample'] is None
    assert result['reason'] is None
    assert result['require'] == 'a is 2 and b is 3'
    assert result['ensure'] == 'result is 5'


def test_failed_with_counterexample():
    code = """
fn bad(a: Number, b: Number) -> Number:
    require a is 5
    require b is 3
    ensure result is 10
    return a + b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    counterexample = result['counterexample']
    assert counterexample == {'a': 5, 'b': 3, 'result': 8}
    for value in counterexample.values():
        assert isinstance(value, int)


def test_only_ensure_holds():
    code = """
fn inc(a: Number) -> Number:
    ensure result is a + 1
    return a + 1
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_require_only_no_contracts():
    code = """
fn guarded(a: Number) -> Number:
    require a greater than 0
    return a
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'no-contracts'
    assert result['require'] == 'a greater than 0'
    assert result['ensure'] is None


def test_no_contracts():
    code = """
fn plain(a: Number) -> Number:
    return a
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'no-contracts'
    assert result['require'] is None
    assert result['ensure'] is None


def test_loop_unsupported():
    code = """
fn looped(n: Number) -> Number:
    require n greater than 0
    ensure result is n
    total = 0
    for i in n:
        total = total + i
    end
    return total
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert result['reason'] is not None
    assert 'loop' in result['reason'].lower()


def test_text_param_unsupported():
    code = """
fn greet(name: Text) -> Text:
    require name is "hi"
    ensure result is name
    return name
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert result['reason'] is not None


def test_list_param_unsupported():
    code = """
fn first(items: List) -> Number:
    ensure result is 1
    return 1
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'


def test_division_guard_no_crash():
    code = """
fn divide(a: Number, b: Number) -> Number:
    require b is not 0
    ensure result is a / b
    return a / b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_if_else_paths_verified():
    code = """
fn choose(flag: Boolean, a: Number) -> Number:
    require flag
    ensure result is a
    if flag:
        return a
    end
    return a + 1
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_render_counterexample_plain_python_values():
    solver = z3.Solver()
    a = z3.Real('a')
    flag = z3.Bool('flag')
    solver.add(a == 7, flag)  # noqa: PLR2004
    assert solver.check() == z3.sat
    counterexample = render_counterexample(solver.model(), ['a', 'flag'])
    assert counterexample == {'a': 7, 'flag': True}
    assert isinstance(counterexample['a'], int)
    assert isinstance(counterexample['flag'], bool)


def test_schema_version_in_every_result():
    code = """
fn f1(a: Number) -> Number:
    require a is 1
    ensure result is 1
    return a
end

fn f2(x: Number) -> Number:
    return x
end
"""
    results = _verify(code)
    assert len(results) == 2  # noqa: PLR2004
    for result in results:
        assert result['schema'] == 'omni.verify'
        assert result['version'] == '1.0'
        assert 'function' in result
        assert 'status' in result


def test_boolean_literal_and_identifiers():
    code = """
fn flag(flag: Boolean) -> Boolean:
    require flag
    ensure result is true
    return flag
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_division_by_literal_zero_unsupported():
    code = """
fn broken(a: Number) -> Number:
    pure
    ensure result is 1
    return a / 0
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert result['reason'] is not None


def test_show_stmt_translates():
    code = """
fn loud(a: Number) -> Number:
    pure
    ensure result is a
    show a
    return a
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_fallthrough_without_return_unsupported():
    code = """
fn missing(a: Number) -> Number:
    require a greater than 0
    ensure result is a
    x = a
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert 'fall' in result['reason'].lower()


def test_function_call_in_ensure_unsupported():
    code = """
fn helper(x: Number) -> Number:
    pure
    return x
end

fn wraps(a: Number) -> Number:
    require a is 1
    ensure result is helper(a)
    return a
end
"""
    results = _verify(code)
    by_name = {r["function"]: r for r in results}
    assert by_name["wraps"]["status"] == "unsupported"
    assert "call" in by_name["wraps"]["reason"].lower()


def test_break_unsupported():
    code = """
fn early(a: Number) -> Number:
    pure
    ensure result is a
    for n in [1, 2]:
        break
    end
    return a
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'


def test_unsupported_requires_no_crash():
    code = """
fn tricky(a: Number) -> Number:
    require [a] is [1]
    ensure result is a
    return a
end
"""
    result = _verify(code)[0]
    assert result['status'] in ('unsupported', 'failed')


def test_verify_contracts_without_symbol_table():
    tokens = tokenize(
        "fn add(a: Number) -> Number:\n"
        "    pure\n"
        "    ensure result is a\n"
        "    return a\n"
        "end\n"
    )
    ast = parse(tokens)
    results = verify_contracts(ast, None)
    assert results[0]['status'] == 'verified'


def test_render_counterexample_float():
    solver = z3.Solver()
    a = z3.Real('a')
    expected = 2.5
    solver.add(a == expected)
    assert solver.check() == z3.sat
    counterexample = render_counterexample(solver.model(), ['a'])
    assert counterexample['a'] == expected
