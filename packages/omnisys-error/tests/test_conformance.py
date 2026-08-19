"""Conformance tests: lock the OMNISYS.error registry contract."""

import omnisys_error

from omni_compiler.omnisys_registry import OMNISYS_MODULES

EXPECTED_PUBLIC = {'OmniError'} | set(OMNISYS_MODULES['error'].functions)


def test_registry_names_are_callable() -> None:
    for name in OMNISYS_MODULES['error'].functions:
        assert callable(getattr(omnisys_error, name)), name


def test_no_unexpected_public_functions() -> None:
    for name in omnisys_error.__all__:
        assert callable(getattr(omnisys_error, name)), name
    assert set(omnisys_error.__all__) == EXPECTED_PUBLIC


def test_error_module_depends_on_core() -> None:
    assert OMNISYS_MODULES['error'].js_deps == ('core',)


def test_error_module_functions_are_pure() -> None:
    for name, fn in OMNISYS_MODULES['error'].functions.items():
        if name == 'throw_error':
            assert fn.effects == frozenset({'panic'})
        else:
            assert fn.effects == frozenset()
