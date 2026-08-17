from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse


def test_parse_assignment():
    code = "x = 42"
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.statements) == 1
    assert ast.statements[0].kind == "assignment"
    assert ast.statements[0].name == "x"

def test_parse_app_block():
    code = """
when app starts:
    greeting = "Hello"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert ast.app_block is not None
    assert len(ast.app_block.body) == 1

def test_parse_fn_block():
    code = """
fn add(a: Number, b: Number) -> Number:
    require a is not 0
    uses network
    reads config
    writes cache
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.name == "add"
    assert len(fn.params) == 2
    assert fn.return_type == "Number"
    assert len(fn.requires) == 1
    assert fn.effects["uses"] == ["network"]
    assert fn.effects["reads"] == ["config"]
    assert fn.effects["writes"] == ["cache"]

def test_parse_ui_block():
    code = """
UI:
<h1>{greeting}</h1>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert ast.ui_template is not None
    assert "<h1>" in ast.ui_template

def test_parse_statements_and_calls():
    code = """
fn compute() -> Number:
    show "starting"
    res = add(10, 20)
    return res
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert len(fn.body) == 3
    assert fn.body[0].kind == "show"
    assert fn.body[1].kind == "assignment"
    assert fn.body[1].expr.kind == "function_call"
    assert fn.body[1].expr.name == "add"
    assert fn.body[2].kind == "return"

