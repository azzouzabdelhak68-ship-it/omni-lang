"""Conformance tests: OMNISYS.core must match the compiler registry contract."""

import omnisys_core as core

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_REGISTRY = OMNISYS_MODULES['core'].functions

_ALLOWED_EXTRA = {'PanicError', 'panic', 'VERSION'}


def test_every_registry_function_exists() -> None:
    for name in _REGISTRY:
        assert callable(getattr(core, name, None)), f'core.{name} missing'


def test_no_unexpected_public_functions() -> None:
    expected = set(_REGISTRY) | _ALLOWED_EXTRA
    assert set(core.__all__) == expected


def test_registry_effects_are_none() -> None:
    for name, fn in _REGISTRY.items():
        assert not fn.effects, f'core.{name} unexpectedly declares effects {fn.effects}'
