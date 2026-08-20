"""JS Emitter Module.

Generates a self-contained ES6 HTML document from OMNI MIR with
live-link batching at the end of each top-level block.
"""

from pathlib import Path
from typing import Any

from omni_compiler.omnisys_registry import js_files_for


def _fp_is_nan(x: float) -> bool:
    """Check if value is NaN (JS: Number.isNaN)."""
    return x != x  # noqa: PLR0124


def _fp_is_finite(x: float) -> bool:
    """Check if value is finite (JS: Number.isFinite)."""
    return x != float('inf') and x != float('-inf') and x == x  # noqa: PLR0124


def _fp_is_infinite(x: float) -> bool:
    """Check if value is infinite (JS: !Number.isFinite && !Number.isNaN)."""
    return x == float('inf') or x == float('-inf')


def _fp_divide(a: float, b: float) -> float:
    """IEEE 754 division with proper edge cases."""
    if b == 0.0:
        if a == 0.0:
            return float('nan')
        return float('inf') if a > 0 else float('-inf')
    return a / b


def _fp_modulo(a: float, b: float) -> float:
    """IEEE 754 remainder with proper edge cases."""
    if b == 0.0 or a != a or b != b:  # noqa: PLR0124, PLR1714
        return float('nan')
    if a == float('inf') or a == float('-inf'):
        return float('nan')
    return a % b


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _assigned_names(stmts: list[dict[str, Any]]) -> set[str]:
    """Recursively collect all `assign` targets in a statement list.

    Includes names first assigned inside nested if/for blocks.
    """
    names: set[str] = set()
    for stmt in stmts:
        op = stmt.get('op')
        if op == 'assign':
            names.add(stmt['name'])
        elif op == 'if':
            names |= _assigned_names(stmt.get('body', []))
            names |= _assigned_names(stmt.get('else', []))
        elif op == 'for' or op == 'while':  # noqa: PLR1714
            names |= _assigned_names(stmt.get('body', []))
        elif op == 'try':
            names |= _assigned_names(stmt.get('body', []))
            names |= _assigned_names(stmt.get('on_error', []))
            names |= _assigned_names(stmt.get('finally', []))
        elif op == 'global':
            names.add(stmt['name'])
    return names


def _fp_runtime_helpers() -> list[str]:
    """Emit IEEE 754 floating-point conformance helpers for JS."""
    return [
        '// IEEE 754 Floating-Point Conformance Helpers',
        'const OmniFP = {',
        '  isNaN: (x) => x !== x,',
        '  isFinite: (x) => x !== Infinity && x !== -Infinity && x === x,',
        '  isInfinite: (x) => x === Infinity || x === -Infinity,',
        '  divide: (a, b) => {',
        '    // Use native division which preserves sign of zero',
        '    return a / b;',
        '  },',
        '  modulo: (a, b) => {',
        '    if (b === 0 || a !== a || b !== b) return NaN;',
        '    if (a === Infinity || a === -Infinity) return NaN;',
        '    return a % b;',
        '  },',
        '  negZero: () => -0,',
        '  copySign: (x, y) => Math.abs(x) * (y < 0 || Object.is(y, -0) ? -1 : 1),',
        '};',
        '',
    ]


def _omnisys_runtime(mir: Any) -> list[str]:
    """Inline the JS sources of the imported OMNISYS modules (deps first)."""
    files = js_files_for(mir.imports) if mir.imports else []
    lines: list[str] = []
    if files:
        lines.append('// OMNISYS runtime (inlined, dependency-ordered)')
        lines.append('// import OMNISYS[.<module>] -> portable standard library')
    lines.extend(_fp_runtime_helpers())
    for rel in files:
        source = (_REPO_ROOT / rel).read_text(encoding='utf-8')
        lines.append(source.rstrip())
        lines.append('')
    return lines


def _js_text(raw: str) -> str:
    r"""Render an OmniScript text literal (with {expr} slots) as JS expression.

    ``\{`` and ``\}`` are literal braces; ``{expr}`` interpolates an expression.
    """
    if len(raw) >= 2 and raw[0] in ('"', "'"):  # noqa: PLR2004, SIM108
        body = raw[1:-1]
    else:
        body = raw
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i + 1] in '{}.':  # noqa: PLR2004
            buf.append(body[i + 1])
            i += 2
        elif body[i] == '{':
            j = body.find('}', i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1 : j]
            if buf:
                parts.append('"' + ''.join(buf) + '"')
                buf = []
            parts.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        parts.append('"' + ''.join(buf) + '"')
    if not parts:
        return '""'
    return ' + '.join(parts)


def _js_expr(e: dict[str, Any], params: set[str]) -> str:  # noqa: PLR0911, PLR0912, PLR0915
    op = e.get('op')
    if op == 'number':
        return str(e['value'])
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return 'null'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        return _js_text(e['value'])
    if op == 'call':
        if e['name'] == 'join' and len(e['args']) == 2:  # noqa: PLR2004
            return f'({_js_expr(e["args"][0], params)}).join({_js_expr(e["args"][1], params)})'
        if e['name'] == 'range' and len(e['args']) == 1:
            return f'Array.from({{length: {_js_expr(e["args"][0], params)}}}, (_, i) => i)'
        return f'{e["name"]}({", ".join(_js_expr(a, params) for a in e["args"])})'
    if op == 'list':
        return '[' + ', '.join(_js_expr(i, params) for i in e['items']) + ']'
    if op == 'map':
        pairs = []
        for k, v in e['items'].items():
            quoted = _js_text('"' + k + '"')
            pairs.append(f'{quoted}: {_js_expr(v, params)}')
        return '{' + ', '.join(pairs) + '}'
    if op == 'index':
        return f'{_js_expr(e["object"], params)}[{_js_expr(e["index"], params)}]'
    if op == 'await':
        return f'await {_js_expr(e["expr"], params)}'
    if op == 'field':
        return f'{_js_expr(e["object"], params)}.{e["field"]}'
    if op == 'struct':
        parts = [f'{name}: {_js_expr(value, params)}' for name, value in e['args'].items()]
        return '{' + ', '.join(parts) + '}'
    if op == 'fn_literal':
        fn_params = ', '.join(p['name'] for p in e['params'])
        body_lines = []
        for stmt in e['body']:
            body_lines.append(
                '  ' + _js_stmt(stmt, set(fn_params.split(', ')) if fn_params else set())
            )
        body = '\n'.join(body_lines) if body_lines else ''
        return f'function({fn_params}) {{\n{body}\n}}'
    if op == 'group':
        return f'({_js_expr(e["expr"], params)})'
    if op == 'not':
        return f'!({_js_expr(e["operand"], params)})'
    if op == 'neg':
        operand = e['operand']
        if operand.get('op') == 'number' and operand.get('value') == 0:
            return '-0'
        return f'-({_js_expr(operand, params)})'
    if op == 'is':
        jop: str = '==='
    elif op == 'is not':
        jop = '!=='
    elif op == 'and':
        jop = '&&'
    elif op == 'or':
        jop = '||'
    elif op == '|>':
        # Pipe: x |> f  becomes  f(x)
        left_expr = _js_expr(e['left'], params)
        right_expr = _js_expr(e['right'], params)
        return f'{right_expr}({left_expr})'
    elif op == 'greater than':
        jop = '>'
    elif op == 'less than':
        jop = '<'
    elif op == 'greater or equal':
        jop = '>='
    elif op == 'less or equal':
        jop = '<='
    elif op == '/':
        return f'OmniFP.divide({_js_expr(e["left"], params)}, {_js_expr(e["right"], params)})'
    elif op == '%':
        return f'OmniFP.modulo({_js_expr(e["left"], params)}, {_js_expr(e["right"], params)})'
    else:
        jop = str(op)
    return f'{_js_expr(e["left"], params)} {jop} {_js_expr(e["right"], params)}'


def _js_stmt(s: dict[str, Any], params: set[str]) -> str:  # noqa: PLR0911, PLR0912
    op = s.get('op')
    if op == 'assign':
        return f'{s["name"]} = {_js_expr(s["expr"], params)};'
    if op == 'return':
        return f'return {_js_expr(s["expr"], params)};'
    if op == 'show':
        return f'console.log({_js_expr(s["expr"], params)});'
    if op == 'call':
        return f'{_js_expr(s, params)};'
    if op == 'break':
        return 'break;'
    if op == 'continue':
        return 'continue;'
    if op == 'if':
        lines = [f'if ({_js_expr(s["cond"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        if s.get('else'):
            lines.append('else {')
            for st in s['else']:
                lines.append('  ' + _js_stmt(st, params))
            lines.append('}')
        return '\n'.join(lines)
    if op == 'for':
        lines = [f'for (const {s["var"]} of {_js_expr(s["iterable"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'while ({_js_expr(s["cond"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        return '\n'.join(lines)
    if op == 'try':
        lines = ['try {']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('} catch (_e) {')
        if s.get('error_var'):
            lines.append(f'  const {s["error_var"]} = String(_e && _e.message ? _e.message : _e);')
        for st in s.get('on_error', []):
            lines.append('  ' + _js_stmt(st, params))
        if s.get('finally'):
            lines.append('} finally {')
            for st in s['finally']:
                lines.append('  ' + _js_stmt(st, params))
            lines.append('}')
        else:
            lines.append('}')
        return '\n'.join(lines)
    if op == 'global':
        return f'// global {s["name"]}'
    return f'// unknown statement: {s!r}'


def _is_style_open(html: str, i: int) -> bool:
    """Return True when the ``<style`` open tag begins at ``i`` in ``html``."""
    return html[i : i + 6].lower() == '<style' and (i + 6 >= len(html) or html[i + 6] in '> \t\r\n')


def _is_style_close(html: str, i: int) -> bool:
    """Return True when the ``</style`` close tag begins at ``i`` in ``html``."""
    return html[i : i + 7].lower() == '</style' and (
        i + 7 >= len(html) or html[i + 7] in '> \t\r\n'
    )


def _js_template(html: str) -> str:  # noqa: PLR0912, PLR0915
    """Convert {slot} HTML placeholders to JS template-literal ${slot}.

    ``{{`` and ``}}`` are literal braces. Inside ``<style>`` blocks every
    brace is literal too, so CSS rules like ``.panel { padding: 8px; }``
    survive untouched instead of being mangled into ``${ ... }`` slots.
    """
    out: list[str] = []
    buf: list[str] = []
    i = 0
    in_style = False
    while i < len(html):
        if html[i] == '<':
            if not in_style and _is_style_open(html, i):
                in_style = True
            elif in_style and _is_style_close(html, i):
                in_style = False
        if in_style:
            if html[i] == '{':
                if i + 1 < len(html) and html[i + 1] == '{':
                    buf.append('{')
                    i += 2
                    continue
                buf.append('{')
                i += 1
                continue
            if html[i] == '}':
                if i + 1 < len(html) and html[i + 1] == '}':
                    buf.append('}')
                    i += 2
                    continue
                buf.append('}')
                i += 1
                continue
            buf.append(html[i])
            i += 1
            continue
        if html[i] == '{':
            if i + 1 < len(html) and html[i + 1] == '{':
                buf.append('{')
                i += 2
                continue
            j = html.find('}', i)
            if j == -1:
                buf.append(html[i:])
                break
            slot = html[i + 1 : j]
            if buf:
                out.append(''.join(buf))
                buf = []
            out.append('${' + slot + '}')
            i = j + 1
        elif html[i] == '}':
            if i + 1 < len(html) and html[i + 1] == '}':
                buf.append('}')
                i += 2
                continue
            buf.append(html[i])
            i += 1
        else:
            buf.append(html[i])
            i += 1
    if buf:
        out.append(''.join(buf))
    return ''.join(out)


def _js_attr_value(v: dict[str, Any], params: set[str]) -> str:
    if v.get('op') == 'slot':
        return _js_expr(v['expr'], params)
    return _js_expr(v, params)


def _js_scene_number(v: dict[str, Any], params: set[str]) -> str:
    """Render a scene attribute value as a JS number (quoted numerics become numbers)."""
    raw = _js_attr_value(v, params)
    if v.get('op') == 'text':
        val = str(v['value'])
        return str(float(val)) if _is_numeric(val) else raw
    return raw


def _js_scene_pos_set(var_name: str, pos: dict[str, Any], params: set[str]) -> list[str]:
    """Emit position.set(...) for a scene object's `pos` attribute.

    Literal text positions ("1,2,3") are split at compile time; slot-valued
    positions ({var}) are split at runtime since the value isn't known yet.
    """
    if pos.get('op') == 'text':
        coords = [c.strip() for c in str(pos['value']).strip('"').split(',')]
        if len(coords) == 3:  # noqa: PLR2004
            return [f'  {var_name}.position.set({coords[0]}, {coords[1]}, {coords[2]});']
        return []
    expr_js = _js_attr_value(pos, params)
    return [
        '  (function() {',
        f"    const _p = String({expr_js}).split(',').map(Number);",
        f'    if (_p.length === 3) {var_name}.position.set(_p[0], _p[1], _p[2]);',
        '  })();',
    ]


def _is_numeric(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    return True


def _js_scene(mir: Any) -> list[str]:  # noqa: PLR0915
    if not mir.scene:
        return []
    lines: list[str] = []
    lines.append('// 3D scene (Three.js)')
    lines.append('let __omniSceneReady = false;')
    lines.append(
        'if (typeof document !== "undefined" && typeof document.createElement === "function") {'
    )  # noqa: E501
    lines.append('  const three = document.createElement("script");')
    lines.append('  three.src = "https://cdn.jsdelivr.net/npm/three@0.152.0/build/three.min.js";')
    lines.append('  three.onload = function() { initScene(); };')
    lines.append('  document.head.appendChild(three);')
    lines.append('  if (typeof THREE !== "undefined") initScene();')
    lines.append('}')
    lines.append('')
    lines.append('function initScene() {')
    lines.append('  if (__omniSceneReady) return;')
    lines.append('  __omniSceneReady = true;')
    lines.append('  const scene = new THREE.Scene();')
    lines.append(
        '  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);'  # noqa: E501
    )  # noqa: E501
    lines.append('  camera.position.z = 5;')
    lines.append('  const renderer = new THREE.WebGLRenderer();')
    lines.append('  renderer.setSize(window.innerWidth, window.innerHeight);')
    lines.append('  document.body.appendChild(renderer.domElement);')
    lines.append('')

    material_idx = 0
    for obj in mir.scene:
        shape = obj['shape']
        attrs = obj.get('attrs', {})
        color = attrs.get('color', {'op': 'text', 'value': '"#ffffff"'})
        size = attrs.get('size', {'op': 'number', 'value': 1})
        if shape == 'box':
            sz = _js_scene_number(size, set())
            lines.append(f'  const box_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.BoxGeometry({sz}, {sz}, {sz}),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'sphere':
            sz = _js_scene_number(size, set())
            lines.append(f'  const sphere_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.SphereGeometry({sz} / 2, 32, 16),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'cylinder':
            sz = _js_scene_number(size, set())
            lines.append(f'  const cylinder_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.CylinderGeometry({sz} / 2, {sz} / 2, {sz}, 32),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'plane':
            sz = _js_scene_number(size, set())
            lines.append(f'  const plane_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.PlaneGeometry({sz}, {sz}),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'light':
            light_type = attrs.get('type', {'op': 'text', 'value': '"directional"'})
            light_js_type = {
                'directional': 'DirectionalLight',
                'point': 'PointLight',
                'ambient': 'AmbientLight',
                'spot': 'SpotLight',
            }.get('directional', 'DirectionalLight')
            lt = _js_attr_value(light_type, set()).strip('"')
            light_js_type = {
                'directional': 'DirectionalLight',
                'point': 'PointLight',
                'ambient': 'AmbientLight',
                'spot': 'SpotLight',
            }.get(lt, 'DirectionalLight')
            intensity = attrs.get('intensity', {'op': 'number', 'value': 1})
            lines.append(
                f'  const light_{material_idx} = new THREE.{light_js_type}({_js_attr_value(color, set())}, {_js_scene_number(intensity, set())});'  # noqa: E501
            )  # noqa: E501
        elif shape == 'camera':
            pos = attrs.get('pos', {'op': 'text', 'value': '0,0,5'})
            lines.extend(_js_scene_pos_set('camera', pos, set()))

        var_name = f'{shape}_{material_idx}'
        if shape != 'light' and shape != 'camera':  # noqa: PLR1714
            pos = attrs.get('pos')
            if pos:
                lines.extend(_js_scene_pos_set(var_name, pos, set()))
            lines.append(f'  scene.add({var_name});')
        elif shape == 'light':
            lines.append(f'  scene.add(light_{material_idx});')
        material_idx += 1  # noqa: SIM113

    lines.append('')
    lines.append('  function animate() {')
    lines.append('    requestAnimationFrame(animate);')
    lines.append('    renderer.render(scene, camera);')
    lines.append('  }')
    lines.append('  animate();')
    lines.append('}')
    lines.append('')
    return lines


def emit_js(mir: Any) -> str:  # noqa: PLR0915
    """Emit a self-contained HTML document with embedded ES6 JS from OMNI MIR."""
    js: list[str] = []
    js.append('// Generated by the OmniScript JS Emitter')
    js.extend(_omnisys_runtime(mir))
    if mir.imports:
        js.append('// OMNISYS namespace: omnisys.<module>.<fn>')
        js.append('')

    # Emit custom type declarations as TS-style interface JSDoc.
    for tname, fields in mir.types.items():
        js.append(f'// interface {tname} {{')
        for fname, ftype in fields.items():
            js.append(f'//   {fname}: {ftype};')
        js.append('// }')
    if mir.types:
        js.append('')

    # Module-scope state: names assigned anywhere in the entry point (including
    # nested if/for). These persist across batchUpdate() invocations, so
    # functions and click handlers can read them. Names assigned only inside a
    # function body become function-local declarations (see the function loop).
    module_scope = _assigned_names(mir.entry_point)
    for v in sorted(module_scope):
        js.append(f'let {v};')
    js.append('')

    template = _js_template(mir.ui_template) if mir.ui_template else '<p></p>'
    js.append('function renderUI() {')
    js.append('  const app = document.getElementById("app");')
    js.append('  if (app) app.innerHTML = `' + template + '`;')
    js.append('}')
    js.append('')
    js.append('async function batchUpdate(fn) {')
    js.append('  await fn();')
    js.append('  renderUI();')
    js.append('}')
    js.append('')

    def _extract_cap_names(effects_list: list[Any]) -> list[Any]:
        """Extract capability names from effects list (handles both old string format and new tuple format)."""  # noqa: E501
        return [cap if isinstance(cap, str) else cap[0] for cap in effects_list]

    for fn in mir.functions.values():
        params = ', '.join(p.name for p in fn.params)
        uses = _extract_cap_names(fn.effects.uses)
        async_pref = 'async ' if 'network' in uses else ''
        js.append(f'{async_pref}function {fn.name}({params}) {{')
        if uses:
            js.append(f'  // capability: {", ".join(uses)}')
        fn_params = set(p.name for p in fn.params)
        fn_locals = sorted(_assigned_names(fn.body) - fn_params - module_scope)
        if fn_locals:
            js.append('  let ' + ', '.join(fn_locals) + ';')
        for stmt in fn.body:
            js.append('  ' + _js_stmt(stmt, fn_params))
        js.append('}')
        js.append('')

    if mir.entry_point:
        js.append('batchUpdate(async function() {')
        for stmt in mir.entry_point:
            js.append('  ' + _js_stmt(stmt, set()))
        js.append('});')
        js.append('')

    js.append('function bindClicks() {')
    js.append('  const app = document.getElementById("app");')
    js.append('  if (!app || typeof app.addEventListener !== "function") return;')
    js.append('  app.addEventListener("click", function(e) {')
    js.append('    const el = e.target.closest("[click]");')
    js.append('    if (!el) return;')
    js.append('    const fn = window[el.getAttribute("click")];')
    js.append('    if (typeof fn === "function") batchUpdate(fn);')
    js.append('  });')
    js.append('}')
    js.append('bindClicks();')
    js.append(
        'if (typeof omnisys !== "undefined" && omnisys.ui) '
        'omnisys.ui._setGlobalOnStateChange(batchUpdate);'
    )

    scene_js = _js_scene(mir)
    if scene_js:
        js.append('')
        js.extend(scene_js)

    body = '\n'.join(js)
    return '\n'.join(
        [
            '<!DOCTYPE html>',
            '<html>',
            '<head><meta charset="utf-8"><title>OmniScript App</title></head>',
            '<body>',
            '  <div id="app"></div>',
            '  <script>',
            body,
            '  </script>',
            '</body>',
            '</html>',
        ]
    )


def emit_js_with_runtime(mir: Any) -> str:
    """Emit a complete HTML file with embedded JS runtime (alias of emit_js)."""
    return emit_js(mir)
