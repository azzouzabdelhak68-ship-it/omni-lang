"""JS Emitter Module
Generates a self-contained ES6 HTML document from OMNI MIR with
live-link batching at the end of each top-level block.
"""

from pathlib import Path
from typing import Any

from omni_compiler.omnisys_registry import js_files_for

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _omnisys_runtime(mir: Any) -> list[str]:
    """Inline the JS sources of the imported OMNISYS modules (deps first)."""
    if not mir.imports:
        return []
    files = js_files_for(mir.imports)
    lines: list[str] = ["// OMNISYS runtime (inlined, dependency-ordered)", "// import OMNISYS[.<module>] -> portable standard library"]
    for rel in files:
        source = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        lines.append(source.rstrip())
        lines.append("")
    return lines


def _js_text(raw: str) -> str:
    """Render an OmniScript text literal (with {expr} slots) as JS expression."""
    if len(raw) >= 2 and raw[0] in ('"', "'"):
        body = raw[1:-1]
    else:
        body = raw
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "{":
            j = body.find("}", i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1:j]
            if buf:
                parts.append('"' + "".join(buf) + '"')
                buf = []
            parts.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        parts.append('"' + "".join(buf) + '"')
    if not parts:
        return '""'
    return " + ".join(parts)


def _js_expr(e: dict[str, Any], params: set[str]) -> str:
    op = e.get("op")
    if op == "number":
        return str(e["value"])
    if op == "boolean":
        return "true" if e["value"] else "false"
    if op == "none":
        return "null"
    if op == "ident":
        return e["name"]
    if op == "text":
        return _js_text(e["value"])
    if op == "call":
        if e["name"] == "join" and len(e["args"]) == 2:
            return f"({_js_expr(e['args'][0], params)}).join({_js_expr(e['args'][1], params)})"
        return f"{e['name']}({', '.join(_js_expr(a, params) for a in e['args'])})"
    if op == "list":
        return "[" + ", ".join(_js_expr(i, params) for i in e["items"]) + "]"
    if op == "field":
        return f"{_js_expr(e['object'], params)}.{e['field']}"
    if op == "struct":
        parts = [f"{name}: {_js_expr(value, params)}" for name, value in e["args"].items()]
        return "{" + ", ".join(parts) + "}"
    if op == "is":
        jop = "==="
    elif op == "is not":
        jop = "!=="
    elif op == "and":
        jop = "&&"
    elif op == "or":
        jop = "||"
    elif op == "greater than":
        jop = ">"
    elif op == "less than":
        jop = "<"
    elif op == "greater or equal":
        jop = ">="
    elif op == "less or equal":
        jop = "<="
    else:
        jop = op
    return f"{_js_expr(e['left'], params)} {jop} {_js_expr(e['right'], params)}"


def _js_stmt(s: dict[str, Any], params: set[str]) -> str:
    op = s.get("op")
    if op == "assign":
        return f"{s['name']} = {_js_expr(s['expr'], params)};"
    if op == "return":
        return f"return {_js_expr(s['expr'], params)};"
    if op == "show":
        return f"console.log({_js_expr(s['expr'], params)});"
    if op == "call":
        return f"{_js_expr(s, params)};"
    if op == "break":
        return "break;"
    if op == "continue":
        return "continue;"
    if op == "if":
        lines = [f"if ({_js_expr(s['cond'], params)}) {{"]
        for st in s["body"]:
            lines.append("  " + _js_stmt(st, params))
        lines.append("}")
        if s.get("else"):
            lines.append("else {")
            for st in s["else"]:
                lines.append("  " + _js_stmt(st, params))
            lines.append("}")
        return "\n".join(lines)
    if op == "for":
        lines = [f"for (const {s['var']} of {_js_expr(s['iterable'], params)}) {{"]
        for st in s["body"]:
            lines.append("  " + _js_stmt(st, params))
        lines.append("}")
        return "\n".join(lines)
    return f"// unknown statement: {s!r}"


def _js_template(html: str) -> str:
    """Convert {slot} HTML placeholders to JS template-literal ${slot}."""
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(html):
        if html[i] == "{":
            j = html.find("}", i)
            if j == -1:
                buf.append(html[i:])
                break
            slot = html[i + 1:j]
            if buf:
                out.append("".join(buf))
                buf = []
            out.append("${" + slot + "}")
            i = j + 1
        else:
            buf.append(html[i])
            i += 1
    if buf:
        out.append("".join(buf))
    return "".join(out)


def _js_attr_value(v: dict[str, Any], params: set[str]) -> str:
    if v.get("op") == "slot":
        return _js_expr(v["expr"], params)
    return _js_expr(v, params)


def _js_scene_number(v: dict[str, Any], params: set[str]) -> str:
    """Render a scene attribute value as a JS number (quoted numerics become numbers)."""
    raw = _js_attr_value(v, params)
    if v.get("op") == "text":
        val = str(v["value"])
        return str(float(val)) if _is_numeric(val) else raw
    return raw


def _is_numeric(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    return True


def _js_scene(mir: Any) -> list[str]:
    if not mir.scene:
        return []
    lines: list[str] = []
    lines.append("// 3D scene (Three.js)")
    lines.append('const three = document.createElement("script");')
    lines.append('three.src = "https://cdn.jsdelivr.net/npm/three@0.152.0/build/three.min.js";')
    lines.append('three.onload = function() { initScene(); };')
    lines.append('document.head.appendChild(three);')
    lines.append("")
    lines.append("function initScene() {")
    lines.append("  const scene = new THREE.Scene();")
    lines.append("  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);")
    lines.append("  camera.position.z = 5;")
    lines.append("  const renderer = new THREE.WebGLRenderer();")
    lines.append("  renderer.setSize(window.innerWidth, window.innerHeight);")
    lines.append('  document.body.appendChild(renderer.domElement);')
    lines.append("")

    material_idx = 0
    for obj in mir.scene:
        shape = obj["shape"]
        attrs = obj.get("attrs", {})
        color = attrs.get("color", {"op": "text", "value": '"#ffffff"'})
        size = attrs.get("size", {"op": "number", "value": 1})
        if shape == "box":
            sz = _js_scene_number(size, set())
            lines.append(f'  const box_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.BoxGeometry({sz}, {sz}, {sz}),')
            lines.append(f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})')
            lines.append("  );")
        elif shape == "sphere":
            sz = _js_scene_number(size, set())
            lines.append(f'  const sphere_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.SphereGeometry({sz} / 2, 32, 16),')
            lines.append(f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})')
            lines.append("  );")
        elif shape == "cylinder":
            sz = _js_scene_number(size, set())
            lines.append(f'  const cylinder_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.CylinderGeometry({sz} / 2, {sz} / 2, {sz}, 32),')
            lines.append(f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})')
            lines.append("  );")
        elif shape == "plane":
            sz = _js_scene_number(size, set())
            lines.append(f'  const plane_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.PlaneGeometry({sz}, {sz}),')
            lines.append(f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})')
            lines.append("  );")
        elif shape == "light":
            light_type = attrs.get("type", {"op": "text", "value": '"directional"'})
            light_js_type = {
                "directional": "DirectionalLight",
                "point": "PointLight",
                "ambient": "AmbientLight",
                "spot": "SpotLight",
            }.get("directional", "DirectionalLight")
            lt = _js_attr_value(light_type, set()).strip('"')
            light_js_type = {
                "directional": "DirectionalLight",
                "point": "PointLight",
                "ambient": "AmbientLight",
                "spot": "SpotLight",
            }.get(lt, "DirectionalLight")
            intensity = attrs.get("intensity", {"op": "number", "value": 1})
            lines.append(f'  const light_{material_idx} = new THREE.{light_js_type}({_js_attr_value(color, set())}, {_js_scene_number(intensity, set())});')
        elif shape == "camera":
            pos = attrs.get("pos", {"op": "text", "value": '"0,0,5"'})
            coords = _js_attr_value(pos, set()).strip('"').split(",")
            coords = [c.strip() for c in coords]
            if len(coords) == 3:
                lines.append(f"  camera.position.set({coords[0]}, {coords[1]}, {coords[2]});")

        var_name = f"{shape}_{material_idx}"
        if shape != "light" and shape != "camera":
            pos = attrs.get("pos")
            if pos:
                coords = _js_attr_value(pos, set()).strip('"').split(",")
                coords = [c.strip() for c in coords]
                if len(coords) == 3:
                    lines.append(f"  {var_name}.position.set({coords[0]}, {coords[1]}, {coords[2]});")
            lines.append(f"  scene.add({var_name});")
        elif shape == "light":
            lines.append(f"  scene.add(light_{material_idx});")
        material_idx += 1

    lines.append("")
    lines.append("  function animate() {")
    lines.append("    requestAnimationFrame(animate);")
    lines.append("    renderer.render(scene, camera);")
    lines.append("  }")
    lines.append("  animate();")
    lines.append("}")
    lines.append("")
    return lines


def emit_js(mir: Any) -> str:
    """Emit a self-contained HTML document with embedded ES6 JS from OMNI MIR."""
    js: list[str] = []
    js.append("// Generated by the OmniScript JS Emitter")
    js.extend(_omnisys_runtime(mir))
    if mir.imports:
        js.append("// OMNISYS namespace: omnisys.<module>.<fn>")
        js.append("")

    # Emit custom type declarations as TS-style interface JSDoc.
    for tname, fields in mir.types.items():
        js.append(f"// interface {tname} {{")
        for fname, ftype in fields.items():
            js.append(f"//   {fname}: {ftype};")
        js.append("// }")
    if mir.types:
        js.append("")

    # Collect variable names that must be declared at module scope.
    needed: set[str] = set()
    for fn in mir.functions.values():
        for stmt in fn.body:
            if stmt.get("op") == "assign":
                needed.add(stmt["name"])
    for stmt in mir.entry_point:
        if stmt.get("op") == "assign":
            needed.add(stmt["name"])
    param_names: set[str] = set()
    for fn in mir.functions.values():
        param_names.update(p.name for p in fn.params)
    for v in sorted(needed - param_names):
        js.append(f"let {v};")
    js.append("")

    template = _js_template(mir.ui_template) if mir.ui_template else "<p></p>"
    js.append("function renderUI() {")
    js.append(f'  document.getElementById("app").innerHTML = `{template}`;')
    js.append("}")
    js.append("")
    js.append("function batchUpdate(fn) {")
    js.append("  fn();")
    js.append("  renderUI();")
    js.append("}")
    js.append("")

    for fn in mir.functions.values():
        params = ", ".join(p.name for p in fn.params)
        async_pref = "async " if "network" in fn.effects.uses else ""
        js.append(f"{async_pref}function {fn.name}({params}) {{")
        if fn.effects.uses:
            js.append(f"  // capability: {', '.join(fn.effects.uses)}")
        fn_params = set(p.name for p in fn.params)
        for stmt in fn.body:
            js.append("  " + _js_stmt(stmt, fn_params))
        js.append("}")
        js.append("")

    if mir.entry_point:
        js.append("batchUpdate(function() {")
        for stmt in mir.entry_point:
            js.append("  " + _js_stmt(stmt, set()))
        js.append("});")
        js.append("")

    js.append("bindClicks();")
    js.append("function bindClicks() {")
    js.append('  document.querySelectorAll("[click]").forEach(function(el) {')
    js.append('    el.onclick = function() { batchUpdate(window[el.getAttribute("click")]); };')
    js.append("  });")
    js.append("}")

    scene_js = _js_scene(mir)
    if scene_js:
        js.append("")
        js.extend(scene_js)

    body = "\n".join(js)
    return "\n".join([
        "<!DOCTYPE html>",
        "<html>",
        '<head><meta charset="utf-8"><title>OmniScript App</title></head>',
        "<body>",
        '  <div id="app"></div>',
        "  <script>",
        body,
        "  </script>",
        "</body>",
        "</html>",
    ])


def emit_js_with_runtime(mir: Any) -> str:
    """Emit a complete HTML file with embedded JS runtime (alias of emit_js)."""
    return emit_js(mir)