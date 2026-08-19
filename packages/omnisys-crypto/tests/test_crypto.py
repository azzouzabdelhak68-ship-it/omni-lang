"""Unit tests for OMNISYS.crypto."""

from __future__ import annotations

import omnisys_crypto as crypto
import pytest


def test_sha256_known_vector_empty() -> None:
    assert crypto.sha256('') == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


def test_sha256_known_vector_abc() -> None:
    expected = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    assert crypto.sha256('abc') == expected


def test_sha256_coerces_input_to_string() -> None:
    assert crypto.sha256(123) == crypto.sha256('123')


def test_sha1_known_vector_empty() -> None:
    assert crypto.sha1('') == 'da39a3ee5e6b4b0d3255bfef95601890afd80709'


def test_sha1_known_vector_abc() -> None:
    assert crypto.sha1('abc') == 'a9993e364706816aba3e25717850c26c9cd0d89d'


def test_hmac_known_vector() -> None:
    assert crypto.hmac('key', 'The quick brown fox jumps over the lazy dog') == (
        'f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8'
    )


def test_hmac_key_and_data_coerced() -> None:
    assert crypto.hmac(1, 2) == crypto.hmac('1', '2')


def test_to_hex_ascii() -> None:
    assert crypto.to_hex('abc') == '616263'


def test_to_hex_empty() -> None:
    assert crypto.to_hex('') == ''


def test_to_hex_uses_utf16_code_units() -> None:
    assert crypto.to_hex('\u00e9') == 'e9'


def test_to_hex_pads_below_16() -> None:
    assert crypto.to_hex('\x01') == '01'


def test_from_hex_round_trip_ascii() -> None:
    assert crypto.from_hex('616263') == 'abc'


def test_from_hex_ignores_trailing_odd_digit() -> None:
    assert crypto.from_hex('6162637') == 'abc'


def test_from_hex_invalid_raises() -> None:
    with pytest.raises(ValueError):
        crypto.from_hex('zz')


def test_to_hex_from_hex_round_trip() -> None:
    text = 'hello \u00e9 world'
    assert crypto.from_hex(crypto.to_hex(text)) == text


def test_random_bytes_returns_hex_of_requested_length() -> None:
    out = crypto.random_bytes(16)
    assert len(out) == 32
    assert all(c in '0123456789abcdef' for c in out)


def test_random_bytes_clamps_negative() -> None:
    assert crypto.random_bytes(-5) == ''


def test_random_bytes_zero() -> None:
    assert crypto.random_bytes(0) == ''


def test_random_bytes_is_probably_unique() -> None:
    assert crypto.random_bytes(16) != crypto.random_bytes(16)


def test_encrypt_aes_shape() -> None:
    cipher = crypto.encrypt_aes('secret', 'payload')
    assert cipher['tag'] == 'cipher'
    assert len(cipher['iv']) == 32
    assert cipher['data']


def test_encrypt_aes_decrypt_aes_round_trip() -> None:
    key = 'top-secret'
    text = 'attack at dawn'
    cipher = crypto.encrypt_aes(key, text)
    assert crypto.decrypt_aes(cipher, key) == text


def test_decrypt_aes_wrong_key_fails() -> None:
    cipher = crypto.encrypt_aes('key-a', 'hello')
    assert crypto.decrypt_aes(cipher, 'key-b') != 'hello'


def test_encrypt_aes_is_nondeterministic_iv() -> None:
    a = crypto.encrypt_aes('k', 'same')
    b = crypto.encrypt_aes('k', 'same')
    assert a['iv'] != b['iv']


def test_kdf_is_deterministic() -> None:
    assert crypto.kdf('pw', 'salt', 1000) == crypto.kdf('pw', 'salt', 1000)


def test_kdf_changes_with_salt() -> None:
    assert crypto.kdf('pw', 'salt-a', 10) != crypto.kdf('pw', 'salt-b', 10)


def test_kdf_changes_with_iterations() -> None:
    assert crypto.kdf('pw', 'salt', 10) != crypto.kdf('pw', 'salt', 11)


def test_kdf_zero_iterations_becomes_one() -> None:
    assert crypto.kdf('pw', 'salt', 0) == crypto.kdf('pw', 'salt', 1)


def test_kdf_output_is_hex() -> None:
    out = crypto.kdf('pw', 'salt', 5)
    assert len(out) == 64
    assert all(c in '0123456789abcdef' for c in out)


def test_constant_time_eq_equal() -> None:
    assert crypto.constant_time_eq('secret', 'secret') is True


def test_constant_time_eq_different() -> None:
    assert crypto.constant_time_eq('secret', 'secret!') is False


def test_constant_time_eq_different_lengths() -> None:
    assert crypto.constant_time_eq('abc', 'abcdef') is False


def test_constant_time_eq_empty() -> None:
    assert crypto.constant_time_eq('', '') is True
