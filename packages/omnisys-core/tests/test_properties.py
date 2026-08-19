"""Property-based tests for OMNISYS.core."""

import math

import omnisys_core as core
from hypothesis import given, settings
from hypothesis import strategies as st


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_clamp_keeps_value_within_bounds(x: float) -> None:
    lo = -5.0
    hi = 5.0
    assert lo <= core.clamp(x, lo, hi) <= hi


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_clamp_returns_input_when_in_bounds(x: float) -> None:
    if -5.0 <= x <= 5.0:
        assert core.clamp(x, -5.0, 5.0) == x


@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False),
)
def test_min_max_ordering(a: float, b: float) -> None:
    assert core.min(a, b) <= a
    assert core.min(a, b) <= b
    assert core.max(a, b) >= a
    assert core.max(a, b) >= b


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_round_is_floor_of_half_up(x: float) -> None:
    assert core.round(x) == math.floor(x + 0.5)


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_abs_non_negative(x: float) -> None:
    assert core.abs(x) >= 0
    assert core.abs(x) == core.abs(-x)


@given(st.floats(min_value=1e-3, max_value=1e9, allow_nan=False, allow_infinity=False))
def test_sqrt_square_round_trip(x: float) -> None:
    assert math.isclose(core.sqrt(x * x), x, rel_tol=1e-9)


@given(
    st.one_of(
        st.none(), st.text(), st.lists(st.integers()), st.dictionaries(st.text(), st.integers())
    )
)
def test_is_empty_matches_length(value: object) -> None:
    assert core.is_empty(value) == (core.length(value) == 0)


@given(st.integers())
def test_option_some_round_trip(x: int) -> None:
    wrapped = core.some(x)
    assert core.is_some(wrapped) is True
    assert core.type_of(wrapped['value']) == 'number'


@settings(max_examples=50)
@given(st.one_of(st.text(), st.integers(), st.booleans()))
def test_ok_err_tags(x: object) -> None:
    ok_res = core.ok(x)
    err_res = core.err('bad')
    assert core.is_ok(ok_res) is True
    assert core.is_err(ok_res) is False
    assert core.is_err(err_res) is True
