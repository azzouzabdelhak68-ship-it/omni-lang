"""Lock OMNISYS.observability to the compiler registry contract."""

from __future__ import annotations

import omnisys_observability

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset()


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['observability'].functions)
    assert expected <= set(omnisys_observability.__all__)
    for name in expected:
        assert callable(getattr(omnisys_observability, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['observability'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_observability.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['observability'].functions) == len(
        omnisys_observability.__all__
    ) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_observability.__all__:
        impl = getattr(omnisys_observability, name)
        assert impl.__module__ == omnisys_observability.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['observability'].functions.items():
        expected = frozenset() if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_registry_declares_expected_js_deps() -> None:
    assert OMNISYS_MODULES['observability'].js_deps == ('core', 'collections')
