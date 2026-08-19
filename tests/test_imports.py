"""v6: `import OMNISYS` compiler support.

Parsing, module validation, effect enforcement, MIR carry, JS-runtime
inlining, and the per-backend gate. These tests exercise the Python
pipeline only (no Node required).
"""

import subprocess
from pathlib import Path

import pytest

from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.omnisys_registry import (
    OMNISYS_MODULES,
    is_omnisys_call,
    js_files_for,
    module_names,
    omnisys_effects,
    resolve_import,
)
from omni_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[1]


def _compile(code: str):
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return ast, symbol_table, mir


def _error_code(code: str) -> str:
    with pytest.raises(DiagnosticError) as exc_info:
        _compile(code)
    return exc_info.value.code


# --------------------------------------------------------------------------
# Registry invariants
# --------------------------------------------------------------------------


def test_registry_module_count_matches_spec() -> None:
    names = set(module_names())
    # Â§17.1 tree minus `collections`/`serde`/`error` (subsumed by core) plus
    # `observability`, `tool`, `pkg` (v6 Phase 5/6) â€” the 18-doc module set.
    expected = {
        'core',
        'ui',
        'db',
        'graphics',
        'gpu',
        'net',
        'http',
        'audio',
        'video',
        'fs',
        'crypto',
        'auth',
        'sim',
        'ai',
        'test',
        'async',
        'platform',
        'scene',
        'collections',
        'serde',
        'error',
        'observability',
        'tool',
        'pkg',
    }
    assert names == expected


def test_every_module_has_js_file() -> None:
    for name, module in OMNISYS_MODULES.items():
        assert (ROOT / module.js_file).exists(), f'{name} -> {module.js_file} missing'
        assert module.functions, f'{name} has no functions'


def test_registry_js_deps_are_known_modules() -> None:
    names = set(OMNISYS_MODULES)
    for module in OMNISYS_MODULES.values():
        for dep in module.js_deps:
            assert dep in names, f'unknown js dep {dep}'


def test_resolve_import_core_is_umbrella() -> None:
    assert resolve_import(('OMNISYS',)).js_file == 'omnisys/core.js'
    assert resolve_import(('OMNISYS', 'core')).js_file == 'omnisys/core.js'
    assert resolve_import(('OMNISYS', 'fs')).js_file == 'omnisys/fs.js'
    assert resolve_import(('OMNISYS', 'nope')) is None
    assert resolve_import(('foo',)) is None


def test_is_omnisys_call_and_effects() -> None:
    assert is_omnisys_call('omnisys.fs.write_file')
    assert is_omnisys_call('OMNISYS.fs.write_file')
    assert not is_omnisys_call('omnisys.nope.fn')
    assert not is_omnisys_call('sim.spawn')
    assert not is_omnisys_call('omnisys.fs')  # too short
    assert omnisys_effects('omnisys.fs.write_file') == {'filesystem'}
    assert omnisys_effects('omnisys.core.abs') == set()


def test_js_files_for_dependency_order() -> None:
    files = js_files_for([['OMNISYS', 'http']])
    # deps first, http last
    assert files[-1] == 'omnisys/http.js'
    assert files.index('omnisys/core.js') < files.index('omnisys/net.js')
    assert files.index('omnisys/net.js') < files.index('omnisys/http.js')
    assert len(files) == len(set(files))
    # umbrella import inlines only core
    assert js_files_for([['OMNISYS']]) == ['omnisys/core.js']


# --------------------------------------------------------------------------
# Parser / MIR
# --------------------------------------------------------------------------


def test_parse_imports_and_mir_carry() -> None:
    _, _, mir = _compile('import OMNISYS\nimport OMNISYS.fs\nwhen app starts:\n    show 1\nend\n')
    assert mir.imports == [['OMNISYS'], ['OMNISYS', 'fs']]


def test_mir_json_round_trip_preserves_imports() -> None:
    _, _, mir = _compile('import OMNISYS.db\nwhen app starts:\n    show 1\nend\n')
    assert mir.imports
    from omni_compiler.mir import MIRModule  # noqa: PLC0415

    round_tripped = MIRModule.from_json(mir.to_json())
    assert round_tripped.imports == [['OMNISYS', 'db']]


def test_import_statement_must_precede_use_for_diagnostic() -> None:
    # using a module without importing it is E-IMPORT-003
    assert (
        _error_code('when app starts:\n    show omnisys.collections.list_join([1, 2], ",")\nend\n')
        == 'E-IMPORT-003'
    )


def test_import_omnisys_scene_parses() -> None:
    from omni_compiler.parser import ImportDecl  # noqa: PLC0415

    tokens = tokenize('import OMNISYS.scene\nwhen app starts:\n    show 1\nend\n')
    ast = parse(tokens)
    assert len(ast.imports) == 1
    imp = ast.imports[0]
    assert isinstance(imp, ImportDecl)
    assert imp.path == ['OMNISYS', 'scene']


def test_import_omnisys_scene_full_pipeline() -> None:
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.emitter import emit_js  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415

    code = 'import OMNISYS.scene\nwhen app starts:\n    show omnisys.scene.new_scene()\nend\n'
    ast = parse(tokenize(code))
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert mir.imports == [['OMNISYS', 'scene']]
    html = emit_js(mir)
    assert 'omnisys/scene.js' not in html  # inlined, no path leak
    assert 'omnisys.scene' in html


# --------------------------------------------------------------------------
# Import validation diagnostics
# --------------------------------------------------------------------------


def test_unknown_import_root_rejected() -> None:
    assert _error_code('import foo\nwhen app starts:\n    show 1\nend\n') == 'E-IMPORT-001'


def test_unknown_omnisys_module_rejected() -> None:
    assert _error_code('import OMNISYS.wat\nwhen app starts:\n    show 1\nend\n') == 'E-IMPORT-002'


def test_imported_module_used_is_valid() -> None:
    ast, symbol_table, mir = _compile(
        'import OMNISYS.core\nwhen app starts:\n    show omnisys.core.length([1])\nend\n'
    )
    assert mir.imports == [['OMNISYS', 'core']]
    assert symbol_table.inspect_symbol('omnisys.core.length') is None  # dotted, not a symbol


def test_omnisys_call_inside_declared_function_ok() -> None:
    code = """
import OMNISYS.fs
fn save(path: Text, data: Text) -> Text:
    uses filesystem
    omnisys.fs.write_file(path, data)
    return "ok"
end
when app starts:
    show save("x.txt", "hi")
end
"""
    _compile(code)


# --------------------------------------------------------------------------
# Effect enforcement
# --------------------------------------------------------------------------


def test_omnisys_effect_requires_declaration() -> None:
    # fs.write_file used without declaring `uses filesystem` -> E-EFFECT-003
    assert (
        _error_code(
            """
import OMNISYS.fs
fn bad(path: Text) -> Text:
    omnisys.fs.write_file(path, "x")
    return "ok"
end
when app starts:
    show bad("x.txt")
end
"""
        )
        == 'E-EFFECT-003'
    )


def test_omnisys_effect_in_pure_function_rejected() -> None:
    assert (
        _error_code(
            """
import OMNISYS.net
fn bad() -> Number:
    pure
    s = omnisys.net.server(handler)
    return 1
end
fn handler(req: Map) -> Map:
    pure
    return req
end
when app starts:
    show 1
end
"""
        )
        == 'E-EFFECT-001'
    )


def test_omnisys_effect_in_app_block_rejected() -> None:
    assert (
        _error_code(
            """
import OMNISYS.fs
when app starts:
    omnisys.fs.file_exists("x")
end
"""
        )
        == 'E-EFFECT-003'
    )


def test_omnisys_call_without_effect_is_fine_in_app_block() -> None:
    _compile(
        """
import OMNISYS.core
when app starts:
    show omnisys.core.abs(5)
end
"""
    )


# --------------------------------------------------------------------------
# v6 Phase 8: capability/effect modeling
# --------------------------------------------------------------------------


def test_gpu_buffer_requires_gpu_capability() -> None:
    # 3.4 C-07: gpu.buffer is GPU-gated, not pure.
    assert (
        _error_code(
            """
import OMNISYS.gpu
fn load(data: List) -> Buffer:
    pure
    return omnisys.gpu.buffer(data)
end
when app starts:
    show 1
end
"""
        )
        == 'E-EFFECT-001'
    )
    _compile(
        """
import OMNISYS.gpu
fn load(data: List) -> Buffer:
    uses GPU
    return omnisys.gpu.buffer(data)
end
when app starts:
    show 1
end
"""
    )


def test_throw_error_not_pure() -> None:
    # 1.4: throw_error aborts control flow; the declaration must be honest.
    assert (
        _error_code(
            """
import OMNISYS.error
fn fail(e: Error) -> None:
    pure
    omnisys.error.throw_error(e)
end
when app starts:
    show 1
end
"""
        )
        == 'E-EFFECT-001'
    )
    assert (
        _error_code(
            """
import OMNISYS.error
fn fail(e: Error) -> None:
    omnisys.error.throw_error(e)
end
when app starts:
    show 1
end
"""
        )
        == 'E-EFFECT-003'
    )
    _compile(
        """
import OMNISYS.error
fn fail(e: Error) -> None:
    uses panic
    omnisys.error.throw_error(e)
end
when app starts:
    show 1
end
"""
    )


def test_serde_fallible_decoders_not_pure() -> None:
    # 2.3: json_decode/base64_decode abort on malformed input -> `uses panic`.
    assert (
        _error_code(
            """
import OMNISYS.serde
fn parse(t: Text) -> any:
    pure
    return omnisys.serde.json_decode(t)
end
when app starts:
    show 1
end
"""
        )
        == 'E-EFFECT-001'
    )
    _compile(
        """
import OMNISYS.serde
fn parse(t: Text) -> any:
    uses panic
    return omnisys.serde.json_decode(t)
end
when app starts:
    show 1
end
"""
    )
    assert omnisys_effects('omnisys.serde.json_encode') == set()
    assert omnisys_effects('omnisys.serde.json_decode') == {'panic'}
    assert omnisys_effects('omnisys.gpu.buffer') == {'GPU'}
    assert omnisys_effects('omnisys.error.throw_error') == {'panic'}
    assert omnisys_effects('omnisys.core.panic') == {'panic'}


# --------------------------------------------------------------------------
# JS emitter inlining
# --------------------------------------------------------------------------


def test_emitter_inlines_only_imported_modules() -> None:
    _, _, mir = _compile(
        'import OMNISYS.core\nwhen app starts:\n    show omnisys.core.abs(1)\nend\n'
    )
    html = emit_js(mir)
    assert 'OMNISYS runtime' in html
    assert 'omnisys/core.js' not in html  # inlined by value, no path leak
    assert 'core.panic' in html


def test_emitter_inlines_transitive_dependencies() -> None:
    _, _, mir = _compile('import OMNISYS.http\nwhen app starts:\n    show 1\nend\n')
    html = emit_js(mir)
    assert 'omnisys.net' in html  # http depends on net
    assert 'omnisys.http' in html


def test_emitter_does_not_inline_without_imports() -> None:
    _, _, mir = _compile('when app starts:\n    show 1\nend\n')
    html = emit_js(mir)
    assert 'OMNISYS runtime' not in html


# --------------------------------------------------------------------------
# CLI per-backend gate
# --------------------------------------------------------------------------


def test_cli_build_rejects_omnisys_calls_on_native_targets(tmp_path: Path) -> None:
    # The §8.3 gate is per-capability: a program that actually CALLS an
    # omnisys.* function requires the JS lane and is rejected on native targets.
    source = tmp_path / 'app.omni'
    source.write_text(
        'import OMNISYS.core\nwhen app starts:\n    show omnisys.core.abs(-5)\nend\n',
        encoding='utf-8',
    )
    for target in ('c', 'rust', 'wasm-browser', 'wasm-wasi'):
        proc = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'build', str(source), '--target', target],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 1, target
        assert 'E-BACKEND-001' in proc.stdout


def test_cli_build_allows_import_only_omnisys_on_native(tmp_path: Path) -> None:
    # §8.3 carve-out: an `import OMNISYS` that never invokes an omnisys.*
    # function consumes no capability, so it builds on native targets.
    source = tmp_path / 'app.omni'
    source.write_text('import OMNISYS.core\nwhen app starts:\n    show 1\nend\n', encoding='utf-8')
    targets = (('c', '.c'), ('rust', '.rs'), ('wasm-browser', '.html'), ('wasm-wasi', '.c'))
    for target, suffix in targets:
        proc = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'build', str(source), '--target', target],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 0, f'{target}: {proc.stdout} {proc.stderr}'
        assert (tmp_path / f'app{suffix}').exists(), target


def test_cli_build_js_allows_omnisys(tmp_path: Path) -> None:
    source = tmp_path / 'app.omni'
    source.write_text('import OMNISYS.core\nwhen app starts:\n    show 1\nend\n', encoding='utf-8')
    proc = subprocess.run(
        ['python', '-m', 'omni_compiler.cli', 'build', str(source), '--target', 'js'],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0
    assert 'OMNISYS runtime' in (tmp_path / 'app.html').read_text(encoding='utf-8')


def test_cli_check_accepts_import_program(tmp_path: Path) -> None:
    source = tmp_path / 'app.omni'
    source.write_text(
        'import OMNISYS.core\nwhen app starts:\n    show omnisys.core.length([1,2])\nend\n',
        encoding='utf-8',
    )
    proc = subprocess.run(
        ['python', '-m', 'omni_compiler.cli', 'check', str(source)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0
    assert 'OK' in proc.stdout
