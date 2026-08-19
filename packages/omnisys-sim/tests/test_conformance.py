"""Lock OMNISYS.sim to the compiler registry contract."""

import omnisys_sim

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset()


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['sim'].functions)
    assert expected <= set(omnisys_sim.__all__)
    for name in expected:
        assert callable(getattr(omnisys_sim, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['sim'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_sim.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['sim'].functions) == len(omnisys_sim.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_sim.__all__:
        impl = getattr(omnisys_sim, name)
        assert impl.__module__ == omnisys_sim.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['sim'].functions.items():
        expected = frozenset() if name in _IMPURE else frozenset()
        assert fn.effects == expected
