"""Unit tests for OMNISYS.auth."""

from __future__ import annotations

import base64
import json
import time

import omnisys_auth as auth


def test_token_is_two_parts() -> None:
    tok = auth.token('alice', {}, 'secret')
    assert len(tok.split('.')) == 2


def test_token_round_trip_subject() -> None:
    tok = auth.token('alice', {}, '')
    assert auth.token_subject(tok) == 'alice'


def test_token_coerces_subject_to_string() -> None:
    tok = auth.token(42, {}, '')
    assert auth.token_subject(tok) == '42'


def test_token_subject_empty_for_signed_token() -> None:
    tok = auth.token('alice', {}, 'real-secret')
    assert auth.token_subject(tok) == ''


def test_verify_token_valid() -> None:
    tok = auth.token('bob', {'role': 'admin'}, 's3cret')
    result = auth.verify_token(tok, 's3cret')
    assert result['valid'] is True
    assert result['sub'] == 'bob'


def test_verify_token_claims_present() -> None:
    tok = auth.token('bob', {'role': 'admin'}, 's3cret')
    result = auth.verify_token(tok, 's3cret')
    assert result['claims']['role'] == 'admin'
    assert result['claims']['sub'] == 'bob'


def test_verify_token_claims_override_sub() -> None:
    tok = auth.token('bob', {'sub': 'evil'}, 's3cret')
    result = auth.verify_token(tok, 's3cret')
    assert result['valid'] is True
    assert result['sub'] == 'evil'


def test_verify_token_malformed() -> None:
    result = auth.verify_token('only-once-part', 'secret')
    assert result == {'valid': False, 'reason': 'malformed'}


def test_verify_token_bad_signature() -> None:
    tok = auth.token('alice', {}, 'correct')
    result = auth.verify_token(tok, 'wrong')
    assert result == {'valid': False, 'reason': 'signature'}


def test_verify_token_tampered_body() -> None:
    tok = auth.token('alice', {}, 's')
    body, sig = tok.split('.')
    tampered = body + 'x' + '.' + sig
    assert auth.verify_token(tampered, 's') == {'valid': False, 'reason': 'signature'}


def test_verify_token_bad_payload() -> None:
    body = 'not-json'
    sig = auth.hmac('s', body)[:24]
    result = auth.verify_token(body + '.' + sig, 's')
    assert result['valid'] is False
    assert result['reason'] == 'payload'


def test_verify_token_non_dict_json_is_bad_payload() -> None:
    body = base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode('utf-8')).decode('ascii')
    body = body.rstrip('=')
    sig = auth.hmac('s', body)[:24]
    tok = body + '.' + sig
    result = auth.verify_token(tok, 's')
    assert result['valid'] is False
    assert result['reason'] == 'payload'


def test_verify_token_invalid_utf8_is_bad_payload() -> None:
    body = base64.urlsafe_b64encode(b'\xff\xfe').decode('ascii').rstrip('=')
    sig = auth.hmac('s', body)[:24]
    result = auth.verify_token(body + '.' + sig, 's')
    assert result['valid'] is False
    assert result['reason'] == 'payload'


def test_hash_password_round_trip() -> None:
    hashed = auth.hash_password('hunter2', 'salty')
    assert auth.verify_password('hunter2', hashed) is True


def test_verify_password_wrong_password() -> None:
    hashed = auth.hash_password('hunter2', 'salty')
    assert auth.verify_password('hunter3', hashed) is False


def test_verify_password_malformed_hash() -> None:
    assert auth.verify_password('hunter2', 'no-dollar-sign') is False


def test_verify_password_too_many_parts() -> None:
    assert auth.verify_password('hunter2', 'a$b$c') is False


def test_hash_password_embeds_salt() -> None:
    hashed = auth.hash_password('pw', 'salty')
    assert hashed.startswith('salty$')


def test_hash_password_salt_changes_hash() -> None:
    assert auth.hash_password('pw', 'salt-a') != auth.hash_password('pw', 'salt-b')


def test_session_new_shape() -> None:
    session = auth.session_new('', 'carol', 60)
    assert session['tag'] == 'session'
    assert session['subject'] == 'carol'
    assert auth.token_subject(session['token']) == 'carol'


def test_session_new_expiry_defaults_to_3600() -> None:
    session = auth.session_new('secret', 'carol', None)
    assert session['expiresAt'] == int(time.time()) + 3600


def test_session_valid_true() -> None:
    session = auth.session_new('secret', 'carol', 60)
    assert auth.session_valid(session) is True


def test_session_valid_expired() -> None:
    session = auth.session_new('secret', 'carol', -100)
    assert auth.session_valid(session) is False


def test_session_valid_none() -> None:
    assert auth.session_valid(None) is False


def test_session_valid_falsy() -> None:
    assert auth.session_valid({}) is False


def test_token_iat_close_to_now() -> None:
    tok = auth.token('alice', {}, 'secret')
    result = auth.verify_token(tok, 'secret')
    assert abs(result['claims']['iat'] - int(time.time())) <= 1
