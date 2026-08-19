"""Lock OMNISYS.platform to the compiler registry contract."""

import omnisys_platform

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()

effect_map: dict[str, frozenset[str]] = {
    'info': frozenset({'process'}),
    'os': frozenset({'process'}),
    'arch': frozenset({'process'}),
    'env': frozenset({'process'}),
    'sleep_ms': frozenset({'process'}),
}


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['platform'].functions)
    assert expected <= set(omnisys_platform.__all__)
    for name in expected:
        assert callable(getattr(omnisys_platform, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['platform'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_platform.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['platform'].functions) == len(omnisys_platform.__all__)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_platform.__all__:
        impl = getattr(omnisys_platform, name)
        assert impl.__module__ == omnisys_platform.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['platform'].functions.items():
        assert fn.effects == effect_map.get(name, frozenset())


def test_registry_declares_core_dependency() -> None:
    assert OMNISYS_MODULES['platform'].js_deps == ('core',)


def test_registry_declares_platform_js_file() -> None:
    assert OMNISYS_MODULES['platform'].js_file == 'omnisys/platform.js'
