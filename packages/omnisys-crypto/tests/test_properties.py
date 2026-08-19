"""Property tests for OMNISYS.crypto."""

from __future__ import annotations

import omnisys_crypto as crypto
from hypothesis import given
from hypothesis import strategies as st

_ASCII = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789 _-', max_size=64)


@given(_ASCII)
def test_to_hex_from_hex_round_trip(text: str) -> None:
    assert crypto.from_hex(crypto.to_hex(text)) == text


@given(_ASCII, st.integers(min_value=0, max_value=32))
def test_random_bytes_length(key: str, n: int) -> None:
    del key
    out = crypto.random_bytes(n)
    assert len(out) == n * 2


@given(_ASCII, _ASCII)
def test_encrypt_decrypt_round_trip(key: str, text: str) -> None:
    cipher = crypto.encrypt_aes(key, text)
    assert crypto.decrypt_aes(cipher, key) == text


@given(_ASCII, _ASCII, st.integers(min_value=0, max_value=20))
def test_kdf_deterministic(password: str, salt: str, iterations: int) -> None:
    assert crypto.kdf(password, salt, iterations) == crypto.kdf(password, salt, iterations)


@given(_ASCII, _ASCII)
def test_constant_time_eq_symmetric(a: str, b: str) -> None:
    assert crypto.constant_time_eq(a, b) == (a == b)


@given(_ASCII)
def test_sha256_length(text: str) -> None:
    assert len(crypto.sha256(text)) == 64


@given(_ASCII)
def test_hmac_length(key: str) -> None:
    assert len(crypto.hmac(key, 'data')) == 64
