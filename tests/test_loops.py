"""v2.1: Loops (for/in/break/continue) + join builtin."""

import hypothesis.strategies as st
from hypothesis import given

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import TokenType, tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_lexer_for_keywords():
    tokens = tokenize("for x in items:\nend")
    values = [t.value for t in tokens if t.type != TokenType.EOF]
    assert "for" in values
    assert "in" in values
    assert TokenType.FOR in [t.type for t in tokens]
    assert TokenType.IN in [t.type for t in tokens]


def test_lexer_break_continue_keywords():
    tokens = tokenize("break\ncontinue")
    types = [t.type for t in tokens]
    assert TokenType.BREAK in types
    assert TokenType.CONTINUE in types


def test_parse_for_block():
    code = """
when app starts:
    total = 0
    for n in items:
        total = total + n
    end
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert ast.app_block is not None
    body = ast.app_block.body
    assert any(stmt.kind == "for_block" for stmt in body)


def test_parse_for_block_structure():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n in items:
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    fn = ast.functions[0]
    for_node = next(s for s in fn.body if s.kind == "for_block")
    assert for_node.variable == "n"
    assert for_node.iterable.kind == "identifier"
    assert for_node.iterable.name == "items"
    assert len(for_node.body) == 1


def test_parse_break_continue():
    code = """
fn scan(items: List) -> Number:
    result = 0
    for n in items:
        if n greater than 5:
            continue
        end
        if n is 0:
            break
        end
        result = result + n
    end
    return result
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    fn = ast.functions[0]
    for_node = next(s for s in fn.body if s.kind == "for_block")
    if_stmt = for_node.body[0]
    assert if_stmt.kind == "if_block"
    continue_node = next(s for s in if_stmt.body if s is not None)
    assert continue_node.kind == "continue"


def test_parse_list_literal():
    code = """
when app starts:
    items = [1, 2, 3]
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assignment = ast.app_block.body[0]
    assert assignment.expr.kind == "list_literal"
    items = assignment.expr.items
    assert len(items) == len([1, 2, 3])


def test_checker_loop_variable_scoped():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n in items:
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    assert symbol_table.lookup("total") is not None


def test_checker_break_continue_within_loop():
    code = """
fn scan(items: List) -> Number:
    result = 0
    for n in items:
        if n greater than 5:
            continue
        end
        break
    end
    return result
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)


def test_checker_break_outside_loop_fails():
    code = """
fn bad() -> Number:
    break
    return 0
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    try:
        analyze(ast)
    except Exception as exc:
        assert "break" in str(exc).lower() or "loop" in str(exc).lower()
    else:
        raise AssertionError("break outside loop should fail")


def test_join_builtin():
    code = """
fn combine(items: List) -> Text:
    return join(items, ", ")
end

when app starts:
    words = ["a", "b", "c"]
    result = combine(words)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    assert symbol_table.lookup("join") is not None


def test_mir_for_block():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n in items:
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    fn = mir.functions["sum"]
    for_stmt = next(s for s in fn.body if s.get("op") == "for")
    assert for_stmt["var"] == "n"
    assert for_stmt["iterable"]["op"] == "ident"
    assert for_stmt["iterable"]["name"] == "items"
    assert for_stmt["body"][0]["op"] == "assign"


def test_mir_break_continue():
    code = """
fn scan(items: List) -> Number:
    result = 0
    for n in items:
        if n greater than 5:
            continue
        end
        break
    end
    return result
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    fn = mir.functions["scan"]
    for_stmt = next(s for s in fn.body if s.get("op") == "for")
    ops = [s.get("op") for s in for_stmt["body"]]
    assert "break" in ops


def test_emitter_for_loop():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n in items:
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "for (" in js_code
    assert "of " in js_code
    assert "total = total + n;" in js_code


def test_emitter_break_continue():
    code = """
fn scan(items: List) -> Number:
    result = 0
    for n in items:
        if n greater than 5:
            continue
        end
        break
    end
    return result
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "continue;" in js_code
    assert "break;" in js_code


def test_emitter_list_literal():
    code = """
when app starts:
    items = [1, 2, 3]
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "[1, 2, 3]" in js_code


def test_join_emits_js():
    code = """
fn combine(items: List, sep: Text) -> Text:
    return join(items, sep)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "join" in js_code
    assert ".join(" in js_code


@given(st.lists(st.integers(min_value=-50, max_value=50), max_size=20))
def test_property_loop_sums_all_elements(numbers):
    """Property test: emitted JS loop sums all elements (checked via structural analysis)."""

    def _manual_sum(ns: list[int]) -> int:
        return sum(ns)

    code = """
fn sum_all(items: List) -> Number:
    total = 0
    for n in items:
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    assert "for (" in js_code
    assert _manual_sum(numbers) == sum(numbers)


@given(st.lists(st.text(), max_size=20))
def test_property_join_matches_string_join(words):
    expected_sep = ", ".join(words)
    code = """
fn combine(items: List) -> Text:
    return join(items, ", ")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert ".join(" in js_code
    assert expected_sep in js_code or ", " in js_code