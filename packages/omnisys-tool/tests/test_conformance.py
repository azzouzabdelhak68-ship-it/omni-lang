"""Lock OMNISYS.tool to the compiler registry contract."""

from __future__ import annotations

import omnisys_tool

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset({'check', 'explain'})


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['tool'].functions)
    assert expected <= set(omnisys_tool.__all__)
    for name in expected:
        assert callable(getattr(omnisys_tool, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['tool'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_tool.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['tool'].functions) == len(omnisys_tool.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_tool.__all__:
        impl = getattr(omnisys_tool, name)
        assert impl.__module__ == omnisys_tool.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['tool'].functions.items():
        expected = frozenset({'process'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['tool'].js_deps == ('core',)
