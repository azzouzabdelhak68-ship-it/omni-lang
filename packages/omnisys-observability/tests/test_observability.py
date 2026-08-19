"""Unit tests for OMNISYS.observability."""

from __future__ import annotations

import omnisys_observability as obs


def _setup() -> None:
    obs.clear()


def test_clear_resets_state() -> None:
    obs.log('info', 'one', {})
    obs.metric('m', 1)
    obs.trace_begin('t')
    obs.clear()
    snap = obs.snapshot()
    assert snap == {'logs': [], 'metrics': {}, 'traces': []}


def test_log_appends_entry() -> None:
    _setup()
    obs.log('info', 'hello', {'user': 'alice'})
    snap = obs.snapshot()
    assert len(snap['logs']) == 1
    entry = snap['logs'][0]
    assert entry['level'] == 'info'
    assert entry['message'] == 'hello'
    assert entry['fields'] == {'user': 'alice'}
    assert isinstance(entry['at'], float)


def test_log_coerces_level_and_message() -> None:
    _setup()
    obs.log(42, 7, None)
    entry = obs.snapshot()['logs'][0]
    assert entry['level'] == '42'
    assert entry['message'] == '7'
    assert entry['fields'] == {}


def test_log_default_fields_when_none() -> None:
    _setup()
    obs.log('debug', 'msg', None)
    assert obs.snapshot()['logs'][0]['fields'] == {}


def test_info_warn_error_levels() -> None:
    _setup()
    obs.info('i', {})
    obs.warn('w', {})
    obs.error('e', {})
    levels = [entry['level'] for entry in obs.snapshot()['logs']]
    assert levels == ['info', 'warn', 'error']


def test_metric_and_metric_value() -> None:
    _setup()
    obs.metric('requests', 3)
    obs.metric('latency', 0.5)
    assert obs.metric_value('requests') == 3.0
    assert obs.metric_value('latency') == 0.5


def test_metric_value_unknown_returns_zero() -> None:
    _setup()
    assert obs.metric_value('missing') == 0


def test_metric_coerces_name() -> None:
    _setup()
    obs.metric(5, 1)
    assert obs.metric_value('5') == 1.0


def test_metric_updates_existing() -> None:
    _setup()
    obs.metric('count', 1)
    obs.metric('count', 2)
    assert obs.metric_value('count') == 2.0


def test_trace_begin_returns_incrementing_ids() -> None:
    _setup()
    assert obs.trace_begin('a') == 1
    assert obs.trace_begin('b') == 2


def test_trace_begin_adds_entry() -> None:
    _setup()
    trace_id = obs.trace_begin('work')
    trace = obs.snapshot()['traces'][0]
    assert trace['id'] == trace_id
    assert trace['name'] == 'work'
    assert trace['start'] is not None
    assert trace['end'] is None
    assert trace['fields'] == {}


def test_trace_end_sets_duration_and_fields() -> None:
    _setup()
    trace_id = obs.trace_begin('work')
    obs.trace_end(trace_id, {'ok': True})
    trace = obs.snapshot()['traces'][0]
    assert trace['end'] is not None
    assert trace['duration'] >= 0
    assert trace['fields'] == {'ok': True}


def test_trace_end_unknown_id_is_noop() -> None:
    _setup()
    obs.trace_begin('work')
    obs.trace_end(999, {})
    trace = obs.snapshot()['traces'][0]
    assert trace['end'] is None


def test_snapshot_shape() -> None:
    _setup()
    snap = obs.snapshot()
    assert set(snap) == {'logs', 'metrics', 'traces'}
    assert snap['logs'] == []
    assert snap['metrics'] == {}
    assert snap['traces'] == []


def test_snapshot_isolates_from_mutations() -> None:
    _setup()
    obs.metric('m', 1)
    snap = obs.snapshot()
    snap['metrics']['m'] = 99
    snap['logs'].append('junk')
    assert obs.metric_value('m') == 1.0
    assert len(obs.snapshot()['logs']) == 0


def test_profile_runs_fn_and_returns_ms() -> None:
    _setup()
    calls: list[int] = []

    def work() -> None:
        calls.append(1)

    elapsed = obs.profile(work, 5)
    assert len(calls) == 5
    assert elapsed >= 0


def test_profile_minimum_one_iteration() -> None:
    _setup()
    calls: list[int] = []

    def work() -> None:
        calls.append(1)

    obs.profile(work, 0)
    obs.profile(work, -3)
    assert len(calls) == 2
