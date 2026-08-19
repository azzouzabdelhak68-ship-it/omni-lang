# ruff: noqa: Q000 - single quotes are the repo style; lint Q000 defaults to double.

"""WASM Emitter Module (v3.5).

Wraps the C emitter output for WebAssembly targets:
- browser: a self-contained HTML page with a canvas, the embedded C
  source, and JS glue that instantiates the module and mirrors printf.
- wasi: the C source plus wasm32-wasi build/run command comments for
  server/edge runtimes such as wasmtime.

SQLite persistence in browser uses sql.js (SQLite compiled to WASM).

Floating-point conformance: WASM FP is IEEE 754 compliant.
The C emitter provides the conformance helpers which are used by WASM.
"""

from typing import Any

_WASM_BROWSER_BUILD = (
    'clang --target=wasm32 --no-standard-libraries '
    '-Wl,--no-entry -Wl,--export-all -o app.wasm app.c'
)
_WASM_WASI_BUILD = 'clang --target=wasm32-wasi -o app.wasm app.c'


def wasm_build_command(mode: str = 'browser') -> str:
    """Return the clang invocation that compiles app.c into app.wasm."""
    if mode == 'wasi':
        return _WASM_WASI_BUILD
    return _WASM_BROWSER_BUILD


def _c_source(mir: Any) -> str:
    """Emit C via the C emitter, adapting defensively if the module changed."""
    try:
        from omni_compiler import c_emitter  # noqa: PLC0415 - lazy import re-reads peer module

        return c_emitter.emit_c(mir)
    except Exception:
        return '// C emitter unavailable; re-read c_emitter.py and adapt.'


def _glue_imports() -> list[str]:
    """JS import shim that maps printf to console.log and allocates memory."""
    return [
        '// WASM import shim (app.js): maps printf to console.log.',
        'const memory = new WebAssembly.Memory({ initial: 256 });',
        'function _mirror(text) {',
        "  const out = document.getElementById('output');",
        '  if (out) { out.textContent += String(text) + String.fromCharCode(10); }',
        '}',
        'function wasmPrintf(fmt) {',
        '  const args = Array.prototype.slice.call(arguments, 1);',
        '  let i = 0;',
        '  const msg = String(fmt).replace(/%[a-zA-Z]/g, function () {',
        "    return i < args.length ? String(args[i++]) : '';",
        '  });',
        "  console.log('[wasm] ' + msg);",
        '  _mirror(msg);',
        '  return msg.length;',
        '}',
        'const imports = {',
        '  env: {',
        '    memory: memory,',
        '    printf: wasmPrintf,',
        '    emscripten_notify_memory_growth: function (index) {',
        "      console.log('[wasm] memory growth notification:', index);",
        '    },',
        '  },',
        '};',
        '',
    ]


def _default_arg(omni_type: str) -> str:
    """Return a neutral default argument value for an OmniScript type."""
    return {
        'Number': '0',
        'Text': '0',
        'Boolean': '0',
        'List': '0',
        'None': '0',
    }.get(omni_type, '0')


def _export_calls(mir: Any) -> list[str]:
    """JS wrappers that call each exported wasm function once."""
    lines = ['// Call every exported WASM function once for a smoke check.']
    lines.append('function callExports(instance) {')
    for fn in mir.functions.values():
        args = ', '.join(_default_arg(p.type) for p in fn.params)
        if not args:
            args = '0'
        lines.append(f"  const {fn.name} = instance.exports['{fn.name}'];")
        lines.append(f"  if (typeof {fn.name} === 'function') {{")
        lines.append(f"    console.log('calling wasm export {fn.name}()');")
        lines.append(f'    {fn.name}({args});')
        lines.append('  }')
    lines.append('}')
    lines.append('')
    return lines


def _load_glue() -> list[str]:
    """JS loader that instantiates the wasm module via fetch."""
    return [
        'async function loadApp() {',
        "  // glue pattern: WebAssembly.instantiateStreaming(fetch('app.wasm'), {})",
        '  try {',
        '    const { instance } = await '
        "WebAssembly.instantiateStreaming(fetch('app.wasm'), imports);",
        "    console.log('wasm module instantiated');",
        '    callExports(instance);',
        '  } catch (err) {',
        "    console.warn('instantiateStreaming failed, falling back:', err);",
        "    const bytes = await (await fetch('app.wasm')).arrayBuffer();",
        '    const { instance } = await WebAssembly.instantiate(bytes, imports);',
        '    callExports(instance);',
        '  }',
        '}',
        'loadApp();',
        '',
    ]


def _scene_js(mir: Any) -> list[str]:
    """Reuse the JS emitter's Three.js scene snippet when available."""
    try:
        from omni_compiler import emitter  # noqa: PLC0415 - lazy import re-reads peer-edited module

        scene_fn = getattr(emitter, '_js_scene', None)
        if scene_fn is None:
            return []
        return list(scene_fn(mir))
    except Exception:
        return []


def _sqlite_js_glue() -> list[str]:
    """JS glue for sql.js (SQLite in WASM) persistence."""
    return [
        '// sql.js (SQLite WASM) integration for db persistence',
        'let _sqlJsDb = null;',
        'let _sqlJsFile = null;',
        '',
        'async function initSqlJsDb(path) {',
        '  const SQL = await initSqlJs({ locateFile: (file) => `https://sql.js.org/dist/${file}` });',  # noqa: E501
        '  if (!path || path === ":memory:") {',
        '    _sqlJsDb = new SQL.Database();',
        '    _sqlJsFile = null;',
        '  } else {',
        '    try {',
        '      const response = await fetch(path);',
        '      if (response.ok) {',
        '        const arrayBuffer = await response.arrayBuffer();',
        '        _sqlJsFile = new Uint8Array(arrayBuffer);',
        '        _sqlJsDb = new SQL.Database(_sqlJsFile);',
        '      } else {',
        '        _sqlJsDb = new SQL.Database();',
        '        _sqlJsFile = null;',
        '      }',
        '    } catch {',
        '      _sqlJsDb = new SQL.Database();',
        '      _sqlJsFile = null;',
        '    }',
        '  }',
        '  _sqlJsDb.run("PRAGMA foreign_keys = ON");',
        '}',
        '',
        'function sqlJsQuery(sql, params) {',
        '  if (!_sqlJsDb) throw new Error("No database open. Call db_open() first.");',
        '  const stmt = _sqlJsDb.prepare(sql);',
        '  const results = [];',
        '  if (params && params.length) {',
        '    stmt.bind(params);',
        '  }',
        '  while (stmt.step()) {',
        '    results.push(stmt.getAsObject());',
        '  }',
        '  stmt.free();',
        '  return results;',
        '}',
        '',
        'function sqlJsExec(sql, params) {',
        '  if (!_sqlJsDb) throw new Error("No database open. Call db_open() first.");',
        '  const stmt = _sqlJsDb.prepare(sql);',
        '  if (params && params.length) {',
        '    stmt.bind(params);',
        '  }',
        '  stmt.step();',
        '  const changes = _sqlJsDb.getRowsModified();',
        '  stmt.free();',
        '  if (_sqlJsFile !== null) {',
        '    _sqlJsFile = _sqlJsDb.export();',
        '  }',
        '  return changes;',
        '}',
        '',
        'function sqlJsClose() {',
        '  if (_sqlJsDb) {',
        '    if (_sqlJsFile !== null) {',
        '      _sqlJsFile = _sqlJsDb.export();',
        '    }',
        '    _sqlJsDb.close();',
        '    _sqlJsDb = null;',
        '  }',
        '}',
        '',
        'function sqlJsExport() {',
        '  if (!_sqlJsDb || _sqlJsFile === null) return null;',
        '  return _sqlJsFile;',
        '}',
        '',
    ]


def emit_wasm_browser(mir: Any) -> str:
    """Emit a self-contained HTML page that loads the wasm build with sql.js."""
    c_code = _c_source(mir)
    build = wasm_build_command('browser')
    scene_js = _scene_js(mir)

    js = [
        '// Generated by OmniScript WASM Emitter (v3.4) — browser mode',
        f'// build: {build}',
        '// Compile with the build comment, then serve this page beside app.wasm.',
        '// Includes sql.js for SQLite persistence.',
        '',
    ]
    js.extend(_glue_imports())
    js.extend(_sqlite_js_glue())
    js.extend(_export_calls(mir))
    js.extend(_load_glue())
    js.extend(scene_js)

    body = '\n'.join(js)
    return '\n'.join(
        [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <meta charset="utf-8"><title>OmniScript WASM App</title>',
            '  <script src="https://sql.js.org/dist/sql-wasm.js"></script>',
            '</head>',
            '<body>',
            '  <canvas id="wasm-canvas" width="512" height="512"></canvas>',
            '  <div id="output"></div>',
            '  <script type="text/emscripten">',
            '  // C source emitted by the OmniScript C Emitter (compile with the build comment).',
            c_code,
            '  </script>',
            '  <script>',
            body,
            '  </script>',
            '</body>',
            '</html>',
        ]
    )


def emit_wasm_wasi(mir: Any) -> str:
    """Emit C source targeting wasm32-wasi for server/edge runtimes."""
    c_code = _c_source(mir)
    header = [
        '// Generated by OmniScript WASM Emitter (v3.3) — wasi mode',
        f'// build: {wasm_build_command("wasi")}',
        '// run: wasmtime app.wasm',
        '',
    ]
    return '\n'.join(header + [c_code])


def emit_wasm(mir: Any, mode: str = 'browser') -> str:
    """Emit a WASM target for the given MIR (browser HTML or wasi C source)."""
    if mode == 'wasi':
        return emit_wasm_wasi(mir)
    return emit_wasm_browser(mir)
