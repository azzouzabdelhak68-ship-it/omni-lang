"""v2.2: 3D scene: block — primitives, attributes, Three.js emission."""

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import TokenType, tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_lexer_scene_shape_keywords():
    tokens = tokenize(
        "scene:\n"
        'box size="2"\n'
        'sphere size="1.5" color="#ffffff"\n'
        'cylinder size="1"\n'
        'plane size="3"\n'
        'light type="directional" intensity="2"\n'
        'camera pos="0,0,5"\n'
        "end"
    )
    types = [t.type for t in tokens]
    assert TokenType.SCENE in types
    for shape in ("box", "sphere", "cylinder", "plane", "light", "camera"):
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
    assert shapes == ["box", "sphere", "light"]


def test_parse_scene_attributes():
    code = """
scene:
    box size="2" color="#e11d48"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    obj = ast.scene_block.objects[0]
    assert obj.shape == "box"
    assert obj.attrs["size"].value == "2"
    assert obj.attrs["color"].value == "#e11d48"


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
    slot = obj.attrs["color"]
    assert slot.kind == "slot"
    assert slot.expr.name == "my_color"


def test_parse_scene_position_tuple():
    code = """
scene:
    sphere size="1.5" pos="0,2,0"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    obj = ast.scene_block.objects[0]
    assert obj.attrs["pos"].value == "0,2,0"


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
        assert "attribute" in str(exc).lower() or "bogus_attr" in str(exc).lower()
    else:
        raise AssertionError("unknown scene attribute should fail")


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
        assert "shape" in str(exc).lower() or "dodecahedron" in str(exc).lower()
    else:
        raise AssertionError("unknown scene shape should fail")


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
        assert "undefined" in str(exc).lower()
    else:
        raise AssertionError("undefined slot variable should fail")


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
    shapes = [o["shape"] for o in mir.scene]
    assert shapes == ["box", "light"]


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
    assert "scene" in json_str
    parsed = mir.from_json(json_str)
    assert parsed.scene[0]["shape"] == "box"


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
    assert "THREE" in js_code
    assert "WebGLRenderer" in js_code
    assert "BoxGeometry" in js_code
    assert "MeshStandardMaterial" in js_code


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
    assert "BoxGeometry" in js_code
    assert "SphereGeometry" in js_code
    assert "CylinderGeometry" in js_code
    assert "PlaneGeometry" in js_code


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
    assert "DirectionalLight" in js_code
    assert "DirectionalLight(" in js_code


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
    assert "camera.position.set(0, 0, 5)" in js_code


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
    assert "my_color" in js_code


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
    assert "requestAnimationFrame" in js_code
    assert "animate" in js_code


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
        "new THREE.Scene()",
        "PerspectiveCamera",
        "new THREE.WebGLRenderer()",
        "SphereGeometry",
        "MeshStandardMaterial",
        "scene.add",
        "DirectionalLight",
    ]
    for part in snapshot_parts:
        assert part in js_code, f"missing snapshot part: {part}"