"""Lock OMNISYS.video to the compiler registry contract."""

import omnisys_video

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_ALLOWED_EXTRA = frozenset()
_IMPURE = frozenset()


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['video'].functions)
    assert expected <= set(omnisys_video.__all__)
    for name in expected:
        assert callable(getattr(omnisys_video, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['video'].functions) | _ALLOWED_EXTRA
    assert set(omnisys_video.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['video'].functions) == len(omnisys_video.__all__) - len(
        _ALLOWED_EXTRA
    )


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_video.__all__:
        impl = getattr(omnisys_video, name)
        assert impl.__module__ == omnisys_video.__name__


def test_registry_declares_expected_effects() -> None:
    for name, fn in OMNISYS_MODULES['video'].functions.items():
        expected = frozenset() if name in _IMPURE else frozenset()
        assert fn.effects == expected


def test_js_deps_are_core_and_audio() -> None:
    assert OMNISYS_MODULES['video'].js_deps == ('core', 'audio')
