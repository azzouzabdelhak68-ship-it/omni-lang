"""Lock OMNISYS.http to the compiler registry contract."""

import omnisys_http

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = {'register', 'register_transport'}
_IMPURE = {'send', 'get', 'post', 'put', 'delete', 'json_get', 'json_post'}


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['http'].functions)
    assert expected <= set(omnisys_http.__all__)
    for name in expected:
        assert callable(getattr(omnisys_http, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['http'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_http.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['http'].functions) == len(omnisys_http.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_http.__all__:
        impl = getattr(omnisys_http, name)
        assert impl.__module__ == omnisys_http.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['http'].functions.items():
        expected = frozenset({'network'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected
