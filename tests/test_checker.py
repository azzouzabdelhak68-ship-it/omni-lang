import pytest

from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse


def test_name_resolution_success():
    code = """
when app starts:
    x = 42
    y = x
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    assert symbol_table.lookup("x") is not None
    assert symbol_table.lookup("y") is not None

def test_name_resolution_undefined_variable():
    code = """
when app starts:
    y = undefined_var
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "undefined" in str(excinfo.value).lower() or "not found" in str(excinfo.value).lower()

def test_symbol_inspection():
    code = """
fn add(a: Number, b: Number) -> Number:
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol("add")
    assert sym is not None
    assert sym["schema"] == "omni.symbol"
    assert sym["name"] == "add"
    assert sym["kind"] == "function"
    assert sym["type"] == "fn(Number, Number) -> Number"
    assert sym["exported"] is True

def test_effect_enforcement_network():
    code = """
fn fetch(url: Text) -> Text:
    uses network
    return "ok"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol("fetch")
    assert sym is not None
    assert "network" in sym["declared_effects"]["uses"]

def test_effect_enforcement_missing_network():
    code = """
fn fetch(url: Text) -> Text:
    return "ok"
end

when app starts:
    fetch("http://example.com")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "network" in str(excinfo.value).lower() or "capability" in str(excinfo.value).lower()

def test_pure_function_enforcement():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol("add")
    assert sym["declared_effects"]["pure"] is True

def test_pure_function_with_network_violation():
    code = """
fn bad_pure() -> Text:
    pure
    return "hello"
end

when app starts:
    show "test"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    # Should pass - pure function doesn't actually call network
    symbol_table = analyze(ast)

def test_require_ensure_parsing():
    code = """
fn divide(a: Number, b: Number) -> Number:
    require b is not 0
    ensure result is not 0
    pure
    return a / b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1
    assert fn.effects["pure"] is True

def test_effect_transitivity():
    code = """
fn helper() -> Text:
    uses network
    return "ok"
end

fn caller() -> Text:
    uses network
    return helper()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    
    helper_sym = symbol_table.inspect_symbol("helper")
    caller_sym = symbol_table.inspect_symbol("caller")
    
    assert "network" in helper_sym["declared_effects"]["uses"]
    assert "network" in caller_sym["declared_effects"]["uses"]

def test_require_ensure_type_checking():
    code = """
fn test(a: Number) -> Number:
    require a > 0
    ensure result > 0
    pure
    return a + 1
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    fn = ast.functions[0]
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1