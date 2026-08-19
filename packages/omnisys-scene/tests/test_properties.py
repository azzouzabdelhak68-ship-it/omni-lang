"""Hypothesis property tests for OMNISYS.scene invariants."""

import omnisys_scene as scene
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

_SETTINGS = settings(max_examples=150, deadline=None)

_ID = st.text()
_GEOMETRY = st.text()
_LIGHT_KIND = st.one_of(st.none(), st.text())
_VEC = st.lists(
    st.floats(allow_nan=False, allow_infinity=False),
    min_size=3,
    max_size=3,
)
_DT = st.floats(allow_nan=False, allow_infinity=False)

_BASE_TRANSFORM = {'position': [0, 0, 0], 'rotation': [0, 0, 0], 'scale': [1, 1, 1]}


@_SETTINGS
@given(_ID)
def test_node_idempotence(id_: str) -> None:
    s = scene.new_scene()
    first = scene.node(s, id_)
    second = scene.node(s, id_)
    assert second is first
    assert s['order'] == [id_]
    assert second['transform'] == _BASE_TRANSFORM


@_SETTINGS
@given(_ID)
def test_node_stringifies_id(id_: str) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    assert s['nodes'][id_]['id'] == id_
    assert s['order'] == [id_]


@_SETTINGS
@given(_ID, _GEOMETRY)
def test_mesh_geometry_roundtrip(id_: str, geometry: str) -> None:
    s = scene.new_scene()
    node_ = scene.mesh(s, id_, geometry)
    assert node_['kind'] == 'mesh'
    assert node_['geometry'] == geometry
    snap = scene.snapshot(s)
    assert snap['nodes'][id_]['geometry'] == geometry


@_SETTINGS
@given(_ID)
def test_camera_kind_stable(id_: str) -> None:
    s = scene.new_scene()
    assert scene.camera(s, id_)['kind'] == 'camera'
    assert scene.camera(s, id_)['kind'] == 'camera'


@_SETTINGS
@given(_ID, _LIGHT_KIND)
def test_light_kind_stringified(id_: str, kind: str | None) -> None:
    s = scene.new_scene()
    node_ = scene.light(s, id_, kind)
    assert node_['lightType'] == (str(kind) if kind else 'directional')


@_SETTINGS
@given(st.lists(_ID, min_size=2, max_size=2, unique=True))
def test_add_parent_child_dedupe(ids: list[str]) -> None:
    parent, child = ids
    s = scene.new_scene()
    scene.node(s, parent)
    scene.add(s, parent, child)
    scene.add(s, parent, child)
    assert s['nodes'][parent]['children'] == [child]
    assert s['order'] == [parent, child]


@_SETTINGS
@given(st.lists(_ID, min_size=3, max_size=3, unique=True))
def test_add_auto_creates_child(ids: list[str]) -> None:
    parent, child, sibling = ids
    s = scene.new_scene()
    scene.node(s, parent)
    scene.add(s, parent, child)
    scene.add(s, parent, sibling)
    assert s['nodes'][parent]['children'] == [child, sibling]
    assert s['nodes'][child]['kind'] == 'group'
    assert s['nodes'][sibling]['kind'] == 'group'


@_SETTINGS
@given(_ID, _VEC)
def test_transform_preserves_position(id_: str, pos: list[float]) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'position': pos})
    snap = scene.snapshot(s)
    assert snap['nodes'][id_]['transform']['position'] == pos


@_SETTINGS
@given(_ID, _VEC)
def test_transform_preserves_rotation(id_: str, rot: list[float]) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'rotation': rot})
    snap = scene.snapshot(s)
    assert snap['nodes'][id_]['transform']['rotation'] == rot


@_SETTINGS
@given(_ID, _VEC)
def test_transform_preserves_scale(id_: str, scale: list[float]) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'scale': scale})
    snap = scene.snapshot(s)
    assert snap['nodes'][id_]['transform']['scale'] == scale


@_SETTINGS
@given(_ID, _VEC, _VEC, _VEC)
def test_transform_sets_all_axes(
    id_: str,
    pos: list[float],
    rot: list[float],
    scale: list[float],
) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'position': pos, 'rotation': rot, 'scale': scale})
    transform = s['nodes'][id_]['transform']
    assert transform['position'] == pos
    assert transform['rotation'] == rot
    assert transform['scale'] == scale


@_SETTINGS
@given(_ID)
def test_transform_ignores_none_values(id_: str) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'position': None, 'rotation': None, 'scale': None})
    assert s['nodes'][id_]['transform'] == _BASE_TRANSFORM


@_SETTINGS
@given(_ID, _VEC)
def test_snapshot_is_detached_deep_copy(id_: str, pos: list[float]) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.transform(s, id_, {'position': pos})
    snap = scene.snapshot(s)
    snap['nodes'][id_]['transform']['position'][0] = 999.0
    snap['order'].append('ghost')
    assert s['nodes'][id_]['transform']['position'] == pos
    assert s['order'] == [id_]


@_SETTINGS
@given(_ID, _VEC)
def test_snapshot_equals_to_json(id_: str, pos: list[float]) -> None:
    s = scene.new_scene()
    scene.mesh(s, id_, 'box')
    scene.transform(s, id_, {'position': pos})
    assert scene.snapshot(s) == scene.to_json(s)
    assert set(scene.snapshot(s)) == {'nodes', 'order'}


@_SETTINGS
@given(_ID, _DT)
def test_update_accumulates_dt(id_: str, dt: float) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.update(s, dt)
    scene.update(s, dt)
    assert s['nodes'][id_]['_elapsed'] == pytest.approx(2 * dt)


@_SETTINGS
@given(_ID, _DT)
def test_update_returns_same_scene(id_: str, dt: float) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    assert scene.update(s, dt) is s


@_SETTINGS
@given(_ID, _DT, _DT)
def test_update_accumulates_sequential_dts(id_: str, dt1: float, dt2: float) -> None:
    s = scene.new_scene()
    scene.node(s, id_)
    scene.update(s, dt1)
    scene.update(s, dt2)
    assert s['nodes'][id_]['_elapsed'] == pytest.approx(dt1 + dt2)
