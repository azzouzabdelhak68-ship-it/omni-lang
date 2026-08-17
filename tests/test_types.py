"""v2.3: Custom types — type Name = {...}, field access, TS interface emission."""

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import TokenType, tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_lexer_type_keyword():
    tokens = tokenize("type Person = { name: Text }")
    types = [t.type for t in tokens]
    assert TokenType.TYPE in types
    assert TokenType.LBRACE in types
    assert TokenType.RBRACE in types


def test_parse_type_declaration():
    code = """
type Person = { name: Text, age: Number }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.types) == 1
    t = ast.types[0]
    assert t.name == "Person"
    assert t.fields["name"] == "Text"
    assert t.fields["age"] == "Number"


def test_parse_nested_type():
    code = """
type Address = { street: Text, zip: Number }
type Person = { name: Text, address: Address }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.types) == len(["Address", "Person"])
    person = ast.types[1]
    assert person.fields["address"] == "Address"


def test_parse_field_access():
    code = """
when app starts:
    p = Person()
    n = p.name
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    body = ast.app_block.body
    field_stmt = body[1]
    assert field_stmt.kind == "assignment"
    assert field_stmt.expr.kind == "field_access"
    assert field_stmt.expr.object.name == "p"
    assert field_stmt.expr.field == "name"


def test_parse_struct_literal_constructor():
    code = """
when app starts:
    p = Person(name="Ada", age=36)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    body = ast.app_block.body
    constructor = body[0].expr
    assert constructor.kind == "struct_construct"
    assert constructor.name == "Person"
    assert "name" in constructor.args
    assert "age" in constructor.args


def test_checker_custom_type_registered():
    code = """
type Person = { name: Text, age: Number }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol("Person")
    assert sym is not None
    assert sym["kind"] == "type"


def test_checker_field_access_valid():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
    n = p.name
    a = p.age
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)


def test_checker_field_access_unknown_field_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
    n = p.nonexistent
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "field" in str(excinfo.value).lower() or "nonexistent" in str(excinfo.value).lower()


def test_checker_field_access_on_non_struct_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    x = 42
    n = x.name
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "field" in str(excinfo.value).lower() or "struct" in str(excinfo.value).lower()


def test_checker_nested_field_access():
    code = """
type Address = { street: Text, zip: Number }
type Person = { name: Text, address: Address }

when app starts:
    p = Person(name="Ada", address=Address(street="Main", zip=1))
    s = p.address.street
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)


def test_checker_constructor_missing_field_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "age" in str(excinfo.value) or "field" in str(excinfo.value).lower()


def test_checker_constructor_unknown_field_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36, bogus=1)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert "bogus" in str(excinfo.value) or "field" in str(excinfo.value).lower()


def test_mir_type_declarations():
    code = """
type Person = { name: Text, age: Number }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert "Person" in mir.types
    assert mir.types["Person"]["fields"]["name"] == "Text"
    assert mir.types["Person"]["fields"]["age"] == "Number"


def test_mir_json_roundtrip_with_types():
    code = """
type Person = { name: Text, age: Number }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    json_str = mir.to_json()
    assert "Person" in json_str
    mir2 = mir.from_json(json_str)
    assert mir2.types["Person"]["fields"]["name"] == "Text"


def test_emitter_ts_interface():
    code = """
type Person = { name: Text, age: Number }
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "interface Person" in js_code
    assert "name" in js_code
    assert "age" in js_code


def test_emitter_struct_constructor():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "name:" in js_code
    assert '"Ada"' in js_code
    assert "36" in js_code


def test_emitter_field_access():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
    n = p.name
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert "p.name" in js_code