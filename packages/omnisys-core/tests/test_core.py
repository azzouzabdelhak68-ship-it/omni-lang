"""Unit tests for the OMNISYS.core package (registry contract)."""

import math

import omnisys_core as core
import pytest
from omnisys_core import PanicError


def test_option_wraps_value() -> None:
    assert core.option(42) == {'tag': 'some', 'value': 42}


def test_some_is_alias_of_option() -> None:
    assert core.some('x') == {'tag': 'some', 'value': 'x'}
    assert core.some is core.option


def test_none_value() -> None:
    assert core.none() == {'tag': 'none'}


def test_is_some_true_and_false() -> None:
    assert core.is_some(core.some(1)) is True
    assert core.is_some(core.none()) is False
    assert core.is_some(None) is False
    assert core.is_some({}) is False


def test_is_none_true_and_false() -> None:
    assert core.is_none(core.none()) is True
    assert core.is_none(core.some(1)) is False
    assert core.is_none(None) is False


def test_ok_wraps_value() -> None:
    assert core.ok('ok') == {'tag': 'ok', 'value': 'ok'}


def test_err_wraps_error() -> None:
    assert core.err('boom') == {'tag': 'err', 'error': 'boom'}


def test_is_ok_true_and_false() -> None:
    assert core.is_ok(core.ok(1)) is True
    assert core.is_ok(core.err('e')) is False
    assert core.is_ok(None) is False
    assert core.is_ok({}) is False


def test_is_err_true_and_false() -> None:
    assert core.is_err(core.err('e')) is True
    assert core.is_err(core.ok(1)) is False
    assert core.is_err(None) is False


def test_panic_raises_panic_error() -> None:
    with pytest.raises(PanicError, match='boom'):
        core.panic('boom')


def test_panic_error_carries_message() -> None:
    try:
        core.panic('details')
    except PanicError as exc:
        assert exc.message == 'details'
    else:
        pytest.fail('panic did not raise')


def test_identity_returns_value() -> None:
    assert core.identity(7) == 7
    assert core.identity(None) is None


def test_type_of_each_branch() -> None:
    assert core.type_of(None) == 'none'
    assert core.type_of([]) == 'list'
    assert core.type_of([1, 2]) == 'list'
    assert core.type_of('s') == 'string'
    assert core.type_of(3) == 'number'
    assert core.type_of(3.5) == 'number'
    assert core.type_of(True) == 'boolean'
    assert core.type_of({}) == 'object'
    assert core.type_of((1,)) == 'object'


def test_abs() -> None:
    assert core.abs(-5) == 5
    assert core.abs(5) == 5


def test_min_both_orders() -> None:
    assert core.min(1, 2) == 1
    assert core.min(2, 1) == 1
    assert core.min(2, 2) == 2


def test_max_both_orders() -> None:
    assert core.max(1, 2) == 2
    assert core.max(2, 1) == 2
    assert core.max(2, 2) == 2


def test_clamp_below_inside_above() -> None:
    assert core.clamp(-5, 0, 10) == 0
    assert core.clamp(5, 0, 10) == 5
    assert core.clamp(15, 0, 10) == 10


def test_round_half_away_from_zero() -> None:
    assert core.round(2.5) == 3
    assert core.round(-1.5) == -1
    assert core.round(-2.5) == -2
    assert core.round(0.5) == 1
    assert core.round(-0.5) == 0
    assert core.round(2.4) == 2


def test_floor_and_ceil() -> None:
    assert core.floor(2.7) == 2
    assert core.floor(-2.1) == -3
    assert core.ceil(2.1) == 3
    assert core.ceil(-2.7) == -2


def test_sqrt_positive() -> None:
    assert core.sqrt(9) == 3.0


def test_sqrt_negative_is_nan() -> None:
    assert math.isnan(core.sqrt(-1))


def test_length_variants() -> None:
    assert core.length('abc') == 3
    assert core.length([1, 2]) == 2
    assert core.length({'a': 1}) == 1
    assert core.length(None) == 0
    assert core.length(42) == 0


def test_is_empty() -> None:
    assert core.is_empty('') is True
    assert core.is_empty([]) is True
    assert core.is_empty({}) is True
    assert core.is_empty('x') is False
    assert core.is_empty(None) is True


def test_version_constant() -> None:
    assert core.VERSION == '6.0.0'
