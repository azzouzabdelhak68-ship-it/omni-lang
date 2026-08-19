# ruff: noqa: Q000
"""Lock OMNISYS.collections to the compiler registry contract."""

import omnisys_collections

from omni_compiler.omnisys_registry import OMNISYS_MODULES


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['collections'].functions)
    assert expected <= set(omnisys_collections.__all__)
    for name in expected:
        assert callable(getattr(omnisys_collections, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['collections'].functions)
    assert set(omnisys_collections.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['collections'].functions) == len(omnisys_collections.__all__)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_collections.__all__:
        impl = getattr(omnisys_collections, name)
        assert impl.__module__ == omnisys_collections.__name__


def test_registry_declares_all_functions_pure() -> None:
    for fn in OMNISYS_MODULES['collections'].functions.values():
        assert not fn.effects
