"""Unit tests for OMNISYS.async.actor — the distributed actor escape."""

from typing import Any

import pytest
from omnisys_async.actor import VERSION, ReceiveBehavior, create_runtime
from omnisys_core import PanicError

_COORD = 'c.coordinator'


def _counter(state: int, msg: Any, _ctx: dict[str, Any]) -> int:
    if msg == 'inc':
        return state + 1
    return state


def _logger(state: list[Any], msg: Any, _ctx: dict[str, Any]) -> list[Any]:
    state.append(msg)
    return state


def _keeper(state: dict[str, Any], msg: Any, _ctx: dict[str, Any]) -> None:
    if msg == 'keep':
        return None
    return state


def _raises(_state: Any, msg: Any, _ctx: dict[str, Any]) -> Any:
    raise ValueError(f'boom {msg}')


def _sender_echo(state: dict[str, Any], _msg: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    state['last_sender'] = ctx['sender']
    state['self_id'] = ctx['self']
    state['node_id'] = ctx['node']
    return state


def test_version() -> None:
    assert VERSION == '5.3.0'


def test_create_runtime_isolation() -> None:
    rt1 = create_runtime()
    rt2 = create_runtime()
    rt1.cluster_create('one')
    assert 'one' in rt1._clusters
    assert 'one' not in rt2._clusters
    assert rt2._current is None


def test_flat_status_empty_without_cluster() -> None:
    assert create_runtime().status() == {}


def test_cluster_create_sets_current_and_coordinator() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    assert cluster['name'] == 'c'
    assert _COORD in cluster['nodes']
    assert cluster['nodes'][_COORD]['alive'] is True
    assert rt._current is cluster


def test_cluster_create_existing_returns_same() -> None:
    rt = create_runtime()
    first = rt.cluster_create('c')
    second = rt.cluster_create('c')
    assert first is second
    assert len(first['nodes']) == 1


def test_cluster_create_config_defaults() -> None:
    rt = create_runtime()
    cfg = rt.cluster_create('c')['config']
    assert cfg['heartbeat_interval'] == 3
    assert cfg['heartbeat_timeout'] == 6
    assert cfg['max_node_restarts'] == 3
    assert cfg['max_actor_restarts'] == 3
    assert cfg['max_steps'] == 10000


def test_cluster_create_config_overrides_and_junk() -> None:
    rt = create_runtime()
    cfg = rt.cluster_create(
        'c',
        {
            'heartbeat_interval': 1,
            'heartbeat_timeout': 2.5,
            'max_node_restarts': True,
            'max_actor_restarts': 'junk',
            'max_steps': 5,
        },
    )['config']
    assert cfg['heartbeat_interval'] == 1
    assert cfg['heartbeat_timeout'] == 2
    assert cfg['max_node_restarts'] == 3
    assert cfg['max_actor_restarts'] == 3
    assert cfg['max_steps'] == 5


def test_cluster_add_node_and_idempotent() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    node = rt.cluster_add_node(cluster, 'n1')
    assert node['id'] == 'n1'
    assert node['alive'] is True
    assert node['last_heartbeat']['n1'] == 0
    assert rt.cluster_add_node(cluster, 'n1') is node
    assert len(cluster['nodes']) == 2


def test_cluster_of_string_name() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    assert rt.cluster_add_node('c', 'n1') is cluster['nodes']['n1']


def test_cluster_of_unknown_name_panics() -> None:
    rt = create_runtime()
    with pytest.raises(PanicError, match="unknown cluster 'nope'"):
        rt.cluster_add_node('nope', 'n1')


def test_no_current_cluster_panics() -> None:
    rt = create_runtime()
    with pytest.raises(PanicError, match='no current cluster'):
        rt.actor_step(None)


def test_partition_heal() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_partition(cluster, _COORD, 'n1')
    assert cluster['partitions'][_COORD] == {'n1'}
    assert cluster['partitions']['n1'] == {_COORD}
    assert cluster['stats']['partitions'] == 1
    rt.cluster_heal(cluster, _COORD, 'n1')
    assert cluster['partitions'][_COORD] == set()
    assert cluster['stats']['heals'] == 1


def test_partition_unknown_node_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown node .* or 'nope'"):
        rt.cluster_partition(cluster, _COORD, 'nope')


def test_heal_unknown_node_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown node .* or 'nope'"):
        rt.cluster_heal(cluster, _COORD, 'nope')


def test_fail_restart_and_remove() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_fail(cluster, 'n1')
    assert cluster['nodes']['n1']['alive'] is False
    assert cluster['stats']['failures'] == 1
    assert rt.cluster_restart(cluster, 'n1') is True
    assert cluster['nodes']['n1']['alive'] is True
    assert cluster['nodes']['n1']['restarts'] == 1
    rt.cluster_remove(cluster, 'n1')
    assert cluster['nodes']['n1']['removed'] is True
    assert rt.cluster_restart(cluster, 'n1') is False


def test_fail_unknown_node_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown node 'nope'"):
        rt.cluster_fail(cluster, 'nope')


def test_fail_removed_node_is_noop() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_remove(cluster, 'n1')
    rt.cluster_fail(cluster, 'n1')
    assert cluster['stats']['failures'] == 0


def test_restart_unknown_node_false() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    assert rt.cluster_restart(cluster, 'nope') is False


def test_restart_removed_node_false() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_remove(cluster, 'n1')
    assert rt.cluster_restart(cluster, 'n1') is False


def test_stop_actor_unknown_node_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown node 'nope'"):
        rt.cluster_stop_actor(cluster, 'nope', 'a')


def test_stop_actor_unknown_actor_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown actor 'a'"):
        rt.cluster_stop_actor(cluster, _COORD, 'a')


def test_members_includes_self_excludes_partitioned() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_add_node(cluster, 'n2')
    assert rt.cluster_members(cluster, _COORD) == [_COORD, 'n1', 'n2']
    rt.cluster_partition(cluster, _COORD, 'n1')
    assert rt.cluster_members(cluster, _COORD) == [_COORD, 'n2']
    assert rt.cluster_members(cluster, 'n1') == ['n1', 'n2']


def test_members_unknown_or_dead_or_removed() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    assert rt.cluster_members(cluster, 'nope') == []
    rt.cluster_fail(cluster, 'n1')
    assert rt.cluster_members(cluster, 'n1') == []
    rt.cluster_restart(cluster, 'n1')
    rt.cluster_remove(cluster, 'n1')
    assert rt.cluster_members(cluster, 'n1') == []


def test_actor_spawn_ref_and_resolve() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    ref = rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    assert ref == {
        '__omni_actor': True,
        'id': 'c.coordinator/counter',
        'node': _COORD,
        'name': 'counter',
    }
    actor = cluster['nodes'][_COORD]['actors']['counter']
    assert actor['state'] == 0
    assert actor['processed'] == 0


def test_actor_spawn_errors() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    with pytest.raises(PanicError, match="unknown node 'nope'"):
        rt.actor_spawn(cluster, 'nope', 'a', _counter, 0)
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_fail(cluster, 'n1')
    with pytest.raises(PanicError, match='not alive'):
        rt.actor_spawn(cluster, 'n1', 'a', _counter, 0)
    rt.cluster_restart(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'a', _counter, 0)
    with pytest.raises(PanicError, match='already exists'):
        rt.actor_spawn(cluster, 'n1', 'a', _counter, 0)
    with pytest.raises(PanicError, match='not a function'):
        rt.actor_spawn(cluster, 'n1', 'b', 'not-a-function', 0)


def test_spawn_send_run_delivery() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    seq1 = rt.actor_send(cluster, 'c.coordinator/counter', 'inc')
    seq2 = rt.actor_send(cluster, 'c.coordinator/counter', 'inc')
    assert seq1 == 1
    assert seq2 == 2
    stats = rt.actor_run(cluster)
    assert stats['sent'] == 2
    assert stats['delivered'] == 2
    assert stats['dead'] == 0
    actor = cluster['nodes'][_COORD]['actors']['counter']
    assert actor['state'] == 2
    assert actor['processed'] == 2


def test_send_to_actor_ref() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    ref = rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    rt.actor_send(cluster, ref, 'inc')
    rt.actor_run(cluster)
    assert cluster['nodes'][_COORD]['actors']['counter']['state'] == 1


def test_send_to_bare_name() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    rt.actor_send(cluster, 'counter', 'inc')
    rt.actor_run(cluster)
    assert cluster['nodes'][_COORD]['actors']['counter']['state'] == 1


def test_send_unknown_actor_deadletters() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    seq = rt.actor_send(cluster, 'c.coordinator/ghost', 'inc')
    assert seq == 1
    dl = rt.actor_deadletters(cluster)
    assert len(dl) == 1
    assert dl[0]['reason'] == 'unknown-actor'
    assert dl[0]['to'] is None
    assert cluster['stats']['sent'] == 0
    assert cluster['stats']['dead'] == 1


def test_send_no_source_node_panics() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    del cluster['nodes'][_COORD]
    with pytest.raises(PanicError, match='no source node'):
        rt.actor_send(cluster, 'n1/counter', 'inc')


def test_sender_empty_outside_processing() -> None:
    rt = create_runtime()
    rt.cluster_create('c')
    assert rt.actor_sender() == ''


def test_sender_and_context_inside_processing() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'echo', _sender_echo, {})
    rt.actor_send(cluster, 'echo', 'x')
    rt.actor_run(cluster)
    state = cluster['nodes'][_COORD]['actors']['echo']['state']
    assert state['last_sender'] == ''
    assert state['self_id'] == 'c.coordinator/echo'
    assert state['node_id'] == _COORD


def test_receive_predicate_drops() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    guarded = rt.actor_receive(_counter, predicate=lambda msg, ctx: msg == 'inc')
    rt.actor_spawn(cluster, _COORD, 'counter', guarded, 0)
    rt.actor_send(cluster, 'counter', 'inc')
    rt.actor_send(cluster, 'counter', 'skip')
    rt.actor_run(cluster)
    assert guarded.dropped == 1
    assert cluster['nodes'][_COORD]['actors']['counter']['state'] == 1
    assert cluster['stats']['delivered'] == 2
    assert cluster['stats']['dead'] == 0


def test_receive_no_predicate_passes_all() -> None:
    wrapped = ReceiveBehavior(_logger)
    state: list[Any] = []
    wrapped(state, 'a', {'self': 's', 'node': 'n', 'sender': ''})
    assert state == ['a']
    assert wrapped.dropped == 0


def test_fifo_order_preserved() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    for i in range(20):
        rt.actor_send(cluster, 'logger', i)
    rt.actor_run(cluster)
    assert cluster['nodes'][_COORD]['actors']['logger']['state'] == list(range(20))


def test_behavior_returning_none_keeps_state() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'keeper', _keeper, {'v': 0})
    rt.actor_send(cluster, 'keeper', 'keep')
    rt.actor_run(cluster)
    assert cluster['nodes'][_COORD]['actors']['keeper']['state'] == {'v': 0}
    assert cluster['stats']['delivered'] == 1


def test_crash_restart_until_exhausted() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c', {'max_actor_restarts': 2})
    rt.actor_spawn(cluster, _COORD, 'bomb', _raises, 'initial')
    for _ in range(4):
        rt.actor_send(cluster, 'bomb', 'go')
    rt.actor_run(cluster)
    actor = cluster['nodes'][_COORD]['actors']['bomb']
    assert actor['crashes'] == 3
    assert actor['restarts'] == 2
    assert actor['stopped'] is True
    assert cluster['stats']['delivered'] == 0
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert reasons.count('crash') == 3
    assert reasons.count('actor-stopped') == 1


def test_crash_single_with_restart_capacity() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c', {'max_actor_restarts': 3})
    rt.actor_spawn(cluster, _COORD, 'bomb', _raises, 'initial')
    rt.actor_send(cluster, 'bomb', 'go')
    rt.actor_run(cluster)
    actor = cluster['nodes'][_COORD]['actors']['bomb']
    assert actor['crashes'] == 1
    assert actor['restarts'] == 1
    assert actor['alive'] is True
    assert actor['state'] == 'initial'


def test_stop_actor_deadletters_mailbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    rt.actor_send(cluster, 'logger', 'a')
    rt.actor_send(cluster, 'logger', 'b')
    rt.actor_steps(cluster, 1)
    rt.cluster_stop_actor(cluster, _COORD, 'logger')
    assert cluster['nodes'][_COORD]['actors']['logger']['stopped'] is True
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert 'actor-stopped' in reasons


def test_partition_holds_then_heal_delivers() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_partition(cluster, _COORD, 'n1')
    rt.actor_send(cluster, 'n1/counter', 'inc')
    first = rt.actor_steps(cluster, 2)
    assert first['delivered'] == 0
    assert first['redelivered'] == 1
    rt.cluster_heal(cluster, _COORD, 'n1')
    stats = rt.actor_run(cluster)
    assert stats['delivered'] == 1
    assert stats['redelivered'] == 2
    assert cluster['nodes']['n1']['actors']['counter']['state'] == 1


def test_partition_holds_while_dead_and_redelivers() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_fail(cluster, 'n1', {'restart': False})
    rt.actor_send(cluster, 'n1/counter', 'inc')
    stats = rt.actor_steps(cluster, 2)
    assert stats['delivered'] == 0
    assert stats['redelivered'] == 1
    assert cluster['nodes']['n1']['removed'] is False


def test_failed_node_supervised_restart() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_fail(cluster, 'n1')
    assert rt.actor_step(cluster) is True
    node = cluster['nodes']['n1']
    assert node['alive'] is True
    assert node['restarts'] == 1
    assert cluster['stats']['restarts'] == 1


def test_failed_node_restart_limit_removes() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c', {'max_node_restarts': 1})
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_fail(cluster, 'n1')
    rt.actor_step(cluster)
    rt.cluster_fail(cluster, 'n1')
    rt.actor_step(cluster)
    assert cluster['nodes']['n1']['removed'] is True


def test_no_restart_node_detected_dead() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c', {'heartbeat_interval': 1, 'heartbeat_timeout': 1})
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.actor_send(cluster, 'n1/counter', 'inc')
    rt.cluster_fail(cluster, 'n1', {'restart': False})
    rt.actor_steps(cluster, 2)
    node = cluster['nodes']['n1']
    assert node['removed'] is True
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert 'detected-dead' in reasons


def test_cluster_remove_deadletters_pending() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.actor_send(cluster, 'n1/counter', 'inc')
    rt.cluster_remove(cluster, 'n1')
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert 'node-removed' in reasons


def test_run_bounded_by_max_steps() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c', {'max_steps': 1})
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    rt.actor_send(cluster, 'logger', 'a')
    rt.actor_send(cluster, 'logger', 'b')
    stats = rt.actor_run(cluster)
    assert stats['steps'] == 1
    assert stats['delivered'] == 1


def test_steps_runs_exactly_n() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    stats = rt.actor_steps(cluster, 3)
    assert stats['steps'] == 3
    assert stats['delivered'] == 0


def test_step_returns_false_when_quiescent() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'counter', _counter, 0)
    assert rt.actor_step(cluster) is False


def test_snapshot_shape() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.actor_send(cluster, 'n1/counter', 'inc')
    rt.actor_run(cluster)
    snap = rt.cluster_snapshot(cluster)
    assert snap['name'] == 'c'
    assert snap['tick'] > 0
    assert snap['partitions'] == []
    assert snap['stats']['deadLetters'] == 0
    by_id = {n['id']: n for n in snap['nodes']}
    assert by_id['n1']['actors'][0]['name'] == 'counter'
    assert by_id['n1']['actors'][0]['state'] == 1
    assert by_id['n1']['members'] == [_COORD, 'n1']


def test_status_shape() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_fail(cluster, 'n1')
    status = rt.cluster_status(cluster)
    assert status[_COORD]['alive'] is True
    assert status['n1']['alive'] is False
    assert 'lastHeartbeat' in status[_COORD]


def test_flat_aliases_operate_on_current() -> None:
    rt = create_runtime()
    rt.cluster('c')
    rt.node('n1')
    rt.spawn('n1', 'counter', _counter, 0)
    rt.send('n1/counter', 'inc')
    stats = rt.run()
    assert stats['delivered'] == 1
    assert rt.sender() == ''
    assert rt.step() is False
    assert rt.stats()['delivered'] == 1
    assert len(rt.deadletters()) == 0
    assert rt.members('n1') == [_COORD, 'n1']
    rt.partition(_COORD, 'n1')
    assert 'n1' not in rt.members(_COORD)
    rt.heal(_COORD, 'n1')
    rt.fail('n1')
    assert rt.restart('n1') is True
    rt.stop_actor('n1', 'counter')
    rt.remove('n1')
    assert rt.status()['n1']['removed'] is True


def test_actor_gone_deadletter_when_stopped_before_inbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    rt.actor_send(cluster, 'logger', 'a')
    rt.cluster_stop_actor(cluster, _COORD, 'logger')
    rt.actor_run(cluster)
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert 'actor-gone' in reasons


def test_redelivered_counter_only_after_retry() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_partition(cluster, _COORD, 'n1')
    rt.actor_send(cluster, 'n1/counter', 'inc')
    assert rt.actor_steps(cluster, 1)['redelivered'] == 0
    assert rt.actor_steps(cluster, 1)['redelivered'] == 1


def test_partitioned_is_bidirectional_check() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_partition(cluster, _COORD, 'n1')
    assert cluster['partitions']['n1'] == {_COORD}


# ------------------------------------------------------------ white-box gates


def _env(seq: int, to: str, msg: Any = 'x') -> dict[str, Any]:
    return {'seq': seq, 'from': '', 'to': to, 'msg': msg, 'attempts': 0}


def test_heal_non_partitioned_pair_is_noop() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_heal(cluster, _COORD, 'n1')
    assert cluster['stats']['heals'] == 1


def test_restart_with_dead_peer_skips_heartbeat() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_add_node(cluster, 'n2')
    rt.cluster_fail(cluster, 'n2', {'restart': False})
    assert rt.cluster_restart(cluster, 'n1') is True


def test_members_skips_dead_nodes() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_add_node(cluster, 'n2')
    rt.cluster_fail(cluster, 'n2', {'restart': False})
    assert 'n2' not in rt.cluster_members(cluster, 'n1')


def test_flat_steps_alias() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'logger', _logger, [])
    rt.actor_send(cluster, 'logger', 'x')
    assert rt.steps(1)['delivered'] == 1


def test_remove_unknown_and_twice_is_noop() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_remove(cluster, 'nope')
    rt.cluster_remove(cluster, 'n1')
    assert cluster['nodes']['n1']['removed'] is True
    rt.cluster_remove(cluster, 'n1')
    assert cluster['stats']['dead'] == 0


def test_remove_node_deadletters_only_matching_outbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_add_node(cluster, 'n2')
    rt.actor_spawn(cluster, 'n1', 'a1', _logger, [])
    rt.actor_spawn(cluster, 'n2', 'a2', _logger, [])
    rt.actor_send(cluster, 'n1/a1', 'x')
    rt.actor_send(cluster, 'n2/a2', 'y')
    rt.cluster_remove(cluster, 'n1')
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert reasons.count('node-removed') == 1
    assert len(cluster['nodes'][_COORD]['outbox']) == 1


def test_remove_node_deadletters_only_matching_inbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.cluster_add_node(cluster, 'n2')
    cluster['nodes'][_COORD]['inbox'] = [_env(1, 'n1/a1'), _env(2, 'n2/a2')]
    rt.cluster_remove(cluster, 'n1')
    reasons = [dl['reason'] for dl in rt.actor_deadletters(cluster)]
    assert reasons.count('node-removed') == 1
    assert len(cluster['nodes'][_COORD]['inbox']) == 1


def test_remove_node_deadletters_mailbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'a1', _logger, [])
    actor = cluster['nodes']['n1']['actors']['a1']
    actor['mailbox'] = [_env(1, 'n1/a1')]
    rt.cluster_remove(cluster, 'n1')
    assert actor['mailbox'] == []
    assert [dl['reason'] for dl in rt.actor_deadletters(cluster)] == ['node-removed']


def test_resolve_actor_bare_name_skips_removed_and_missing() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'counter', _counter, 0)
    rt.cluster_add_node(cluster, 'a1')
    rt.actor_spawn(cluster, 'a1', 'other', _logger, [])
    rt.cluster_remove(cluster, 'a1')
    rt.actor_send(cluster, 'counter', 'inc')
    rt.actor_run(cluster)
    assert cluster['nodes']['n1']['actors']['counter']['state'] == 1


def test_resolve_actor_bare_name_unknown_deadletters() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_send(cluster, 'ghost', 'inc')
    assert rt.actor_deadletters(cluster)[0]['reason'] == 'unknown-actor'


def test_lookup_actor_removed_node_returns_none() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    rt.actor_spawn(cluster, 'n1', 'a1', _logger, [])
    rt.cluster_remove(cluster, 'n1')
    rt.actor_send(cluster, 'n1/a1', 'x')
    assert rt.actor_deadletters(cluster)[0]['reason'] == 'unknown-actor'


def test_lookup_helpers_no_slash_forms() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.actor_spawn(cluster, _COORD, 'a1', _logger, [])
    assert rt._node_of_actor_id(cluster, 'coordinator') is None
    assert rt._node_of_actor_id(cluster, 'c.coordinator/a1') is not None
    assert rt._lookup_actor_by_id(cluster, 'noslash') is None


def test_dead_letter_is_idempotent() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    env = _env(1, 'n1/a1')
    rt._dead_letter(cluster, env, 'x')
    rt._dead_letter(cluster, env, 'x')
    assert cluster['stats']['dead'] == 1


def test_step4_skips_already_dead_envelope() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    env = _env(1, 'n1/a1')
    env['_dead'] = True
    cluster['nodes'][_COORD]['outbox'] = [env]
    assert rt.actor_step(cluster) is False


def test_step4_actor_gone_in_outbox() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    rt.cluster_add_node(cluster, 'n1')
    cluster['nodes'][_COORD]['outbox'] = [_env(1, 'n1/ghost')]
    rt.actor_step(cluster)
    assert rt.actor_deadletters(cluster)[0]['reason'] == 'actor-gone'


def test_step4_non_string_target_deadletters() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    cluster['nodes'][_COORD]['outbox'] = [_env(1, 'n1/a1')]
    cluster['nodes'][_COORD]['outbox'][0]['to'] = None
    rt.actor_step(cluster)
    assert rt.actor_deadletters(cluster)[0]['reason'] == 'actor-gone'


def test_step5_skips_already_dead_envelope() -> None:
    rt = create_runtime()
    cluster = rt.cluster_create('c')
    env = _env(1, 'c.coordinator/a1')
    env['_dead'] = True
    cluster['nodes'][_COORD]['inbox'] = [env]
    assert rt.actor_step(cluster) is False
