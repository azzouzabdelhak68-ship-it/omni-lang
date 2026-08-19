"""Conformance tests: OMNISYS.async must match the compiler registry contract."""

import omnisys_async as omni_async

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_REGISTRY = OMNISYS_MODULES['async'].functions


def test_every_registry_function_exists() -> None:
    for name in _REGISTRY:
        assert callable(getattr(omni_async, name, None)), f'async.{name} missing'


def test_no_unexpected_public_functions() -> None:
    assert set(omni_async.__all__) == set(_REGISTRY)


def test_registry_effects_are_none() -> None:
    for name, fn in _REGISTRY.items():
        assert not fn.effects, f'async.{name} unexpectedly declares effects {fn.effects}'
