"""Property tests for OMNISYS.async.actor — determinism and delivery semantics."""

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st
from omnisys_async.actor import create_runtime

_COORD = 'c.coordinator'


def _logger(state: list[Any], msg: Any, _ctx: dict[str, Any]) -> list[Any]:
    state.append(msg)
    return state


def _counter(state: int, msg: Any, _ctx: dict[str, Any]) -> int:
    if msg == 'inc':
        return state + 1
    return state


def _scenario(nodes: int, messages: int) -> dict[str, Any]:
    """Run a fixed scenario twice and compare stats (determinism check)."""

    def run() -> dict[str, Any]:
        rt = create_runtime()
        cluster = rt.cluster_create('c')
        for i in range(nodes):
            rt.cluster_add_node(cluster, f'n{i}')
        rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
        for i in range(messages):
            rt.actor_send(cluster, 'logger', i)
        return rt.actor_run(cluster)

    return run()


@settings(max_examples=20, deadline=None)
@given(st.integers(min_value=0, max_value=4), st.integers(min_value=0, max_value=30))
def test_run_is_deterministic(nodes: int, messages: int) -> None:
    """Two identical scenarios produce identical stats."""
    a = _scenario(nodes, messages)
    b = _scenario(nodes, messages)
    assert a == b


@settings(max_examples=20, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=9), min_size=0, max_size=30))
def test_fifo_order_preserved(messages: list[int]) -> None:
    """A logger actor observes messages in FIFO order."""
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    for msg in messages:
        rt.actor_send(cluster, 'logger', msg)
    rt.actor_run(cluster)
    assert cluster['nodes'][_COORD]['actors']['logger']['state'] == messages


@settings(max_examples=20, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=9), min_size=1, max_size=20))
def test_no_loss_without_chaos(messages: list[int]) -> None:
    """Every sent message is delivered when there is no chaos."""
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    for _ in messages:
        rt.actor_send(cluster, 'counter', 'inc')
    stats = rt.actor_run(cluster)
    assert stats['sent'] == len(messages)
    assert stats['delivered'] == len(messages)
    assert stats['dead'] == 0
    assert cluster['nodes'][_COORD]['actors']['counter']['state'] == len(messages)


@settings(max_examples=20, deadline=None)
@given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=10))
def test_partition_then_heal_is_eventually_consistent(nodes: int, messages: int) -> None:
    """Partitioning then healing never loses a message (AT-LEAST-ONCE)."""
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_partition(cluster, _COORD, 'n1')
    for _ in range(messages):
        rt.actor_send(cluster, 'n1/counter', 'inc')
    rt.actor_steps(cluster, nodes)
    rt.cluster_heal(cluster, _COORD, 'n1')
    stats = rt.actor_run(cluster)
    assert stats['sent'] == messages
    assert stats['delivered'] == messages
    assert stats['dead'] == 0
    assert cluster['nodes']['n1']['actors']['counter']['state'] == messages


@settings(max_examples=20, deadline=None)
@given(st.integers(min_value=0, max_value=10), st.integers(min_value=0, max_value=10))
def test_every_envelope_is_accounted_for(nodes: int, messages: int) -> None:
    """Every sent envelope ends up delivered or dead-lettered (no silent drops)."""
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_fail(cluster, 'n1', {'restart': False})
    for _ in range(messages):
        rt.actor_send(cluster, 'n1/counter', 'inc')
    rt.actor_steps(cluster, nodes)
    rt.cluster_restart(cluster, 'n1')
    stats = rt.actor_run(cluster)
    assert stats['delivered'] + stats['dead'] == stats['sent']
