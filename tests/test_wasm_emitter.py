# ruff: noqa: Q000 - single quotes are the repo style; lint Q000 defaults to double.

"""v3.3: WASM Emitter tests."""

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse
from omni_compiler.wasm_emitter import (
    emit_wasm,
    emit_wasm_browser,
    emit_wasm_wasi,
    wasm_build_command,
)

_SOURCE = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
end
"""


def _mir():
    tokens = tokenize(_SOURCE)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    return to_mir(ast, symbol_table)


def test_emit_wasm_browser_contains_build_and_glue():
    out = emit_wasm(_mir(), mode='browser')

    assert '--target=wasm32' in out
    assert 'WebAssembly.instantiateStreaming' in out
    assert '<canvas' in out
    assert '<script' in out


def test_emit_wasm_browser_import_shim():
    out = emit_wasm_browser(_mir())

    assert 'printf' in out
    assert 'console.log' in out
    assert 'emscripten_notify_memory_growth' in out
    assert 'WebAssembly.Memory' in out


def test_emit_wasm_wasi_contains_target_and_c():
    out = emit_wasm(_mir(), mode='wasi')

    assert '--target=wasm32-wasi' in out
    assert 'wasmtime app.wasm' in out
    assert 'int main(' in out
    assert 'double add(double a, double b)' in out


def test_emit_wasm_wasi_helper():
    assert 'int main(' in emit_wasm_wasi(_mir())


def test_wasm_build_command():
    assert wasm_build_command('browser') == (
        'clang --target=wasm32 --no-standard-libraries '
        '-Wl,--no-entry -Wl,--export-all -o app.wasm app.c'
    )
    assert wasm_build_command('wasi') == 'clang --target=wasm32-wasi -o app.wasm app.c'
    assert wasm_build_command() == wasm_build_command('browser')


def test_browser_html_parseable():
    out = emit_wasm_browser(_mir())

    assert out.startswith('<!DOCTYPE html>')
    assert '</html>' in out


def test_browser_embeds_c_source():
    mir = _mir()

    assert emit_c(mir) in emit_wasm_browser(mir)


def test_wasm_group_not_neg_through_c():
    code = """
fn decide(a: Number) -> Boolean:
    pure
    return not (a is 0)
end

fn flipped(a: Number) -> Number:
    pure
    return -a
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    out = emit_wasm(mir, mode='wasi')

    assert 'return (!((a == 0.0)));' in out
    assert 'return (-a);' in out
