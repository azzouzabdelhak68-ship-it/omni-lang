"""Lock OMNISYS.net to the compiler registry contract."""

import omnisys_net

from omni_compiler.omnisys_registry import OMNISYS_MODULES

_REGISTRY = set(OMNISYS_MODULES['net'].functions)
_ALLOWED_EXTRA = set()


def test_every_registry_function_is_exported() -> None:
    assert set(omnisys_net.__all__) >= _REGISTRY
    for name in _REGISTRY:
        assert callable(getattr(omnisys_net, name))


def test_no_unexpected_public_functions() -> None:
    assert set(omnisys_net.__all__) == _REGISTRY | _ALLOWED_EXTRA


def test_registry_function_count() -> None:
    assert len(_REGISTRY) == len(omnisys_net.__all__)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_net.__all__:
        impl = getattr(omnisys_net, name)
        assert impl.__module__ == omnisys_net.__name__


def test_network_effect_marking_matches_registry() -> None:
    transport = {'server', 'start', 'request', 'get', 'post', 'middleware'}
    for name, fn in OMNISYS_MODULES['net'].functions.items():
        assert ('network' in fn.effects) == (name in transport)
