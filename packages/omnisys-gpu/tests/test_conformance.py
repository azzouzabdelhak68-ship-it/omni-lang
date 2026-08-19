"""Lock OMNISYS.gpu to the compiler registry contract."""

import omnisys_gpu

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = {'compute', 'parallel', 'add', 'scale', 'dot', 'matmul', 'normalize', 'device_info'}


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['gpu'].functions)
    assert expected <= set(omnisys_gpu.__all__)
    for name in expected:
        assert callable(getattr(omnisys_gpu, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['gpu'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_gpu.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['gpu'].functions) == len(omnisys_gpu.__all__) - len(_ALLOWED_EXTRA)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_gpu.__all__:
        impl = getattr(omnisys_gpu, name)
        assert impl.__module__ == omnisys_gpu.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['gpu'].functions.items():
        expected = frozenset({'GPU'}) if name in _IMPURE else frozenset()
        assert fn.effects == expected
