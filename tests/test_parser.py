from omni_compiler.lexer import is_agent_mode, tokenize
from omni_compiler.parser import parse


def test_is_agent_mode_detection():
    code = '#lang agent\nadd(a, b) -> Number: a + b'
    assert is_agent_mode(code) is True

    code2 = 'fn add(a: Number, b: Number) -> Number:\n    return a + b\nend'
    assert is_agent_mode(code2) is False


def test_agent_mode_implicit_fn():
    code = """#lang agent
add(a: Number, b: Number) -> Number:
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.name == 'add'
    assert len(fn.params) == 2
    assert fn.params[0].name == 'a'
    assert fn.params[0].type == 'Number'
    assert fn.params[1].name == 'b'
    assert fn.params[1].type == 'Number'
    assert fn.return_type == 'Number'
    assert len(fn.body) == 1
    assert fn.body[0].kind == 'return'


def test_agent_mode_single_expression_function():
    code = """#lang agent
add(a: Number, b: Number) -> Number: a + b
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.name == 'add'
    assert len(fn.params) == 2
    assert fn.return_type == 'Number'
    # Single expression becomes implicit return
    assert len(fn.body) == 1
    assert fn.body[0].kind == 'return'
    assert fn.body[0].expr.kind == 'binary_expr'
    assert fn.body[0].expr.op == '+'
    # Implicit pure for single-expression functions
    assert fn.effects['pure'] is True


def test_agent_mode_fat_arrow():
    code = """#lang agent
add(a: Number, b: Number) => Number: a + b
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.name == 'add'
    assert fn.return_type == 'Number'


def test_agent_mode_optional_types():
    code = """#lang agent
add(a: Number?, b: Number?) -> Number?:
    a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.params[0].type == 'Number?'
    assert fn.params[1].type == 'Number?'
    assert fn.return_type == 'Number?'


def test_agent_mode_compact_contracts():
    code = """#lang agent
divide(a: Number, b: Number) -> Number:
    @require b != 0
    @ensure result != 0
    a / b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1
    # The expressions should be parsed correctly
    req = fn.requires[0]
    assert req.kind == 'binary_expr'
    assert req.op == 'is not'


def test_agent_mode_pipe_operator():
    code = """#lang agent
process(x: Number) -> Number:
    x |> double |> increment
end

double(x: Number) -> Number: x * 2
increment(x: Number) -> Number: x + 1
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 3
    fn = ast.functions[0]
    # The pipe expression should be parsed as BinaryExpr with op '|>'
    body = fn.body[0]
    assert body.kind == 'return'
    expr = body.expr
    # x |> double |> increment  parses as (x |> double) |> increment
    assert expr.kind == 'binary_expr'
    assert expr.op == '|>'
    right = expr.right
    assert right.kind == 'identifier'
    assert right.name == 'increment'
    left = expr.left
    assert left.kind == 'binary_expr'
    assert left.op == '|>'
    assert left.left.kind == 'identifier'
    assert left.left.name == 'x'
    assert left.right.kind == 'identifier'
    assert left.right.name == 'double'


def test_agent_mode_no_end_for_single_expr():
    code = """#lang agent
add(a: Number, b: Number) -> Number: a + b
mul(a: Number, b: Number) -> Number: a * b
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 2
    for fn in ast.functions:
        assert len(fn.body) == 1
        assert fn.body[0].kind == 'return'
        assert fn.effects['pure'] is True


def test_agent_mode_mixed_with_regular_syntax():
    code = """#lang agent
# Regular function with full syntax
fn subtract(a: Number, b: Number) -> Number:
    return a - b
end

# Shorthand function
add(a: Number, b: Number) -> Number: a + b
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 2
    # Both should parse correctly
    fn1 = ast.functions[0]
    assert fn1.name == 'subtract'
    fn2 = ast.functions[1]
    assert fn2.name == 'add'
    assert fn2.effects['pure'] is True


def test_agent_mode_multi_statement_function():
    code = """#lang agent
compute(x: Number) -> Number:
    y = x * 2
    z = y + 1
    return z
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert fn.name == 'compute'
    # Multi-statement function should have multiple body statements
    assert len(fn.body) == 3
    assert fn.body[0].kind == 'assignment'
    assert fn.body[1].kind == 'assignment'
    assert fn.body[2].kind == 'return'
    # Not implicit pure for multi-statement
    assert fn.effects['pure'] is False


def test_parse_assignment():
    code = 'x = 42'
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.statements) == 1
    assert ast.statements[0].kind == 'assignment'
    assert ast.statements[0].name == 'x'


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
    assert fn.name == 'add'
    assert len(fn.params) == 2  # noqa: PLR2004
    assert fn.return_type == 'Number'
    assert len(fn.requires) == 1
    assert fn.effects['uses'] == [('network', None)]
    assert fn.effects['reads'] == [('config', None)]
    assert fn.effects['writes'] == [('cache', None)]


def test_parse_ui_block():
    code = """
UI:
<h1>{greeting}</h1>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert ast.ui_template is not None
    assert '<h1>' in ast.ui_template


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
    assert len(fn.body) == 3  # noqa: PLR2004
    assert fn.body[0].kind == 'show'
    assert fn.body[1].kind == 'assignment'
    assert fn.body[1].expr.kind == 'function_call'
    assert fn.body[1].expr.name == 'add'
    assert fn.body[2].kind == 'return'


def test_parse_logical_and_or():
    code = """
fn decide(a: Number, b: Number) -> Number:
    pure
    if a is 1 and b is 2:
        return 1
    end
    if a is 1 or b is 2:
        return 2
    end
    return 0
end
"""
    ast = parse(tokenize(code))
    fn = ast.functions[0]
    first = fn.body[0].condition
    assert first.kind == 'binary_expr'
    assert first.op == 'and'
    assert first.left.kind == 'binary_expr'
    assert first.left.op == 'is'


def test_parse_not_expression():
    code = """
when app starts:
    x = 1
    if not (x is 0):
        show x
    end
end
"""
    ast = parse(tokenize(code))
    cond = ast.app_block.body[1].condition
    assert cond.kind == 'unary_expr'
    assert cond.op == 'not'
    assert cond.operand.kind == 'group_expr'


def test_parse_negative_literals():
    code = """
when app starts:
    x = -1
    y = -(-5)
end
"""
    ast = parse(tokenize(code))
    x = ast.app_block.body[0].expr
    assert x.kind == 'unary_expr'
    assert x.op == 'neg'
    y = ast.app_block.body[1].expr
    assert y.op == 'neg'
    assert y.operand.kind == 'group_expr'
    assert y.operand.expr.op == 'neg'


def test_parse_comparison_with_negation():
    code = """
when app starts:
    x = 1
    if x is -1:
        show x
    end
end
"""
    ast = parse(tokenize(code))
    cond = ast.app_block.body[1].condition
    assert cond.kind == 'binary_expr'
    assert cond.op == 'is'
    assert cond.right.kind == 'unary_expr'
    assert cond.right.op == 'neg'


def test_parse_not_binds_looser_than_is():
    # `not x is 1` must parse as `not (x is 1)`
    code = """
when app starts:
    x = 1
    if not x is 1:
        show x
    end
end
"""
    ast = parse(tokenize(code))
    cond = ast.app_block.body[1].condition
    assert cond.kind == 'unary_expr'
    assert cond.op == 'not'
    assert cond.operand.kind == 'binary_expr'
    assert cond.operand.op == 'is'
