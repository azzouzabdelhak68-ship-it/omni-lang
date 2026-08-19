"""Property tests for OMNISYS.observability."""

from __future__ import annotations

import omnisys_observability as obs
from hypothesis import given
from hypothesis import strategies as st

_NAMES = st.text(alphabet='abcdefghijklmnopqrstuvwxyz._-', max_size=32)


def _setup() -> None:
    obs.clear()


@given(_NAMES, st.integers(min_value=-1000, max_value=1000))
def test_metric_then_value(name: str, value: int) -> None:
    _setup()
    obs.metric(name, value)
    assert obs.metric_value(name) == float(value)


@given(_NAMES)
def test_metric_value_unknown_is_zero(name: str) -> None:
    _setup()
    assert obs.metric_value(name) == 0


@given(st.text(max_size=32))
def test_log_then_snapshot_contains_message(message: str) -> None:
    _setup()
    obs.log('info', message, {})
    entry = obs.snapshot()['logs'][0]
    assert entry['message'] == message


@given(_NAMES)
def test_trace_begin_ids_increment(name: str) -> None:
    _setup()
    first = obs.trace_begin(name)
    second = obs.trace_begin(name)
    assert second == first + 1


def test_clear_then_snapshot_empty() -> None:
    _setup()
    obs.log('info', 'x', {})
    obs.metric('m', 1)
    obs.trace_begin('t')
    obs.clear()
    assert obs.snapshot() == {'logs': [], 'metrics': {}, 'traces': []}


@given(_NAMES)
def test_trace_begin_adds_expected_entry(name: str) -> None:
    _setup()
    obs.trace_begin(name)
    trace = obs.snapshot()['traces'][0]
    assert trace['name'] == name
    assert trace['end'] is None
