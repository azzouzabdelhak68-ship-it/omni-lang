"""Property tests for OMNISYS.sim."""

from __future__ import annotations

import omnisys_sim as sim
from hypothesis import assume, given
from hypothesis import strategies as st


@given(st.text())
def test_entity_is_idempotent(name: str) -> None:
    w = sim.world()
    first = sim.entity(w, name)
    second = sim.entity(w, name)
    assert second is first
    assert w['order'] == [name]
    assert sim.entities(w) == [name]


@given(st.text(), st.text(), st.integers())
def test_component_round_trips_through_get(name: str, comp: str, value: int) -> None:
    w = sim.world()
    sim.component(w, name, comp, value)
    assert sim.get(w, name, comp) == value


@given(st.lists(st.text(), max_size=5), st.text())
def test_query_results_are_entities_with_component(names: list[str], comp: str) -> None:
    w = sim.world()
    for name in names:
        sim.component(w, name, comp, 1)
    found = sim.query(w, comp)
    assert set(found) == set(names)
    for name in found:
        assert name in sim.entities(w)


@given(st.integers(min_value=0, max_value=6))
def test_run_accumulates_steps(steps: int) -> None:
    w = sim.world()

    def tick(_world: dict) -> None:
        pass

    sim.system(w, tick)
    sim.run(w, steps)
    assert w['step'] == steps


@given(st.text(), st.text(), st.integers())
def test_snapshot_preserves_entities(name: str, comp: str, value: int) -> None:
    w = sim.world()
    sim.component(w, name, comp, value)
    snap = sim.snapshot(w)
    assert snap['entities'][name]['components'][comp] == value
    assert snap['order'] == [name]


@given(st.text(), st.text())
def test_remove_entity_excludes_from_entities(name: str, other: str) -> None:
    assume(name != other)
    w = sim.world()
    sim.entity(w, name)
    sim.entity(w, other)
    sim.remove_entity(w, name)
    assert name not in sim.entities(w)
    assert other in sim.entities(w)
