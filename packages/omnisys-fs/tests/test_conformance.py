"""Conformance tests: the registry contract locks the public surface."""

import omnisys_fs as fs

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_EXPECTED = set(OMNISYS_MODULES['fs'].functions)
_REGISTRY_COUNT = 14


def test_every_registry_function_is_callable_attribute() -> None:
    for name in _EXPECTED:
        assert callable(getattr(fs, name))


def test_no_unexpected_public_functions() -> None:
    assert set(fs.__all__) == _EXPECTED


def test_function_count_matches_registry() -> None:
    assert len(_EXPECTED) == _REGISTRY_COUNT
