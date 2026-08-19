"""Hypothesis-based property tests for OMNISYS.test invariants."""

from __future__ import annotations

import omnisys_test
from hypothesis import given
from hypothesis import strategies as st

JSON_LIKE = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=25,
)


def _noop() -> None:
    """Do nothing; a trivial benchmark workload."""


@given(JSON_LIKE)
def test_assert_eq_is_reflexive(value: object) -> None:
    assert omnisys_test.assert_eq(value, value) is None


@given(st.dictionaries(st.text(), st.integers()))
def test_assert_eq_ignores_key_order(table: dict[str, int]) -> None:
    shuffled = dict(reversed(list(table.items())))
    assert omnisys_test.assert_eq(table, shuffled) is None


@given(st.integers(min_value=1, max_value=200))
def test_property_is_deterministic(samples: int) -> None:
    first: list[int] = []
    second: list[int] = []
    omnisys_test.property(lambda v: first.append(v) or True, samples)
    omnisys_test.property(lambda v: second.append(v) or True, samples)
    assert first == second


@given(st.integers(min_value=0, max_value=8))
def test_bench_returns_non_negative_for_any_iterations(iterations: int) -> None:
    assert omnisys_test.bench(_noop, iterations) >= 0.0


def test_bench_zero_and_one_timing_sanity() -> None:
    zero = omnisys_test.bench(_noop, 0)
    one = omnisys_test.bench(_noop, 1)
    assert zero >= 0.0
    assert one >= 0.0
