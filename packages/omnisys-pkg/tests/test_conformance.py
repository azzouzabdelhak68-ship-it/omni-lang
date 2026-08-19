"""Lock OMNISYS.pkg to the compiler registry contract."""

from __future__ import annotations

import omnisys_pkg

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset({'manifest', 'install'})


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['pkg'].functions)
    assert expected <= set(omnisys_pkg.__all__)
    for name in expected:
        assert callable(getattr(omnisys_pkg, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['pkg'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_pkg.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['pkg'].functions) == len(omnisys_pkg.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_pkg.__all__:
        impl = getattr(omnisys_pkg, name)
        assert impl.__module__ == omnisys_pkg.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['pkg'].functions.items():
        expected = frozenset({'filesystem'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['pkg'].js_deps == ('core', 'serde', 'fs')
