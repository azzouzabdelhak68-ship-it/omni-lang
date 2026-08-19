"""Hypothesis property tests for OMNISYS.error invariants."""

from hypothesis import given
from hypothesis import strategies as st
from omnisys_error import (
    Error,
    error,
    error_code,
    error_has_context,
    error_message,
    error_to_dict,
    error_with_context,
    is_error,
)

contexts = st.dictionaries(st.text(), st.integers())


@st.composite
def error_values(draw: st.DrawFn) -> Error:
    message = draw(st.text())
    code = draw(st.text())
    err = error_code(message, code)
    for key, value in draw(contexts).items():
        err = error_with_context(err, key, value)
    return err


@given(message=st.text())
def test_error_default_code(message: str) -> None:
    assert error(message)['code'] == 'E-OMNI'


@given(message=st.text(), code=st.text())
def test_error_message_is_built_message(message: str, code: str) -> None:
    assert error_message(error_code(message, code)) == message


@given(message=st.text(), code=st.text())
def test_to_dict_round_trip_keeps_fields(message: str, code: str) -> None:
    out = error_to_dict(error_code(message, code))
    assert out['tag'] == 'error'
    assert out['message'] == message
    assert out['code'] == code
    assert out['context'] == {}


@given(err=error_values())
def test_to_dict_round_trip_preserves_context(err: Error) -> None:
    out = error_to_dict(err)
    assert out['message'] == err['message']
    assert out['code'] == err['code']
    assert out['context'] == err['context']


@given(err=error_values())
def test_to_dict_is_idempotent(err: Error) -> None:
    assert error_to_dict(error_to_dict(err)) == error_to_dict(err)


@given(message=st.text(), code=st.text(), key=st.text(), value=st.integers())
def test_with_context_idempotent(message: str, code: str, key: str, value: int) -> None:
    err = error_code(message, code)
    once = error_with_context(err, key, value)
    twice = error_with_context(once, key, value)
    assert once['context'] == {key: value}
    assert twice['context'] == {key: value}


@given(key1=st.text(), value1=st.integers(), key2=st.text(), value2=st.integers())
def test_with_context_is_additive(key1: str, value1: int, key2: str, value2: int) -> None:
    err = error('boom')
    first = error_with_context(err, key1, value1)
    second = error_with_context(first, key2, value2)
    assert first['context'] == {key1: value1}
    assert second['context'] == {key1: value1, key2: value2}
    assert err['context'] == {}


@given(err=error_values(), key=st.text(), value=st.integers())
def test_with_context_does_not_mutate(err: Error, key: str, value: int) -> None:
    before = dict(err)
    before_context = dict(err['context'])
    out = error_with_context(err, key, value)
    assert err == before
    assert err['context'] == before_context
    assert out['context'] == {**before_context, key: value}


@given(err=error_values(), key=st.text())
def test_has_context_matches_context(err: Error, key: str) -> None:
    assert error_has_context(err, key) is (key in err['context'])


@given(err=error_values())
def test_is_error_true_for_built_errors(err: Error) -> None:
    assert is_error(err) is True
