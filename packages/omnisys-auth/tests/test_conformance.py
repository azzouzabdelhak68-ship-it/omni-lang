"""Lock OMNISYS.auth to the compiler registry contract."""

from __future__ import annotations

import omnisys_auth

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset(
    {
        'token',
        'verify_token',
        'token_subject',
        'hash_password',
        'verify_password',
        'session_new',
        'session_valid',
    }
)


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['auth'].functions)
    assert expected <= set(omnisys_auth.__all__)
    for name in expected:
        assert callable(getattr(omnisys_auth, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['auth'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_auth.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['auth'].functions) == len(omnisys_auth.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_auth.__all__:
        impl = getattr(omnisys_auth, name)
        assert impl.__module__ == omnisys_auth.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['auth'].functions.items():
        expected = frozenset({'secrets'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['auth'].js_deps == ('core', 'crypto')
