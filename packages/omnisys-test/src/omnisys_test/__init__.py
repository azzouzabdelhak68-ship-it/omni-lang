"""OMNISYS.test — assertions, deterministic property testing, benchmarking."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any, NoReturn

from omnisys_core import panic

__all__ = [
    'assert_true',
    'assert_eq',
    'assert_throws',
    'property',
    'bench',
    'fail',
]


def fail(msg: str) -> NoReturn:
    """Abort the current test run with a failed-assertion panic."""
    panic('test assertion failed: ' + str(msg))
    raise AssertionError('unreachable')


def assert_true(cond: bool, msg: str | None = None) -> None:
    """Panic unless ``cond`` is truthy; the default message is ``expected true``."""
    if not cond:
        fail(msg or 'expected true')


def assert_eq(actual: Any, expected: Any) -> None:
    """Panic unless the canonical-JSON forms of ``actual`` and ``expected`` match."""
    actual_str = json.dumps(actual, sort_keys=True, default=str)
    expected_str = json.dumps(expected, sort_keys=True, default=str)
    if actual_str != expected_str:
        fail('assert_eq: expected ' + expected_str + ' got ' + actual_str)


def assert_throws(fn: Callable[[], Any]) -> bool:
    """Return True when ``fn()`` raises any exception, else False."""
    try:
        fn()
    except Exception:
        return True
    return False


def _lcg(seed: int) -> Callable[[], int]:
    """Deterministic 32-bit linear congruential generator mirroring the JS runtime."""
    state = seed & 0xFFFFFFFF

    def next_value() -> int:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state

    return next_value


def property(prop: Callable[[int], Any], samples: int) -> bool:
    """Run ``prop`` over deterministic samples, panicking on the first falsy result."""
    rand = _lcg(12345)
    n = max(1, int(samples))
    for i in range(n):
        value = rand() % 1000
        if not prop(value):
            fail('property failed at sample ' + str(i) + ' with value ' + str(value))
    return True


def bench(fn: Callable[[], Any], iterations: int) -> float:
    """Run ``fn`` ``iterations`` times and return the elapsed milliseconds as a float."""
    n = max(1, int(iterations))
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - start) * 1000.0
