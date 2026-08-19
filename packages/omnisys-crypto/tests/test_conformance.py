"""Lock OMNISYS.crypto to the compiler registry contract."""

from __future__ import annotations

import omnisys_crypto

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset({'random_bytes', 'encrypt_aes', 'decrypt_aes', 'kdf'})


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['crypto'].functions)
    assert expected <= set(omnisys_crypto.__all__)
    for name in expected:
        assert callable(getattr(omnisys_crypto, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['crypto'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_crypto.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['crypto'].functions) == len(omnisys_crypto.__all__) - len(
        _ALLOWED_EXTRA
    )


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_crypto.__all__:
        impl = getattr(omnisys_crypto, name)
        assert impl.__module__ == omnisys_crypto.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['crypto'].functions.items():
        expected = frozenset({'secrets'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['crypto'].js_deps == ('core', 'error')
