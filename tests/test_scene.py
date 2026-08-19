"""v2.2: 3D scene: block — primitives, attributes, Three.js emission."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import TokenType, tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_lexer_scene_shape_keywords():
    tokens = tokenize(
        'scene:\n'
        'box size="2"\n'
        'sphere size="1.5" color="#ffffff"\n'
        'cylinder size="1"\n'
        'plane size="3"\n'
        'light type="directional" intensity="2"\n'
        'camera pos="0,0,5"\n'
        'end'
    )
    types = [t.type for t in tokens]
    assert TokenType.SCENE in types
    for shape in ('box', 'sphere', 'cylinder', 'plane', 'light', 'camera'):
        assert shape in [t.value for t in tokens]


def test_parse_scene_block():
    code = """
scene:
    box size="2" color="#e11d48"
    sphere size="1.5" color="#ffffff" pos="0,2,0"
    light type="directional" intensity="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert ast.scene_block is not None
    shapes = [obj.shape for obj in ast.scene_block.objects]
    assert shapes == ['box', 'sphere', 'light']


def test_parse_scene_attributes():
    code = """
scene:
    box size="2" color="#e11d48"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    obj = ast.scene_block.objects[0]
    assert obj.shape == 'box'
    assert obj.attrs['size'].value == '2'
    assert obj.attrs['color'].value == '#e11d48'


def test_parse_scene_live_link_slot():
    code = """
when app starts:
    my_color = "#00ff00"
end

scene:
    sphere size="1.5" color={my_color}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    obj = ast.scene_block.objects[0]
    slot = obj.attrs['color']
    assert slot.kind == 'slot'
    assert slot.expr.name == 'my_color'


def test_parse_scene_position_tuple():
    code = """
scene:
    sphere size="1.5" pos="0,2,0"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    obj = ast.scene_block.objects[0]
    assert obj.attrs['pos'].value == '0,2,0'


def test_checker_scene_valid():
    code = """
when app starts:
    color = "#e11d48"
end

scene:
    box size="2" color={color}
    light type="directional" intensity="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)


def test_checker_scene_unknown_attribute_fails():
    code = """
scene:
    box size="2" bogus_attr="1"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    try:
        analyze(ast)
    except Exception as exc:
        assert 'attribute' in str(exc).lower() or 'bogus_attr' in str(exc).lower()
    else:
        raise AssertionError('unknown scene attribute should fail')


def test_checker_scene_unknown_shape_fails():
    code = """
scene:
    dodecahedron size="2"
end
"""
    tokens = tokenize(code)
    try:
        parse(tokens)
    except Exception as exc:
        assert 'shape' in str(exc).lower() or 'dodecahedron' in str(exc).lower()
    else:
        raise AssertionError('unknown scene shape should fail')


def test_checker_scene_undefined_slot_fails():
    code = """
scene:
    sphere size="1.5" color={undefined_color}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    try:
        analyze(ast)
    except Exception as exc:
        assert 'undefined' in str(exc).lower()
    else:
        raise AssertionError('undefined slot variable should fail')


def test_checker_scene_live_link_expression():
    code = """
when app starts:
    r = 1.5
    g = 2.0
    size_val = r * g
end

scene:
    sphere size={size_val}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)


def test_mir_scene_graph():
    code = """
scene:
    box size="2" color="#e11d48"
    light type="directional" intensity="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert mir.scene is not None
    shapes = [o['shape'] for o in mir.scene]
    assert shapes == ['box', 'light']


def test_mir_scene_json_roundtrip():
    code = """
scene:
    box size="2" color="#e11d48"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    json_str = mir.to_json()
    assert 'scene' in json_str
    parsed = mir.from_json(json_str)
    assert parsed.scene[0]['shape'] == 'box'


def test_emitter_scene_threejs():
    code = """
scene:
    box size="2" color="#e11d48"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'THREE' in js_code
    assert 'WebGLRenderer' in js_code
    assert 'BoxGeometry' in js_code
    assert 'MeshStandardMaterial' in js_code


def test_emitter_scene_shapes():
    code = """
scene:
    box size="2"
    sphere size="1.5"
    cylinder size="1"
    plane size="3"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'BoxGeometry' in js_code
    assert 'SphereGeometry' in js_code
    assert 'CylinderGeometry' in js_code
    assert 'PlaneGeometry' in js_code


def test_emitter_scene_light():
    code = """
scene:
    light type="directional" intensity="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'DirectionalLight' in js_code
    assert 'DirectionalLight(' in js_code


def test_emitter_scene_camera_position():
    code = """
scene:
    camera pos="0,0,5"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'camera.position.set(0, 0, 5)' in js_code


def test_emitter_scene_live_link():
    code = """
when app starts:
    my_color = "#e11d48"
end

scene:
    sphere size="1.5" color={my_color}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'my_color' in js_code


def test_emitter_scene_animate_loop():
    code = """
scene:
    box size="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'requestAnimationFrame' in js_code
    assert 'animate' in js_code


def test_scene_snapshot():
    """Snapshot: emitted scene JS is stable and contains the full Three.js setup."""
    code = """
scene:
    sphere size="1.5" color="#ffffff" pos="0,2,0"
    light type="directional" intensity="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    snapshot_parts = [
        'new THREE.Scene()',
        'PerspectiveCamera',
        'new THREE.WebGLRenderer()',
        'SphereGeometry',
        'MeshStandardMaterial',
        'scene.add',
        'DirectionalLight',
    ]
    for part in snapshot_parts:
        assert part in js_code, f'missing snapshot part: {part}'


SCENE_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
global.__sets = [];
global.console = Object.assign({}, console, { log: () => {} });
global.document = {
  getElementById: () => ({ innerHTML: "", addEventListener: () => {} }),
  querySelectorAll: () => [],
  createElement: () => ({}),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
global.window = global;
global.requestAnimationFrame = () => {};
global.THREE = {
  Scene: function () { return { add() {} }; },
  PerspectiveCamera: function () { return { position: { set() {} } }; },
  WebGLRenderer: function () { return { setSize() {}, render() {}, domElement: {} }; },
  BoxGeometry: function () {},
  SphereGeometry: function () {},
  CylinderGeometry: function () {},
  PlaneGeometry: function () {},
  MeshStandardMaterial: function () {},
  Mesh: function () { return { position: { set: (...v) => global.__sets.push(v) } }; },
  DirectionalLight: function () {},
  PointLight: function () {},
  AmbientLight: function () {},
  SpotLight: function () {},
};
vm.runInThisContext(code, { filename: htmlPath });
if (typeof global.initScene === "function") {
  global.initScene();
}
process.stdout.write(JSON.stringify(global.__sets) + "\n");
"""


def _run_scene(html: str) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8', delete=False) as f:
        f.write(html)
        html_path = Path(f.name)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', encoding='utf-8', delete=False) as g:
        g.write(SCENE_HARNESS)
        runner = Path(g.name)
    try:
        return subprocess.run(
            ['node', str(runner), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        html_path.unlink(missing_ok=True)
        runner.unlink(missing_ok=True)


@pytest.mark.skipif(not shutil.which('node'), reason='node not installed')
def test_emitter_scene_pos_slot_runtime():
    """MEDIUM-8: pos={var} must position at runtime, not be silently dropped."""
    code = """
when app starts:
    dynamic_pos = "1,2,3"
end

scene:
    sphere size="1" pos={dynamic_pos}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    proc = _run_scene(emit_js(mir))
    assert proc.returncode == 0, proc.stderr
    sets = json.loads(proc.stdout.strip().splitlines()[-1])
    assert [1, 2, 3] in sets


def test_emitter_scene_pos_slot_emits_position_set():
    """C-04: pos={var} must keep the slot as an expression, not be split at build."""
    code = """
when app starts:
    dynamic_pos = "1,2,3"
end

scene:
    sphere size="1" pos={dynamic_pos}
    camera pos={dynamic_pos}
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'position.set' in js_code
    assert 'dynamic_pos' in js_code
    assert 'String(dynamic_pos).split' in js_code


def test_emitter_scene_loader_is_guarded():
    """C-06: top-level document.createElement must be DOM-guarded."""
    code = """
scene:
    box size="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    assert 'typeof document.createElement === "function"' in js_code
    assert '__omniSceneReady' in js_code


BARE_STUB_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
global.document = {
  getElementById: () => ({ innerHTML: "" }),
  querySelectorAll: () => [],
};
vm.runInThisContext(code, { filename: htmlPath });
process.stdout.write("ok\n");
"""


def _run_bare_stub(html: str) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8', delete=False) as f:
        f.write(html)
        html_path = Path(f.name)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', encoding='utf-8', delete=False) as g:
        g.write(BARE_STUB_HARNESS)
        runner = Path(g.name)
    try:
        return subprocess.run(
            ['node', str(runner), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        html_path.unlink(missing_ok=True)
        runner.unlink(missing_ok=True)


@pytest.mark.skipif(not shutil.which('node'), reason='node not installed')
def test_emitter_scene_runs_with_bare_document_stub():
    """C-06: scene-bearing artifact must not crash under a bare 2-field stub."""
    code = """
scene:
    box size="2"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    proc = _run_bare_stub(emit_js(mir))
    assert proc.returncode == 0, proc.stderr
    assert 'ok' in proc.stdout
