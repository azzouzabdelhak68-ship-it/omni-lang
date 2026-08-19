"""Lock the OMNISYS.test registry contract to the Python implementation."""

from __future__ import annotations

import omnisys_test

from omni_compiler.omnisys_registry import OMNISYS_MODULES

EXPECTED_TYPES = {
    'assert_true': 'fn(Boolean, Text) -> None',
    'assert_eq': 'fn(any, any) -> None',
    'assert_throws': 'fn(fn) -> Boolean',
    'property': 'fn(fn, Number) -> Boolean',
    'bench': 'fn(fn, Number) -> Number',
    'fail': 'fn(Text) -> None',
}


def test_registry_names_are_callable_attributes() -> None:
    registered = OMNISYS_MODULES['test'].functions
    assert set(registered) == set(omnisys_test.__all__)
    for name in registered:
        assert callable(getattr(omnisys_test, name))


def test_registry_signature_contract() -> None:
    registered = OMNISYS_MODULES['test'].functions
    for name, expected in EXPECTED_TYPES.items():
        assert registered[name].type == expected
