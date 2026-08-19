"""Unit tests for every OMNISYS.scene function."""

import omnisys_scene as scene
import pytest
from omnisys_core import PanicError

_BASE_TRANSFORM = {'position': [0, 0, 0], 'rotation': [0, 0, 0], 'scale': [1, 1, 1]}


def test_new_scene_builds_value_shape() -> None:
    assert scene.new_scene() == {'tag': 'scene', 'nodes': {}, 'order': [], 'nextId': 1}


def test_new_scene_is_fresh_each_call() -> None:
    first = scene.new_scene()
    second = scene.new_scene()
    assert first is not second
    assert first['nodes'] == {}
    assert first['order'] == []


def test_node_creates_group_with_base_shape() -> None:
    s = scene.new_scene()
    result = scene.node(s, 'a')
    assert result['id'] == 'a'
    assert result['kind'] == 'group'
    assert result['children'] == []
    assert result['transform'] == _BASE_TRANSFORM
    assert s['nodes'] == {'a': result}
    assert s['order'] == ['a']


def test_node_returns_same_node_on_second_call() -> None:
    s = scene.new_scene()
    first = scene.node(s, 'a')
    second = scene.node(s, 'a')
    assert second is first
    assert s['order'] == ['a']


def test_node_does_not_override_kind_of_existing_node() -> None:
    s = scene.new_scene()
    scene.camera(s, 'a')
    result = scene.node(s, 'a')
    assert result['kind'] == 'camera'


def test_node_coerces_int_id_to_string() -> None:
    s = scene.new_scene()
    result = scene.node(s, 7)
    assert result['id'] == '7'
    assert '7' in s['nodes']
    assert s['order'] == ['7']


def test_node_stringifies_varied_ids() -> None:
    s = scene.new_scene()
    for id_ in (0, 1, -1, 3.5):
        scene.node(s, id_)
    assert set(s['nodes']) == {'0', '1', '-1', '3.5'}


def test_mesh_sets_geometry_and_kind() -> None:
    s = scene.new_scene()
    result = scene.mesh(s, 'sphere', '#fff')
    assert result['kind'] == 'mesh'
    assert result['geometry'] == '#fff'
    assert s['order'] == ['sphere']


def test_mesh_stringifies_geometry() -> None:
    s = scene.new_scene()
    scene.mesh(s, 'sphere', 5)
    assert s['nodes']['sphere']['geometry'] == '5'


def test_mesh_replaces_geometry_on_update() -> None:
    s = scene.new_scene()
    scene.mesh(s, 'box', 'old')
    scene.mesh(s, 'box', 'new')
    assert s['nodes']['box']['geometry'] == 'new'
    assert s['order'] == ['box']


def test_camera_sets_kind() -> None:
    s = scene.new_scene()
    result = scene.camera(s, 'main')
    assert result['kind'] == 'camera'
    assert s['order'] == ['main']


def test_light_defaults_to_directional() -> None:
    s = scene.new_scene()
    result = scene.light(s, 'sun')
    assert result['kind'] == 'light'
    assert result['lightType'] == 'directional'


def test_light_uses_explicit_kind() -> None:
    s = scene.new_scene()
    result = scene.light(s, 'sun', 'ambient')
    assert result['lightType'] == 'ambient'


def test_light_falsy_kind_defaults_to_directional() -> None:
    s = scene.new_scene()
    for falsy in (None, '', 0, False):
        result = scene.light(s, 'x', falsy)
        assert result['lightType'] == 'directional'


def test_add_wires_parent_child_once() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    scene.add(s, 'parent', 'child')
    assert s['nodes']['parent']['children'] == ['child']
    assert s['order'] == ['parent', 'child']


def test_add_is_idempotent() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    scene.add(s, 'parent', 'child')
    scene.add(s, 'parent', 'child')
    assert s['nodes']['parent']['children'] == ['child']
    assert s['order'] == ['parent', 'child']


def test_add_wires_multiple_children() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    scene.add(s, 'parent', 'a')
    scene.add(s, 'parent', 'b')
    assert s['nodes']['parent']['children'] == ['a', 'b']


def test_add_auto_creates_child_as_group() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    scene.add(s, 'parent', 'child')
    assert s['nodes']['child']['kind'] == 'group'
    assert s['nodes']['child']['children'] == []


def test_add_does_not_remake_existing_child() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    scene.mesh(s, 'child', 'box')
    scene.add(s, 'parent', 'child')
    assert s['nodes']['child']['kind'] == 'mesh'
    assert s['nodes']['parent']['children'] == ['child']


def test_add_returns_same_scene() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    assert scene.add(s, 'parent', 'child') is s


def test_add_panics_on_unknown_parent() -> None:
    s = scene.new_scene()
    with pytest.raises(PanicError, match='unknown parent missing'):
        scene.add(s, 'missing', 'child')


def test_add_panic_leaves_scene_unchanged() -> None:
    s = scene.new_scene()
    scene.node(s, 'parent')
    with pytest.raises(PanicError):
        scene.add(s, 'ghost', 'child')
    assert s['nodes'] == {'parent': scene.node(s, 'parent')}
    assert s['order'] == ['parent']


def test_transform_sets_position() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    result = scene.transform(s, 'a', {'position': [1, 2, 3]})
    assert result is s
    assert s['nodes']['a']['transform']['position'] == [1, 2, 3]


def test_transform_sets_rotation() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {'rotation': [0, 0, 1]})
    assert s['nodes']['a']['transform']['rotation'] == [0, 0, 1]


def test_transform_sets_scale() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {'scale': [2, 2, 2]})
    assert s['nodes']['a']['transform']['scale'] == [2, 2, 2]


def test_transform_sets_all_axes_together() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(
        s,
        'a',
        {'position': [1, 2, 3], 'rotation': [0, 0, 1], 'scale': [2, 2, 2]},
    )
    assert s['nodes']['a']['transform'] == {
        'position': [1, 2, 3],
        'rotation': [0, 0, 1],
        'scale': [2, 2, 2],
    }


def test_transform_ignores_absent_keys() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {'position': [1, 2, 3]})
    assert s['nodes']['a']['transform']['rotation'] == [0, 0, 0]
    assert s['nodes']['a']['transform']['scale'] == [1, 1, 1]


def test_transform_ignores_none_values() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {'position': None, 'rotation': [1, 0, 0]})
    assert s['nodes']['a']['transform']['position'] == [0, 0, 0]
    assert s['nodes']['a']['transform']['rotation'] == [1, 0, 0]


def test_transform_empty_attrs_is_noop() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {})
    assert s['nodes']['a']['transform'] == _BASE_TRANSFORM


def test_transform_works_on_mesh_node() -> None:
    s = scene.new_scene()
    scene.mesh(s, 'box', 'cube')
    scene.transform(s, 'box', {'position': [5, 5, 5]})
    assert s['nodes']['box']['transform']['position'] == [5, 5, 5]


def test_transform_panics_on_unknown_node() -> None:
    s = scene.new_scene()
    with pytest.raises(PanicError, match='unknown node ghost'):
        scene.transform(s, 'ghost', {'position': [1, 1, 1]})


def test_remove_deletes_node_and_order_entry() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.node(s, 'b')
    result = scene.remove(s, 'a')
    assert result is s
    assert 'a' not in s['nodes']
    assert s['order'] == ['b']


def test_remove_keeps_other_nodes() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.node(s, 'b')
    scene.node(s, 'c')
    scene.remove(s, 'b')
    assert set(s['nodes']) == {'a', 'c'}
    assert s['order'] == ['a', 'c']


def test_remove_unknown_id_is_noop() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    result = scene.remove(s, 'ghost')
    assert result is s
    assert s['order'] == ['a']
    assert s['nodes'] == {'a': scene.node(s, 'a')}


def test_remove_last_node_empties_scene() -> None:
    s = scene.new_scene()
    scene.node(s, 'only')
    scene.remove(s, 'only')
    assert s['nodes'] == {}
    assert s['order'] == []


def test_remove_removes_all_order_occurrences() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    s['order'] = ['a', 'a', 'b']
    scene.remove(s, 'a')
    assert s['order'] == ['b']


def test_snapshot_matches_to_json() -> None:
    s = scene.new_scene()
    scene.mesh(s, 'box', 'cube')
    scene.node(s, 'root')
    scene.add(s, 'root', 'box')
    assert scene.snapshot(s) == scene.to_json(s)


def test_snapshot_has_only_nodes_and_order_keys() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    snap = scene.snapshot(s)
    assert set(snap) == {'nodes', 'order'}
    assert 'tag' not in snap
    assert 'nextId' not in snap


def test_snapshot_is_deep_copy() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    snap = scene.snapshot(s)
    snap['nodes']['a']['transform']['position'] = [9, 9, 9]
    snap['order'].append('x')
    assert s['nodes']['a']['transform']['position'] == [0, 0, 0]
    assert s['order'] == ['a']


def test_snapshot_deep_copies_nested_transform() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.transform(s, 'a', {'position': [1, 2, 3]})
    snap = scene.snapshot(s)
    snap['nodes']['a']['transform']['position'][0] = 99
    assert s['nodes']['a']['transform']['position'] == [1, 2, 3]


def test_snapshot_keeps_mesh_geometry() -> None:
    s = scene.new_scene()
    scene.mesh(s, 'box', '#fff')
    snap = scene.snapshot(s)
    assert snap['nodes']['box']['geometry'] == '#fff'


def test_snapshot_is_detached_from_later_mutation() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    snap = scene.snapshot(s)
    scene.node(s, 'b')
    assert 'b' not in snap['nodes']
    assert snap['order'] == ['a']


def test_snapshot_includes_elapsed_field() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.update(s, 2.5)
    snap = scene.snapshot(s)
    assert snap['nodes']['a']['_elapsed'] == 2.5


def test_update_increments_elapsed_by_dt() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.node(s, 'b')
    result = scene.update(s, 0.5)
    assert result is s
    assert s['nodes']['a']['_elapsed'] == 0.5
    assert s['nodes']['b']['_elapsed'] == 0.5


def test_update_accumulates_across_calls() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.update(s, 1)
    scene.update(s, 2)
    assert s['nodes']['a']['_elapsed'] == 3


def test_update_leaves_new_nodes_starting_from_zero() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    scene.update(s, 1.5)
    scene.node(s, 'b')
    scene.update(s, 1.5)
    assert s['nodes']['a']['_elapsed'] == 3.0
    assert s['nodes']['b']['_elapsed'] == 1.5


def test_update_only_touches_nodes_in_order() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    s['nodes']['b'] = {
        'id': 'b',
        'kind': 'group',
        'children': [],
        'transform': _BASE_TRANSFORM,
    }
    scene.update(s, 1)
    assert '_elapsed' not in s['nodes']['b']


def test_update_handles_order_id_missing_from_nodes() -> None:
    s = scene.new_scene()
    scene.node(s, 'a')
    s['order'].append('ghost')
    scene.update(s, 1)
    assert s['nodes']['a']['_elapsed'] == 1
