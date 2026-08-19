"""OMNISYS.auth — signed tokens, password hashing, sessions.

Python reference implementation of the OMNISYS ``auth`` module (v6),
mirroring the JS reference lane ``omnisys/auth.js`` and satisfying the
registry contract (``OMNISYS_MODULES["auth"]``). Tokens are compact signed
JSON (``body.signature``) where the body is base64url of the JSON payload and
the signature is the first 24 hex chars of HMAC-SHA256 over the body. All
seven functions declare the ``secrets`` capability.
"""

import base64
import json
import time
from typing import Any, TypeAlias

from omnisys_crypto import constant_time_eq, hmac, kdf

__all__ = [
    'token',
    'verify_token',
    'token_subject',
    'hash_password',
    'verify_password',
    'session_new',
    'session_valid',
]

Token: TypeAlias = str
Session: TypeAlias = dict[str, Any]
VerifyResult: TypeAlias = dict[str, Any]

_SIGNATURE_LENGTH = 24
_MALFORMED_PARTS = 2
_HASH_PARTS = 2
_KDF_ROUNDS = 128
_DEFAULT_TTL = 3600


def _b64url(text: str) -> str:
    """Base64url-encode ``text`` (UTF-8) without padding."""
    return base64.urlsafe_b64encode(text.encode('utf-8')).decode('ascii').rstrip('=')


def _unb64url(part: str) -> str:
    """Base64url-decode ``part`` (UTF-8), tolerating missing padding."""
    b64 = part + '=' * (-len(part) % 4)
    return base64.urlsafe_b64decode(b64).decode('utf-8')


def _sign(payload: dict[str, Any], secret: Any) -> Token:
    body = _b64url(json.dumps(payload))
    sig = hmac(secret, body)[:_SIGNATURE_LENGTH]
    return body + '.' + sig


def token(subject: Any, claims: Any, secret: Any) -> Token:
    """Create a signed token for ``subject`` with optional extra ``claims``."""
    payload: dict[str, Any] = {'sub': str(subject), 'iat': int(time.time())}
    if claims:
        payload.update(claims)
    return _sign(payload, secret)


def verify_token(token_value: Any, secret: Any) -> VerifyResult:
    """Verify ``token_value`` against ``secret``; returns a valid/result map."""
    parts = str(token_value).split('.')
    if len(parts) != _MALFORMED_PARTS:
        return {'valid': False, 'reason': 'malformed'}
    body = parts[0]
    sig = hmac(secret, body)[:_SIGNATURE_LENGTH]
    if not constant_time_eq(sig, parts[1]):
        return {'valid': False, 'reason': 'signature'}
    try:
        payload = json.loads(_unb64url(body))
    except (ValueError, UnicodeDecodeError):
        return {'valid': False, 'reason': 'payload'}
    if not isinstance(payload, dict):
        return {'valid': False, 'reason': 'payload'}
    return {'valid': True, 'sub': payload.get('sub'), 'claims': payload}


def token_subject(token_value: Any) -> str:
    """Return the subject of ``token_value``, or ``''`` when invalid."""
    result = verify_token(token_value, '')
    return result['sub'] if result['valid'] else ''


def hash_password(password: Any, salt: Any) -> str:
    """Hash ``password`` with ``salt`` into ``<salt>$<kdf-hash>``."""
    hash_value = kdf(str(password), str(salt), _KDF_ROUNDS)
    return str(salt) + '$' + hash_value


def verify_password(password: Any, hash_value: Any) -> bool:
    """Check ``password`` against a hash produced by :func:`hash_password`."""
    parts = str(hash_value).split('$')
    if len(parts) != _HASH_PARTS:
        return False
    return constant_time_eq(parts[1], kdf(str(password), parts[0], _KDF_ROUNDS))


def session_new(secret: Any, subject: Any, ttl_seconds: Any) -> Session:
    """Create a session map with a signed token expiring after ``ttl_seconds``."""
    token_value = token(subject, {}, secret)
    return {
        'tag': 'session',
        'token': token_value,
        'subject': subject,
        'expiresAt': int(time.time()) + (ttl_seconds or _DEFAULT_TTL),
    }


def session_valid(session: Any) -> bool:
    """Return True when ``session`` exists and has not yet expired."""
    if not session:
        return False
    return int(time.time()) < int(session['expiresAt'])
