"""Property tests for OMNISYS.platform."""

from __future__ import annotations

import omnisys_platform as platform
from hypothesis import given, settings
from hypothesis import strategies as st


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=200))
def test_sleep_ms_returns_its_input(ms: int) -> None:
    assert platform.sleep_ms(ms) == ms


@given(st.none())
def test_now_is_between_sequential_calls(_: None) -> None:
    first = platform.now()
    second = platform.now()
    assert first <= second


@given(st.none())
def test_capabilities_always_contains_none_and_process(_: None) -> None:
    caps = platform.capabilities()
    assert 'none' in caps
    assert 'process' in caps
