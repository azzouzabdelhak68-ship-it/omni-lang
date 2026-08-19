"""Unit tests for every OMNISYS.test registry function."""

from __future__ import annotations

import omnisys_core
import omnisys_test
import pytest

ALWAYS_TRUE_LIMIT = 1000
FAILING_LIMIT = 500
SAMPLES_COUNT = 10
BENCH_RUNS = 5


def _noop() -> None:
    """Do nothing; a trivial benchmark workload."""


def test_fail_raises_panic_with_prefix() -> None:
    with pytest.raises(omnisys_core.PanicError, match=r'^test assertion failed: boom$'):
        omnisys_test.fail('boom')


def test_assert_true_passes_for_true() -> None:
    assert omnisys_test.assert_true(True) is None


def test_assert_true_raises_default_message() -> None:
    with pytest.raises(omnisys_core.PanicError, match=r'^test assertion failed: expected true$'):
        omnisys_test.assert_true(False)


def test_assert_true_raises_custom_message() -> None:
    with pytest.raises(omnisys_core.PanicError, match=r'^test assertion failed: custom message$'):
        omnisys_test.assert_true(False, 'custom message')


def test_assert_eq_passes_for_key_order() -> None:
    assert omnisys_test.assert_eq({'a': 1, 'b': 2}, {'b': 2, 'a': 1}) is None


def test_assert_eq_passes_for_equal_values() -> None:
    assert omnisys_test.assert_eq([1, 2, 3], [1, 2, 3]) is None


def test_assert_eq_raises_on_mismatch_with_both_values() -> None:
    with pytest.raises(omnisys_core.PanicError) as exc_info:
        omnisys_test.assert_eq({'x': 1}, {'x': 2})
    assert str(exc_info.value) == 'test assertion failed: assert_eq: expected {"x": 2} got {"x": 1}'


def test_assert_eq_raises_on_type_mismatch() -> None:
    with pytest.raises(omnisys_core.PanicError):
        omnisys_test.assert_eq(1, '1')


def test_assert_eq_uses_default_str_for_unsupported_values() -> None:
    marker = object()
    assert omnisys_test.assert_eq({'a': marker}, {'a': marker}) is None


def test_assert_throws_true_when_fn_raises() -> None:
    def boom() -> None:
        raise ValueError('boom')

    assert omnisys_test.assert_throws(boom) is True


def test_assert_throws_false_when_fn_succeeds() -> None:
    def ok() -> None:
        pass

    assert omnisys_test.assert_throws(ok) is False


def test_property_returns_true_for_always_true_prop() -> None:
    assert omnisys_test.property(lambda v: v < ALWAYS_TRUE_LIMIT, 100) is True


def test_property_raises_with_sample_info() -> None:
    with pytest.raises(
        omnisys_core.PanicError,
        match=r'^test assertion failed: property failed at sample \d+ with value \d+$',
    ):
        omnisys_test.property(lambda v: v < FAILING_LIMIT, 1000)


def test_property_honors_samples_count() -> None:
    seen: list[int] = []
    omnisys_test.property(lambda v: seen.append(v) or True, SAMPLES_COUNT)
    assert len(seen) == SAMPLES_COUNT


def test_property_zero_samples_run_once() -> None:
    seen: list[int] = []
    omnisys_test.property(lambda v: seen.append(v) or True, 0)
    assert len(seen) == 1


def test_property_negative_samples_run_once() -> None:
    seen: list[int] = []
    omnisys_test.property(lambda v: seen.append(v) or True, -7)
    assert len(seen) == 1


def test_property_is_deterministic() -> None:
    first: list[int] = []
    second: list[int] = []
    omnisys_test.property(lambda v: first.append(v) or True, 20)
    omnisys_test.property(lambda v: second.append(v) or True, 20)
    assert first == second


def test_property_lcg_golden_sequence_matches_js() -> None:
    seen: list[int] = []
    omnisys_test.property(lambda v: seen.append(v) or True, 5)
    assert seen == [868, 467, 374, 157, 0]


def test_bench_returns_non_negative_float() -> None:
    elapsed = omnisys_test.bench(_noop, 10)
    assert isinstance(elapsed, float)
    assert elapsed >= 0.0


def test_bench_executes_fn_exact_times() -> None:
    count = 0

    def tick() -> None:
        nonlocal count
        count += 1

    omnisys_test.bench(tick, BENCH_RUNS)
    assert count == BENCH_RUNS


def test_bench_zero_iterations_run_once() -> None:
    count = 0

    def tick() -> None:
        nonlocal count
        count += 1

    omnisys_test.bench(tick, 0)
    assert count == 1


def test_bench_negative_iterations_run_once() -> None:
    count = 0

    def tick() -> None:
        nonlocal count
        count += 1

    omnisys_test.bench(tick, -3)
    assert count == 1
