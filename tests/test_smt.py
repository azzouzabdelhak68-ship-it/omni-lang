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
    assert result['status'] == 'verified'


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


def test_function_call_in_ensure_inlined():
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
    by_name = {r['function']: r for r in results}
    assert by_name['wraps']['status'] == 'verified'


def test_break_supported():
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
    assert result['status'] == 'verified'


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
        'fn add(a: Number) -> Number:\n    pure\n    ensure result is a\n    return a\nend\n'
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


def test_group_expr_in_contracts():
    code = """
fn mul_add(a: Number, b: Number) -> Number:
    pure
    require (a + b) greater than 0
    ensure result is a + b
    return a + b
end
"""
    ast = parse(tokenize(code))
    results = verify_contracts(ast)
    result = next(r for r in results if r['function'] == 'mul_add')
    assert result['status'] in ('verified', 'unsupported')


def test_not_and_neg_in_contracts():
    code = """
fn neg(a: Number) -> Number:
    pure
    ensure result is -a
    return -a
end
"""
    ast = parse(tokenize(code))
    results = verify_contracts(ast)
    result = next(r for r in results if r['function'] == 'neg')
    assert result['status'] in ('verified', 'unsupported')


# --- String/Text contract tests ---


def test_text_param_basic():
    code = """
fn greet(name: Text) -> Text:
    pure
    require name is "hi"
    ensure result is name
    return name
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_text_literal_in_contracts():
    code = """
fn hello() -> Text:
    pure
    ensure result is "hello"
    return "hello"
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_concatenation():
    code = """
fn concat(a: Text, b: Text) -> Text:
    pure
    ensure result is a + b
    return a + b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_concatenation_with_literal():
    code = """
fn greet(name: Text) -> Text:
    pure
    ensure result is "hello " + name
    return "hello " + name
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_concatenation_counterexample():
    code = """
fn concat(a: Text, b: Text) -> Text:
    require a is "a"
    require b is "b"
    ensure result is "wrong"
    return a + b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample']['a'] == 'a'
    assert result['counterexample']['b'] == 'b'
    assert result['counterexample']['result'] == 'ab'


def test_length_function():
    code = """
fn len(text: Text) -> Number:
    pure
    ensure result is length(text)
    return length(text)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_length_with_literal():
    code = """
fn len_hello() -> Number:
    pure
    ensure result is 5
    return length("hello")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_length_in_require():
    code = """
fn short(text: Text) -> Text:
    require length(text) less than 10
    ensure result is text
    return text
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_length_counterexample():
    code = """
fn len_check(text: Text) -> Number:
    require length(text) is 5
    ensure result is 5
    return length(text)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'

    # Test failing case
    code2 = """
fn len_check(text: Text) -> Number:
    require length(text) is 5
    ensure result is 3
    return length(text)
end
"""
    result2 = _verify(code2)[0]
    assert result2['status'] == 'failed'


def test_contains_function():
    code = """
fn has_sub(text: Text, sub: Text) -> Boolean:
    pure
    ensure result is contains(text, sub)
    return contains(text, sub)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_contains_with_literal():
    code = """
fn has_hello(text: Text) -> Boolean:
    pure
    ensure result is contains(text, "hello")
    return contains(text, "hello")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_contains_counterexample():
    code = """
fn check_contains(text: Text) -> Boolean:
    require text is "hello world"
    ensure result is false
    return contains(text, "hello")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample']['text'] == 'hello world'
    assert result['counterexample']['result'] is True


def test_starts_with_function():
    code = """
fn starts(text: Text, prefix: Text) -> Boolean:
    pure
    ensure result is starts_with(text, prefix)
    return starts_with(text, prefix)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_starts_with_counterexample():
    code = """
fn check_starts(text: Text) -> Boolean:
    require text is "hello"
    ensure result is false
    return starts_with(text, "he")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample']['result'] is True


def test_ends_with_function():
    code = """
fn ends(text: Text, suffix: Text) -> Boolean:
    pure
    ensure result is ends_with(text, suffix)
    return ends_with(text, suffix)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_ends_with_counterexample():
    code = """
fn check_ends(text: Text) -> Boolean:
    require text is "world"
    ensure result is false
    return ends_with(text, "ld")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample']['result'] is True


def test_substring_function():
    code = """
fn sub(text: Text, start: Number, end_pos: Number) -> Text:
    pure
    ensure result is substring(text, start, end_pos)
    return substring(text, start, end_pos)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_substring_with_literals():
    code = """
fn hello_sub() -> Text:
    pure
    ensure result is "ell"
    return substring("hello", 1, 4)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_substring_counterexample():
    code = """
fn check_sub(text: Text) -> Text:
    require text is "hello"
    ensure result is "xyz"
    return substring(text, 1, 3)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample']['result'] == 'el'


def test_string_equality():
    code = """
fn equal(a: Text, b: Text) -> Boolean:
    pure
    ensure result is (a is b)
    return a is b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_inequality():
    code = """
fn not_equal(a: Text, b: Text) -> Boolean:
    pure
    ensure result is (a is not b)
    return a is not b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_mixed_number_text_unsupported():
    code = """
fn mixed(a: Number, b: Text) -> Text:
    pure
    ensure result is b
    return a + b
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'


def test_regex_match_unsupported():
    code = """
fn check_regex(text: Text) -> Boolean:
    pure
    ensure result is regex_match(text, ".*")
    return regex_match(text, ".*")
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert 'regex' in result['reason'].lower()


def test_string_in_if_condition():
    code = """
fn branch(text: Text) -> Text:
    pure
    ensure (text is "a" and result is "a") or (text is not "a" and result is "other")
    if text is "a":
        return "a"
    end
    return "other"
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_assignment_and_return():
    code = """
fn build() -> Text:
    pure
    ensure result is "hello world"
    x = "hello"
    y = "world"
    return x + " " + y
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_empty_string():
    code = """
fn empty() -> Text:
    pure
    ensure result is ""
    ensure length(result) is 0
    return ""
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_require_ensure_combined():
    code = """
fn sanitize(input: Text) -> Text:
    require length(input) greater than 0
    require not contains(input, "<script>")
    ensure not contains(result, "<script>")
    ensure length(result) is length(input)
    return input
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_struct_param_field_access_verified():
    code = """
type Point = { x: Number, y: Number }
fn norm(p: Point) -> Number:
    pure
    ensure result is p.x + p.y
    return p.x + p.y
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_struct_construction_verified():
    code = """
type Point = { x: Number, y: Number }
fn make(a: Number, b: Number) -> Point:
    pure
    ensure result is Point(x=a, y=b)
    return Point(x=a, y=b)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_nested_struct_field_access():
    code = """
type Address = { street: Text, zip: Number }
type Person = { name: Text, address: Address }
fn zip_of(p: Person) -> Number:
    pure
    ensure result is p.address.zip
    return p.address.zip
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_struct_construction_counterexample():
    code = """
type Point = { x: Number, y: Number }
fn shifted(p: Point, dx: Number) -> Point:
    pure
    require p.x is 1
    ensure result is Point(x=p.x + dx, y=p.y)
    return Point(x=p.x, y=p.y)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'failed'
    assert result['counterexample'] is not None


def test_range_loop_bounded_verified():
    code = """
fn sum3(n: Number) -> Number:
    pure
    require n is 3
    ensure result is 3
    total = 0
    for i in range(n):
        total = total + i
    end
    return total
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_list_loop_verified():
    code = """
fn sum_list() -> Number:
    pure
    ensure result is 6
    total = 0
    for x in [1, 2, 3]:
        total = total + x
    end
    return total
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_while_loop_bounded_verified():
    code = """
fn dec(n: Number) -> Number:
    pure
    require n is 2
    ensure result is 0
    while n greater than 0:
        n = n - 1
    end
    return n
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_unbounded_range_loop_unsupported():
    code = """
fn sum(n: Number) -> Number:
    pure
    ensure result is 0
    total = 0
    for i in range(n):
        total = total + i
    end
    return total
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert 'unrolling bound' in result['reason']


def test_unbounded_while_loop_unsupported():
    code = """
fn dec(n: Number) -> Number:
    pure
    ensure result is 0
    while n greater than 0:
        n = n - 1
    end
    return n
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert 'terminate' in result['reason']


def test_recursive_function_call_unsupported():
    code = """
fn countdown(n: Number) -> Number:
    pure
    ensure result is 0
    if n less or equal 0:
        return 0
    end
    return countdown(n - 1)
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'unsupported'
    assert 'recursive' in result['reason'].lower()


def test_function_call_multiple_paths_verified():
    code = """
fn helper(x: Number) -> Number:
    pure
    if x greater than 10:
        return x * 2
    end
    return x + 1
end

fn caller(a: Number) -> Number:
    require a is 5
    ensure result is helper(a)
    return a + 1
end
"""
    results = _verify(code)
    by_name = {r['function']: r for r in results}
    assert by_name['caller']['status'] == 'verified'


def test_function_call_failed_counterexample():
    code = """
fn helper(x: Number) -> Number:
    pure
    return x + 1
end

fn wraps(a: Number) -> Number:
    require a is 1
    ensure result is helper(a)
    return a
end
"""
    results = _verify(code)
    by_name = {r['function']: r for r in results}
    assert by_name['wraps']['status'] == 'failed'


def test_break_inside_range_loop_verified():
    code = """
fn first_two(n: Number) -> Number:
    pure
    require n is 5
    ensure result is 2
    target = 0
    for i in range(n):
        if i is 2:
            target = i
            break
        end
    end
    return target
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'


def test_string_sanitization_proof():
    code = """
fn sanitize(input: Text) -> Text:
    require length(input) greater than 0
    require not contains(input, "<script>")
    ensure not contains(result, "<script>")
    ensure length(result) less or equal length(input)
    return substring(input, 0, length(input))
end
"""
    result = _verify(code)[0]
    assert result['status'] == 'verified'
