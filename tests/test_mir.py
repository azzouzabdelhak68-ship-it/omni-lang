import json

from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.mir import MIRModule, to_mir
from omni_compiler.parser import parse


def test_mir_basic_structure():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    assert isinstance(mir, MIRModule)
    assert 'add' in mir.functions
    assert mir.version == '1.0'
    assert mir.schema == 'omni.mir'


def test_mir_function_structure():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    fn = mir.functions['add']
    assert fn.name == 'add'
    assert fn.return_type == 'Number'
    assert len(fn.params) == 2
    assert fn.params[0].name == 'a'
    assert fn.params[0].type == 'Number'
    assert fn.params[1].name == 'b'
    assert fn.params[1].type == 'Number'
    assert fn.effects.pure is True
    assert fn.effects.uses == []


def test_mir_with_effects():
    code = """
fn fetch(url: Text) -> Text:
    uses network
    reads cache
    return "data"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    fn = mir.functions['fetch']
    # Effects are now stored as tuples (capability, parameter)
    uses = [cap if isinstance(cap, str) else cap[0] for cap in fn.effects.uses]
    reads = [cap if isinstance(cap, str) else cap[0] for cap in fn.effects.reads]
    assert 'network' in uses
    assert 'cache' in reads
    assert fn.effects.writes == []
    assert fn.effects.pure is False


def test_mir_serialization():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    # Test JSON serialization
    json_str = mir.to_json()
    assert isinstance(json_str, str)

    # Verify it can be parsed back
    parsed = json.loads(json_str)
    assert parsed['schema'] == 'omni.mir'
    assert parsed['version'] == '1.0'
    assert 'add' in parsed['functions']


def test_mir_with_require_ensure():
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
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    fn = mir.functions['divide']
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1
    assert 'b is not 0' in fn.requires[0]
    assert 'result is not 0' in fn.ensures[0]


def test_mir_ui_block():
    code = """
when app starts:
    greeting = "Hello"
end

UI:
<h1>{greeting}</h1>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    assert mir.ui_template is not None
    assert '<h1>{greeting}</h1>' in mir.ui_template


def test_mir_serialization_roundtrip():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    # Serialize to JSON
    json_str = mir.to_json()

    # Deserialize
    from omni_compiler.mir import MIRModule  # noqa: PLC0415

    mir2 = MIRModule.from_json(json_str)

    assert mir2.version == mir.version
    assert mir2.schema == mir.schema
    assert 'add' in mir2.functions
    assert mir2.functions['add'].name == 'add'


def test_mir_normalizes_omnisys_call_names():
    code = """
import OMNISYS.core
when app starts:
    show OMNISYS.core.abs(-5)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert mir.entry_point[0]['op'] == 'show'
    call = mir.entry_point[0]['expr']
    assert call['name'] == 'omnisys.core.abs'


def test_mir_group_expr():
    code = """
when app starts:
    a = 1
    b = 2
    c = 3
    x = (a + b + c) / 5
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    expr = mir.entry_point[3]['expr']
    assert expr['op'] == '/'
    assert expr['left']['op'] == 'group'


def test_mir_unary_expr():
    code = """
when app starts:
    x = -1
    y = not true
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert mir.entry_point[0]['expr']['op'] == 'neg'
    assert mir.entry_point[1]['expr']['op'] == 'not'
