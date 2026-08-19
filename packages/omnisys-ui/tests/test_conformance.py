"""Lock OMNISYS.ui to the compiler registry contract."""

import omnisys_ui

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_IMPURE = {'get_value', 'get_form_data'}


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['ui'].functions)
    assert expected <= set(omnisys_ui.__all__)
    for name in expected:
        assert callable(getattr(omnisys_ui, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['ui'].functions)
    assert set(omnisys_ui.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['ui'].functions) == len(omnisys_ui.__all__)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_ui.__all__:
        impl = getattr(omnisys_ui, name)
        assert impl.__module__ == omnisys_ui.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['ui'].functions.items():
        expected = frozenset({'dom'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected
