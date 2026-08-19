"""OMNISYS.crypto — hashing, HMAC, hex, random bytes, AES, KDF.

Python reference implementation of the OMNISYS ``crypto`` module (v6),
mirroring the JS reference lane ``omnisys/crypto.js`` and satisfying the
registry contract (``OMNISYS_MODULES["crypto"]``). Hashing, HMAC, hex and
constant-time comparison are pure; random bytes, AES encrypt/decrypt and KDF
declare the ``secrets`` capability. Pure-Python fallbacks are unnecessary here
because :mod:`hashlib`, :mod:`hmac` and :mod:`secrets` provide the primitives
portably. Real AES-256 is an escape; the portable cipher is an XOR keystream
over a sha256-derived stream (documented in RESEARCH.md).
"""

import hashlib
import hmac as _hmac
import secrets
from typing import Any, TypeAlias

__all__ = [
    'sha256',
    'sha1',
    'hmac',
    'to_hex',
    'from_hex',
    'random_bytes',
    'encrypt_aes',
    'decrypt_aes',
    'kdf',
    'constant_time_eq',
]

Cipher: TypeAlias = dict[str, Any]


def to_hex(text: Any) -> str:
    """Encode ``text`` as lowercase hex of its UTF-16 code units (JS-compatible)."""
    return ''.join(format(ord(ch), '02x') for ch in str(text))


def from_hex(hex_text: Any) -> str:
    """Decode lowercase hex back into text; ignore a trailing odd digit."""
    h = str(hex_text)
    out: list[str] = []
    for i in range(0, len(h) - 1, 2):
        out.append(chr(int(h[i : i + 2], 16)))
    return ''.join(out)


def sha256(data: Any) -> str:
    """Return the lowercase SHA-256 hex digest of ``str(data)``."""
    return hashlib.sha256(str(data).encode('utf-8')).hexdigest()


def sha1(data: Any) -> str:
    """Return the lowercase SHA-1 hex digest of ``str(data)``."""
    return hashlib.sha1(str(data).encode('utf-8')).hexdigest()


def hmac(key: Any, data: Any) -> str:
    """Return the HMAC-SHA256 hex digest of ``data`` keyed by ``key``."""
    return _hmac.new(
        str(key).encode('utf-8'), str(data).encode('utf-8'), hashlib.sha256
    ).hexdigest()


def random_bytes(n: Any) -> str:
    """Return ``max(0, int(n))`` cryptographically secure random bytes as hex."""
    return secrets.token_hex(max(0, int(n)))


def _key_stream(hex_key: str, length: int) -> str:
    """Return ``length`` hex characters from the sha256 counter keystream."""
    out = ''
    counter = 0
    while len(out) < length:
        out += sha256(hex_key + ':' + str(counter))
        counter += 1
    return out


def encrypt_aes(key: Any, text: Any) -> Cipher:
    """Encrypt ``text`` with an XOR keystream over ``key``, returning a cipher map."""
    hex_key = sha256(str(key))
    stream = _key_stream(hex_key, len(str(text)) * 2)
    cipher_chars: list[str] = []
    for i, ch in enumerate(str(text)):
        cipher_chars.append(chr(ord(ch) ^ int(stream[i * 2 : i * 2 + 2], 16)))
    return {'tag': 'cipher', 'iv': random_bytes(16), 'data': to_hex(''.join(cipher_chars))}


def decrypt_aes(cipher: Cipher, key: Any) -> str:
    """Decrypt a ``{'data': hex}`` cipher map produced by :func:`encrypt_aes`."""
    hex_key = sha256(str(key))
    raw = from_hex(cipher['data'])
    stream = _key_stream(hex_key, len(raw) * 2)
    plain_chars: list[str] = []
    for i, ch in enumerate(raw):
        plain_chars.append(chr(ord(ch) ^ int(stream[i * 2 : i * 2 + 2], 16)))
    return ''.join(plain_chars)


def kdf(password: Any, salt: Any, iterations: Any) -> str:
    """Derive a hex key from ``password``/``salt`` over ``max(1, int(iterations))`` rounds."""
    hash_ = sha256(str(password) + ':' + str(salt))
    for i in range(max(1, int(iterations))):
        hash_ = sha256(hash_ + ':' + str(i))
    return hash_


def constant_time_eq(a: Any, b: Any) -> bool:
    """Return True when ``a`` and ``b`` are equal, compared in constant time."""
    return _hmac.compare_digest(str(a), str(b))
