"""Unit tests for OMNISYS.sim."""

from __future__ import annotations

import omnisys_sim as sim
import pytest
from omnisys_core import PanicError


def test_world_shape() -> None:
    w = sim.world()
    assert w['tag'] == 'world'
    assert w['entities'] == {}
    assert w['order'] == []
    assert w['systems'] == []
    assert w['step'] == 0


def test_entity_creates_and_is_idempotent() -> None:
    w = sim.world()
    first = sim.entity(w, 'hero')
    assert first == {'tag': 'entity', 'name': 'hero', 'components': {}}
    assert sim.entity(w, 'hero') is first
    assert w['order'] == ['hero']


def test_entity_adds_in_insertion_order() -> None:
    w = sim.world()
    sim.entity(w, 'a')
    sim.entity(w, 'b')
    sim.entity(w, 'a')
    assert w['order'] == ['a', 'b']


def test_component_sets_str_key_and_returns_world() -> None:
    w = sim.world()
    result = sim.component(w, 'hero', 'hp', 100)
    assert result is w
    assert w['entities']['hero']['components'] == {'hp': 100}


def test_component_coerces_key_to_string() -> None:
    w = sim.world()
    sim.component(w, 'hero', 42, 'answer')
    assert w['entities']['hero']['components'] == {'42': 'answer'}


def test_component_auto_creates_entity() -> None:
    w = sim.world()
    sim.component(w, 'ghost', 'hp', 1)
    assert 'ghost' in w['entities']
    assert w['entities']['ghost']['components'] == {'hp': 1}


def test_get_returns_value() -> None:
    w = sim.world()
    sim.component(w, 'hero', 'hp', 100)
    assert sim.get(w, 'hero', 'hp') == 100


def test_get_returns_none_for_missing_component() -> None:
    w = sim.world()
    sim.component(w, 'hero', 'hp', 100)
    assert sim.get(w, 'hero', 'mana') is None


def test_get_panics_for_unknown_entity() -> None:
    w = sim.world()
    with pytest.raises(PanicError):
        sim.get(w, 'nobody', 'hp')


def test_system_appends_in_registration_order() -> None:
    w = sim.world()
    calls: list[str] = []

    def s1(_world: dict) -> None:
        calls.append('s1')

    def s2(_world: dict) -> None:
        calls.append('s2')

    sim.system(w, s1)
    sim.system(w, s2)
    assert w['systems'] == [s1, s2]


def test_run_invokes_systems_per_step_in_order() -> None:
    w = sim.world()
    calls: list[int] = []

    def s1(_world: dict) -> None:
        calls.append(1)

    def s2(_world: dict) -> None:
        calls.append(2)

    sim.system(w, s1)
    sim.system(w, s2)
    result = sim.run(w, 2)
    assert result is w
    assert calls == [1, 2, 1, 2]
    assert w['step'] == 2


def test_run_with_negative_steps_is_noop() -> None:
    w = sim.world()
    calls: list[int] = []

    def s1(_world: dict) -> None:
        calls.append(1)

    sim.system(w, s1)
    sim.run(w, -3)
    assert calls == []
    assert w['step'] == 0


def test_run_system_sees_world() -> None:
    w = sim.world()
    sim.component(w, 'hero', 'hp', 100)

    def heal(_world: dict) -> None:
        _world['entities']['hero']['components']['hp'] += 10

    sim.system(w, heal)
    sim.run(w, 1)
    assert sim.get(w, 'hero', 'hp') == 110


def test_query_filters_by_component_presence() -> None:
    w = sim.world()
    sim.component(w, 'a', 'pos', [0, 0])
    sim.component(w, 'b', 'vel', [1, 1])
    sim.component(w, 'c', 'pos', [2, 2])
    assert sim.query(w, 'pos') == ['a', 'c']


def test_query_includes_later_created_entities() -> None:
    w = sim.world()
    sim.component(w, 'a', 'pos', [0, 0])
    sim.query(w, 'pos')
    sim.component(w, 'b', 'pos', [1, 1])
    assert sim.query(w, 'pos') == ['a', 'b']


def test_query_coerces_component_to_string() -> None:
    w = sim.world()
    sim.component(w, 'a', 7, 'x')
    assert sim.query(w, 7) == ['a']


def test_query_excludes_missing_component_and_removed_entities() -> None:
    w = sim.world()
    sim.component(w, 'a', 'pos', [0, 0])
    sim.component(w, 'b', 'vel', [1, 1])
    sim.remove_entity(w, 'a')
    assert sim.query(w, 'pos') == []


def test_remove_entity_deletes_and_returns_world() -> None:
    w = sim.world()
    sim.entity(w, 'a')
    sim.entity(w, 'b')
    result = sim.remove_entity(w, 'a')
    assert result is w
    assert 'a' not in w['entities']
    assert w['order'] == ['b']


def test_remove_entity_unknown_name_is_noop() -> None:
    w = sim.world()
    sim.entity(w, 'a')
    sim.remove_entity(w, 'nope')
    assert w['entities'] == {'a': {'tag': 'entity', 'name': 'a', 'components': {}}}
    assert w['order'] == ['a']


def test_entities_returns_a_copy() -> None:
    w = sim.world()
    sim.entity(w, 'a')
    result = sim.entities(w)
    result.append('x')
    assert w['order'] == ['a']
    assert result == ['a', 'x']


def test_snapshot_shape_and_deep_copy() -> None:
    w = sim.world()
    sim.component(w, 'a', 'pos', [0, 0])

    def s1(_world: dict) -> None:
        pass

    sim.system(w, s1)
    sim.run(w, 3)
    snap = sim.snapshot(w)
    assert set(snap) == {'tag', 'step', 'entities', 'order'}
    assert snap['tag'] == 'world'
    assert snap['step'] == 3
    assert snap['order'] == ['a']
    assert 'systems' not in snap
    snap['entities']['a']['components']['pos'][0] = 99
    snap['order'].append('x')
    assert sim.get(w, 'a', 'pos') == [0, 0]
    assert sim.entities(w) == ['a']


def test_snapshot_after_remove_entity() -> None:
    w = sim.world()
    sim.entity(w, 'a')
    sim.entity(w, 'b')
    sim.remove_entity(w, 'a')
    assert sim.snapshot(w) == {
        'tag': 'world',
        'step': 0,
        'entities': {'b': {'tag': 'entity', 'name': 'b', 'components': {}}},
        'order': ['b'],
    }
