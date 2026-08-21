import omnisys_serde

from omni_compiler.omnisys_registry import OMNISYS_MODULES


def test_registry_functions_are_callable_public_attributes() -> None:
    for name in OMNISYS_MODULES['serde'].functions:
        assert callable(getattr(omnisys_serde, name))


def test_registry_functions_are_pure() -> None:
    for name, function in OMNISYS_MODULES['serde'].functions.items():
        if name in {'json_decode', 'base64_decode'}:
            assert function.effects == frozenset({'panic'})
        else:
            assert function.effects == frozenset()


def test_no_unexpected_public_callables() -> None:
    declared = set(OMNISYS_MODULES['serde'].functions)
    public_callables = {
        name
        for name in vars(omnisys_serde)
        if not name.startswith('_')
        and callable(getattr(omnisys_serde, name))
        and getattr(omnisys_serde, name).__module__ == omnisys_serde.__name__
    }
    assert public_callables == declared


def test_all_matches_registry() -> None:
    assert set(omnisys_serde.__all__) == set(OMNISYS_MODULES['serde'].functions)
