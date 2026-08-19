"""Lock OMNISYS.audio to the compiler registry contract."""

import omnisys_audio

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset()


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['audio'].functions)
    assert expected <= set(omnisys_audio.__all__)
    for name in expected:
        assert callable(getattr(omnisys_audio, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['audio'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_audio.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['audio'].functions) == len(omnisys_audio.__all__) - len(
        _ALLOWED_EXTRA
    )


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_audio.__all__:
        impl = getattr(omnisys_audio, name)
        assert impl.__module__ == omnisys_audio.__name__


def test_registry_declares_expected_effects() -> None:
    effect_map: dict[str, frozenset[str]] = {}
    for name, fn in OMNISYS_MODULES['audio'].functions.items():
        assert fn.effects == effect_map.get(name, frozenset())


def test_registry_js_deps() -> None:
    assert OMNISYS_MODULES['audio'].js_deps == ('core',)
