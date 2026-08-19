"""Lock OMNISYS.db to the compiler registry contract."""

import omnisys_db

from omni_compiler.omnisys_registry import OMNISYS_MODULES


def test_every_registry_function_is_exported() -> None:
    expected = set(OMNISYS_MODULES['db'].functions)
    assert expected <= set(omnisys_db.__all__)
    for name in expected:
        assert callable(getattr(omnisys_db, name))


def test_no_unexpected_public_functions() -> None:
    expected = set(OMNISYS_MODULES['db'].functions)
    assert set(omnisys_db.__all__) == expected


def test_registry_function_count() -> None:
    assert len(OMNISYS_MODULES['db'].functions) == len(omnisys_db.__all__)


def test_public_functions_are_implemented_in_module() -> None:
    for name in omnisys_db.__all__:
        impl = getattr(omnisys_db, name)
        assert impl.__module__ == omnisys_db.__name__


def test_registry_declares_database_effect() -> None:
    # Most db functions declare only 'database' effect
    # db_open also needs 'filesystem' for file-based databases
    expected_effects = {
        'create_db': frozenset({'database'}),
        'create_table': frozenset({'database'}),
        'insert': frozenset({'database'}),
        'select': frozenset({'database'}),
        'update': frozenset({'database'}),
        'delete': frozenset({'database'}),
        'count': frozenset({'database'}),
        'drop_table': frozenset({'database'}),
        'schema': frozenset({'database'}),
        'table_size': frozenset({'database'}),
        'db_open': frozenset({'database', 'filesystem'}),
        'db_query': frozenset({'database'}),
        'db_exec': frozenset({'database'}),
        'db_close': frozenset({'database'}),
    }
    for name, fn in OMNISYS_MODULES['db'].functions.items():
        assert fn.effects == expected_effects[name], f'{name}: expected {expected_effects[name]}, got {fn.effects}'
