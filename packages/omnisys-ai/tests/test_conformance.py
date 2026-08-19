"""Lock OMNISYS.ai to the compiler registry contract."""

from __future__ import annotations

import omnisys_ai

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset()


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['ai'].functions)
    assert expected <= set(omnisys_ai.__all__)
    for name in expected:
        assert callable(getattr(omnisys_ai, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['ai'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_ai.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['ai'].functions) == len(omnisys_ai.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_ai.__all__:
        impl = getattr(omnisys_ai, name)
        assert impl.__module__ == omnisys_ai.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['ai'].functions.items():
        expected = frozenset() if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['ai'].js_deps == ('core',)
