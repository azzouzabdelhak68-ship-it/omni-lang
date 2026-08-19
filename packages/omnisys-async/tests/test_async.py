"""Unit tests for the OMNISYS.async package (registry contract)."""

import asyncio
import time

import pytest
from omnisys_async import (
    all,
    any,
    channel,
    channel_recv,
    channel_send,
    delay,
    is_promise,
    race,
    task,
    timeout,
)
from omnisys_core import PanicError


async def test_task_runs_and_returns_result() -> None:
    assert await task(lambda: 42) == 42


async def test_task_result_types_preserved() -> None:
    assert await task(lambda: 'hello') == 'hello'


async def test_delay_returns_none_and_waits() -> None:
    start = time.perf_counter()
    result = await delay(50)
    elapsed = time.perf_counter() - start
    assert result is None
    assert elapsed >= 0.04


async def test_all_returns_results_in_order() -> None:
    results = await all([task(lambda: 1), task(lambda: 2), task(lambda: 3)])
    assert results == [1, 2, 3]


async def test_all_fails_fast() -> None:
    def boom() -> int:
        raise ValueError('boom')

    with pytest.raises(ValueError, match='boom'):
        await all([task(boom), task(lambda: 2)])


async def test_all_empty() -> None:
    assert await all([]) == []


async def test_race_returns_first_completed() -> None:
    result = await race([delay(1.0), task(lambda: 'fast')])
    assert result == 'fast'


async def test_race_returns_first_completed_slow() -> None:
    result = await race([task(lambda: 'a'), task(lambda: 'b')])
    assert result in ('a', 'b')


async def test_race_empty_panics() -> None:
    with pytest.raises(PanicError, match='race'):
        await race([])


async def test_any_picks_the_succeeding_task() -> None:
    def boom() -> str:
        raise ValueError('boom')

    result = await any([task(boom), task(lambda: 'ok')])
    assert result == 'ok'


async def test_any_raises_when_all_fail() -> None:
    def boom() -> str:
        raise ValueError('boom')

    with pytest.raises(ValueError, match='boom'):
        await any([task(boom), task(boom)])


async def test_any_empty_panics() -> None:
    with pytest.raises(PanicError, match='any'):
        await any([])


async def test_timeout_returns_fast_result() -> None:
    assert await timeout(delay(5), 1000) is None


async def test_timeout_raises_on_slow_task() -> None:
    with pytest.raises(asyncio.TimeoutError):
        await timeout(delay(1.0), 0.05)


async def test_channel_fifo_order() -> None:
    ch = channel(2)
    await channel_send(ch, 'a')
    await channel_send(ch, 'b')
    assert await channel_recv(ch) == 'a'
    assert await channel_recv(ch) == 'b'


async def test_channel_send_blocks_when_full() -> None:
    ch = channel(1)
    await channel_send(ch, 1)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel_send(ch, 2), timeout=0.05)
    assert await channel_recv(ch) == 1


async def test_channel_recv_blocks_when_empty() -> None:
    ch = channel(1)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(channel_recv(ch), timeout=0.05)


async def test_channel_unbounded_capacity_zero() -> None:
    ch = channel(0)
    for i in range(50):
        await channel_send(ch, i)
    assert await channel_recv(ch) == 0
    assert await channel_recv(ch) == 1


def test_channel_tag_and_capacity() -> None:
    ch = channel(3)
    assert ch['tag'] == 'channel'
    assert ch['capacity'] == 3


def test_is_promise_true_for_awaitables() -> None:
    c = task(lambda: 1)
    assert is_promise(c) is True
    c.close()
    d = delay(1)
    assert is_promise(d) is True
    d.close()


def test_is_promise_false_for_plain_values() -> None:
    assert is_promise(5) is False
    assert is_promise('x') is False
    assert is_promise(None) is False
    assert is_promise([]) is False
