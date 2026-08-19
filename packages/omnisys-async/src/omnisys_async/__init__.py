"""OMNISYS.async — Task / Future / Stream-style concurrency primitives.

Portable async/await primitives built on :mod:`asyncio`, mirroring the JS
runtime ``omnisys/async.js``. Tasks are awaitables (coroutines/Tasks); the
Channel is a bounded FIFO backed by ``asyncio.Queue``.

The advanced escape (distributed actors + clustering) lives in the
:mod:`omnisys_async.actor` submodule — it is NOT part of the portable
registry contract and declares the ``network`` capability.
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from omnisys_core import panic

from . import actor as actor  # noqa: F401 - re-exported submodule (escape)

T = TypeVar('T')


def task(fn: Callable[[], T]) -> Awaitable[T]:
    """Return an awaitable that runs ``fn()`` and resolves to its result."""

    async def _run() -> T:
        return fn()

    return _run()


async def delay(ms: float) -> None:
    """Resolve after ``ms`` milliseconds (mirrors ``setTimeout``)."""
    await asyncio.sleep(ms / 1000.0)


async def all(tasks: list[Awaitable[T]]) -> list[T]:
    """Resolve when every task resolves; fail fast like ``Promise.all``."""
    return await asyncio.gather(*tasks)


async def race(tasks: list[Awaitable[T]]) -> T:
    """Resolve with the first task to complete (any outcome)."""
    if not tasks:
        panic('async.race on empty list')
    pending: set[asyncio.Future[Any]] = {asyncio.ensure_future(t) for t in tasks}
    done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
    return cast(T, next(iter(done)).result())


async def any(tasks: list[Awaitable[T]]) -> T:
    """Resolve with the first task to succeed; raise if all fail."""
    if not tasks:
        panic('async.any on empty list')
    pending: set[asyncio.Future[Any]] = {asyncio.ensure_future(t) for t in tasks}
    first_error: BaseException | None = None
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for fut in done:
            try:
                return cast(T, fut.result())
            except BaseException as exc:  # noqa: BLE001 - first failure is re-raised below
                if first_error is None:
                    first_error = exc
    assert first_error is not None
    raise first_error


async def timeout(task: Awaitable[T], ms: float) -> T:
    """Resolve with ``task`` or raise ``asyncio.TimeoutError`` after ``ms``."""
    return await asyncio.wait_for(task, timeout=ms / 1000.0)


def channel(capacity: int) -> dict[str, Any]:
    """Create a bounded FIFO channel (capacity 0 = unbounded)."""
    return {'tag': 'channel', 'capacity': capacity, 'queue': asyncio.Queue(maxsize=capacity)}


async def channel_send(channel: dict[str, Any], value: Any) -> None:
    """Send ``value``; block while the channel is full."""
    await channel['queue'].put(value)


async def channel_recv(channel: dict[str, Any]) -> Any:
    """Receive the next value; block while the channel is empty."""
    return await channel['queue'].get()


def is_promise(x: Any) -> bool:
    """Return True when ``x`` is awaitable (mirrors the JS ``x.then`` check)."""
    return inspect.isawaitable(x)


__all__ = [
    'task',
    'delay',
    'all',
    'race',
    'any',
    'timeout',
    'channel',
    'channel_send',
    'channel_recv',
    'is_promise',
]
