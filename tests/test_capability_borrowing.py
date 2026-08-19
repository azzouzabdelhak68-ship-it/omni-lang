"""Capability delegation / borrowing tests.

`borrows` is a Rust-lifetime-style effect clause: a function borrows a
capability token from its caller for the duration of the call. The borrowed
capability may be exercised inside the function body without a `uses`
declaration, expires when the function returns, and every call site must
provide it.
"""

import json

import pytest

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import MIRModule, to_mir
from omni_compiler.parser import parse
from omni_compiler.rust_emitter import emit_rust


def _parse(code: str):
    return parse(tokenize(code))


def _analyze(code: str):
    ast = _parse(code)
    return ast, analyze(ast)


# ---- Parser ----

def test_parser_borrows_clause_simple():
    ast = _parse(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    fn = ast.functions[0]
    assert ('network', None) in fn.effects['borrows']
    assert fn.effects['pure'] is False


def test_parser_borrows_clause_parameterized():
    ast = _parse(
        """
fn read_cfg() -> Text:
    borrows network("api.com")
    return http_get("http://api.com")
end
"""
    )
    fn = ast.functions[0]
    assert ('network', 'api.com') in fn.effects['borrows']


def test_parser_borrows_multiple_on_one_line():
    ast = _parse(
        """
fn both() -> Number:
    borrows network database
    http_get("http://x.com")
    db_query("SELECT 1")
    return 0
end
"""
    )
    fn = ast.functions[0]
    caps = {cap for cap, _ in fn.effects['borrows']}
    assert caps == {'network', 'database'}


# ---- Checker: valid borrowing ----

def test_borrowed_cap_exercised_in_body_passes():
    _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )


def test_borrow_with_parameterized_value_passes():
    _analyze(
        """
fn read_cfg() -> Text:
    borrows network("api.com")
    return http_get("http://api.com")
end
"""
    )


def test_caller_provides_borrow_via_uses():
    _analyze(
        """
fn child() -> Text:
    borrows network
    return http_get("http://example.com")
end
fn parent() -> Text:
    uses network
    return child()
end
"""
    )


def test_caller_reborrows_capability():
    _analyze(
        """
fn child() -> Text:
    borrows network
    return http_get("http://example.com")
end
fn parent() -> Text:
    borrows network
    return child()
end
"""
    )


def test_caller_provides_via_reads():
    _analyze(
        """
fn child() -> Text:
    borrows network
    return http_get("http://example.com")
end
fn parent() -> Text:
    reads network
    return child()
end
"""
    )


def test_multiple_borrows_passes():
    _analyze(
        """
fn both() -> Number:
    borrows network database
    http_get("http://x.com")
    db_query("SELECT 1")
    return 0
end
"""
    )


# ---- Checker: violations ----

def test_pure_with_borrows_error():
    with pytest.raises(DiagnosticError) as excinfo:
        _analyze(
            """
fn bad() -> Text:
    pure
    borrows network
    return http_get("http://example.com")
end
"""
        )
    assert excinfo.value.code == 'E-EFFECT-010'


def test_dangling_borrow_error():
    with pytest.raises(DiagnosticError) as excinfo:
        _analyze(
            """
fn bad() -> Number:
    borrows network
    return 1
end
"""
        )
    assert excinfo.value.code == 'E-EFFECT-011'


def test_borrow_not_provided_by_caller_error():
    with pytest.raises(DiagnosticError) as excinfo:
        _analyze(
            """
fn child() -> Text:
    borrows network
    return http_get("http://example.com")
end
fn parent() -> Text:
    return child()
end
"""
        )
    assert excinfo.value.code == 'E-EFFECT-012'
    assert 'network' in excinfo.value.message


def test_app_block_implicitly_provides_borrow():
    # The app block is the top-level capability owner, so it is exempt from
    # the borrow-provider check, just as it is exempt from the `uses` check
    # for built-in capabilities.
    _analyze(
        """
fn child() -> Text:
    borrows network
    return http_get("http://example.com")
end
when app starts:
    child()
end
"""
    )


def test_borrow_chain_without_use_is_not_dangling():
    # A borrowed cap passed to a re-borrowing callee is exercised by
    # delegation, so it is not a dangling borrow.
    _analyze(
        """
fn leaf() -> Text:
    borrows network
    return http_get("http://example.com")
end
fn mid() -> Text:
    borrows network
    return leaf()
end
fn top() -> Text:
    borrows network
    return mid()
end
"""
    )


# ---- Symbol table ----

def test_symbol_table_declares_borrows():
    _, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    sym = table.inspect_symbol('read_cfg')
    assert sym is not None
    assert 'network' in sym['declared_effects']['borrows']


# ---- MIR ----

def test_mir_build_preserves_borrows():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    mir = to_mir(ast, table)
    assert isinstance(mir, MIRModule)
    assert mir.functions['read_cfg'].effects.borrows == [('network', None)]


def test_mir_json_roundtrip_preserves_borrows():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network("api.com")
    return http_get("http://api.com")
end
"""
    )
    mir = to_mir(ast, table)
    data = mir.to_json()
    restored = MIRModule.from_json(data)
    assert restored.functions['read_cfg'].effects.borrows == [['network', 'api.com']]


# ---- Emitters ----

def test_js_emitter_accepts_borrows():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    mir = to_mir(ast, table)
    out = emit_js(mir)
    assert 'function read_cfg' in out


def test_c_emitter_accepts_borrows():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    mir = to_mir(ast, table)
    out = emit_c(mir)
    assert 'read_cfg' in out


def test_rust_emitter_accepts_borrows():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    mir = to_mir(ast, table)
    out = emit_rust(mir)
    assert 'read_cfg' in out


def test_mir_json_shape_has_borrows_key():
    ast, table = _analyze(
        """
fn read_cfg() -> Text:
    borrows network
    return http_get("http://example.com")
end
"""
    )
    mir = to_mir(ast, table)
    data = json.loads(mir.to_json())
    assert 'borrows' in data['functions']['read_cfg']['effects']
    assert data['functions']['read_cfg']['effects']['borrows'] == [['network', None]]