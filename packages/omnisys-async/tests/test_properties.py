"""Property-based tests for OMNISYS.async."""

import omnisys_async as omni_async
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from omnisys_async import channel, channel_recv, channel_send, is_promise


def test_is_promise_false_for_plain_values() -> None:
    @given(st.one_of(st.none(), st.integers(), st.text(), st.booleans(), st.lists(st.integers())))
    def _check(value: object) -> None:
        assert is_promise(value) is False

    _check()


@given(st.integers(min_value=0, max_value=100))
def test_channel_shape_and_capacity(capacity: int) -> None:
    ch = channel(capacity)
    assert ch['tag'] == 'channel'
    assert ch['capacity'] == capacity
    recv = channel_recv(ch)
    assert is_promise(recv) is True
    recv.close()


@pytest.mark.asyncio
@given(st.lists(st.integers(), max_size=8))
async def test_channel_preserves_fifo_order(values: list[int]) -> None:
    ch = channel(0)
    for value in values:
        await channel_send(ch, value)
    received = [await channel_recv(ch) for _ in values]
    assert received == values


@settings(max_examples=50)
@pytest.mark.asyncio
@given(st.lists(st.integers(), min_size=1, max_size=4))
async def test_any_deterministic_with_success_tasks(values: list[int]) -> None:
    first = await omni_async.any([omni_async.task(lambda: values[0])])
    assert first == values[0]
