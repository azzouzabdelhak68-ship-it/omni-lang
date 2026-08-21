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
import sys
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


async def _with_timeout_impl(task: Awaitable[T], ms: float) -> T:
    """Resolve with ``task`` or raise ``asyncio.TimeoutError`` after ``ms``."""
    return await asyncio.wait_for(task, timeout=ms / 1000.0)


async def with_timeout(task: Awaitable[T], ms: float) -> T:
    """Resolve with ``task`` or raise ``asyncio.TimeoutError`` after ``ms``."""
    return await _with_timeout_impl(task, ms)


def interval(ms: float, fn: Callable[[], None]) -> asyncio.Task[None]:
    """Return a Task that calls ``fn`` every ``ms`` milliseconds (mirrors JS setInterval)."""

    async def _loop() -> None:
        while True:
            await asyncio.sleep(ms / 1000.0)
            fn()

    return asyncio.create_task(_loop())


def timeout(*args: Any, **kwargs: Any) -> asyncio.Task[Any]:  # noqa: ANN401
    """Overloaded ``timeout``: registry ``timeout(ms, fn)`` or legacy ``timeout(task, ms)``.

    Registry signature is ``timeout(Number, fn() -> None) -> Task`` (JS setTimeout).
    Legacy Python signature ``timeout(task, ms)`` is preserved for backwards compat
    and dispatches to :func:`with_timeout`.
    """
    if len(args) == 2 and isinstance(args[0], (int, float)) and callable(args[1]):  # noqa: PLR2004
        ms, fn = args
        ms_f = float(ms)

        async def _run_timeout() -> None:
            await asyncio.sleep(ms_f / 1000.0)
            fn()

        return asyncio.create_task(_run_timeout())
    if len(args) == 2:  # noqa: PLR2004
        task_arg, ms_val = args
        return asyncio.create_task(_with_timeout_impl(task_arg, float(ms_val)))
    if 'ms' in kwargs and 'fn' in kwargs:
        ms_f = float(kwargs['ms'])
        fn_c = kwargs['fn']

        async def _run_kw() -> None:
            await asyncio.sleep(ms_f / 1000.0)
            fn_c()

        return asyncio.create_task(_run_kw())
    if 'task' in kwargs and 'ms' in kwargs:
        return asyncio.create_task(_with_timeout_impl(kwargs['task'], float(kwargs['ms'])))
    raise TypeError('timeout expects (ms, fn) or (task, ms)')


def tick(fn: Callable[[], None]) -> asyncio.Task[None]:
    """Schedule ``fn`` on the next event-loop tick (mirrors requestAnimationFrame)."""

    async def _run() -> None:
        await asyncio.sleep(0)
        fn()

    return asyncio.create_task(_run())


def cancel(task: Any) -> None:  # noqa: ANN401
    """Cancel ``task`` if it supports cancellation (mirrors JS task.cancel)."""
    try:
        canceller = getattr(task, 'cancel', None)
        if callable(canceller):
            canceller()
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        # asyncio.Task fallback
        if hasattr(task, 'cancel'):
            task.cancel()
    except Exception:  # noqa: BLE001
        pass


async def _await_impl(task: Awaitable[T]) -> T:
    """Await ``task`` and return its result (registry ``await``)."""
    return await task


# ``await`` is a keyword, so expose via setattr for registry conformance.
setattr(sys.modules[__name__], 'await', _await_impl)


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
    'interval',
    'timeout',
    'tick',
    'cancel',
    'await',
    'all',
    'race',
    'any',
    'channel',
    'channel_send',
    'channel_recv',
    'is_promise',
    'with_timeout',
]
