"""Unit tests for every OMNISYS.error function."""

import pytest
from omnisys_error import (
    OmniError,
    error,
    error_code,
    error_code_of,
    error_has_context,
    error_message,
    error_to_dict,
    error_with_context,
    is_error,
    throw_error,
)


def test_error_default_code() -> None:
    err = error('boom')
    assert err['tag'] == 'error'
    assert err['message'] == 'boom'
    assert err['code'] == 'E-OMNI'
    assert err['context'] == {}
    assert 'stack' in err
    assert isinstance(err['stack'], str)


def test_error_code_sets_code() -> None:
    err = error_code('boom', 'E-CUSTOM')
    assert err['tag'] == 'error'
    assert err['message'] == 'boom'
    assert err['code'] == 'E-CUSTOM'
    assert err['context'] == {}


def test_error_message_dict_with_message() -> None:
    assert error_message(error_code('boom', 'E-X')) == 'boom'
    assert error_message(error('boom')) == 'boom'


def test_error_message_dict_without_message_falls_back_to_str() -> None:
    err = {'code': 'E-X'}
    assert error_message(err) == str(err)


def test_error_message_non_dict_falls_back_to_str() -> None:
    assert error_message('plain') == 'plain'
    assert error_message(42) == '42'
    assert error_message(None) == 'None'


def test_error_code_of_present() -> None:
    assert error_code_of(error_code('boom', 'E-CUSTOM')) == 'E-CUSTOM'
    assert error_code_of(error('boom')) == 'E-OMNI'


def test_error_code_of_missing_is_empty() -> None:
    assert error_code_of({'message': 'boom'}) == ''
    assert error_code_of({}) == ''
    assert error_code_of('not an error') == ''


def test_error_with_context_adds_and_does_not_mutate() -> None:
    err = error('boom')
    out = error_with_context(err, 'user', 'alice')
    assert out is not err
    assert out['message'] == 'boom'
    assert out['code'] == 'E-OMNI'
    assert out['context'] == {'user': 'alice'}
    assert err['context'] == {}


def test_error_with_context_preserves_prior_context() -> None:
    err = error_with_context(error('boom'), 'a', 1)
    out = error_with_context(err, 'b', 2)
    assert out['context'] == {'a': 1, 'b': 2}
    assert err['context'] == {'a': 1}


def test_error_with_context_replaces_existing_key() -> None:
    err = error_with_context(error('boom'), 'a', 1)
    out = error_with_context(err, 'a', 2)
    assert out['context'] == {'a': 2}


def test_error_with_context_non_dict_context() -> None:
    err = {'tag': 'error', 'message': 'boom', 'code': 'E-X', 'context': 'oops'}
    out = error_with_context(err, 'k', 1)
    assert out['context'] == {'k': 1}
    assert err['context'] == 'oops'


def test_error_has_context_true() -> None:
    err = error_with_context(error('boom'), 'user', 'alice')
    assert error_has_context(err, 'user') is True


def test_error_has_context_false_when_missing() -> None:
    err = error_with_context(error('boom'), 'user', 'alice')
    assert error_has_context(err, 'missing') is False
    assert error_has_context(error('boom'), 'user') is False


def test_error_has_context_false_for_non_dict_context() -> None:
    err = {'tag': 'error', 'message': 'boom', 'context': 'oops'}
    assert error_has_context(err, 'k') is False


def test_error_to_dict_normalizes() -> None:
    err = {'tag': 'error', 'message': 'boom', 'code': 'E-X', 'context': {'k': 1}, 'extra': True}
    out = error_to_dict(err)
    assert out['tag'] == 'error'
    assert out['message'] == 'boom'
    assert out['code'] == 'E-X'
    assert out['context'] == {'k': 1}
    assert 'stack' in out


def test_error_to_dict_from_minimal() -> None:
    err = {'tag': 'error'}
    out = error_to_dict(err)
    assert out['tag'] == 'error'
    assert out['message'] == str(err)
    assert out['code'] == ''
    assert out['context'] == {}


def test_throw_error_raises_omnierror() -> None:
    err = error_with_context(error_code('boom', 'E-X'), 'user', 'alice')
    with pytest.raises(OmniError) as excinfo:
        throw_error(err)
    raised = excinfo.value
    assert raised.message == 'boom'
    assert raised.code == 'E-X'
    assert raised.context == {'user': 'alice'}
    assert str(raised) == 'boom'


def test_throw_error_non_dict_context() -> None:
    err = {'tag': 'error', 'message': 'boom', 'code': 'E-X', 'context': 'oops'}
    with pytest.raises(OmniError) as excinfo:
        throw_error(err)
    assert excinfo.value.context == {}


def test_omnierror_defaults() -> None:
    err = OmniError('boom')
    assert err.message == 'boom'
    assert err.code == 'E-OMNI'
    assert err.context == {}
    assert str(err) == 'boom'
    assert isinstance(err, Exception)


def test_is_error_true() -> None:
    assert is_error(error('boom')) is True
    assert is_error(error_code('boom', 'E-X')) is True
    assert is_error({'tag': 'error'}) is True


def test_is_error_false() -> None:
    assert is_error({'tag': 'ok', 'value': 1}) is False
    assert is_error({'message': 'boom'}) is False
    assert is_error('error') is False
    assert is_error(42) is False
    assert is_error(None) is False
    assert is_error(['tag']) is False
    assert is_error({}) is False
