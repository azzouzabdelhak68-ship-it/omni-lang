"""Property tests for OMNISYS.auth."""

from __future__ import annotations

import omnisys_auth as auth
from hypothesis import given
from hypothesis import strategies as st

_SUBJECTS = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-', max_size=32)
_SECRETS = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', max_size=32)


@given(_SUBJECTS, _SECRETS)
def test_token_verify_token_round_trip(subject: str, secret: str) -> None:
    tok = auth.token(subject, {}, secret)
    result = auth.verify_token(tok, secret)
    assert result['valid'] is True
    assert result['sub'] == subject


@given(_SUBJECTS)
def test_token_subject_round_trip(subject: str) -> None:
    tok = auth.token(subject, {}, '')
    assert auth.token_subject(tok) == subject


@given(_SECRETS)
def test_verify_token_rejects_tampered(secret: str) -> None:
    tok = auth.token('alice', {}, secret)
    assert auth.verify_token(tok + 'x', secret)['valid'] is False


@given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', max_size=32), _SECRETS)
def test_hash_verify_password_round_trip(password: str, salt: str) -> None:
    hashed = auth.hash_password(password, salt)
    assert auth.verify_password(password, hashed) is True


@given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', max_size=32), _SECRETS)
def test_verify_password_wrong_password_fails(password: str, salt: str) -> None:
    hashed = auth.hash_password(password, salt)
    assert auth.verify_password(password + 'x', hashed) is False


@given(_SUBJECTS, _SECRETS, st.integers(min_value=1, max_value=3600))
def test_session_valid_within_ttl(subject: str, secret: str, ttl: int) -> None:
    session = auth.session_new(secret, subject, ttl)
    assert auth.session_valid(session) is True


@given(_SUBJECTS)
def test_session_new_token_matches_subject(subject: str) -> None:
    session = auth.session_new('', subject, 3600)
    assert auth.token_subject(session['token']) == subject
