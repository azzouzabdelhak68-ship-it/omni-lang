"""Unit tests for OMNISYS.db."""

import omnisys_core as core
import omnisys_db as db
import pytest


@pytest.fixture()
def database() -> dict:
    return db.create_db('shop')


@pytest.fixture()
def table(database: dict) -> dict:
    return db.create_table(database, 'items', {'name': 'Text', 'price': 'Number'})


def test_create_db_shape() -> None:
    d = db.create_db('shop')
    assert d == {'tag': 'database', 'name': 'shop', 'tables': {}}


def test_create_db_coerces_name() -> None:
    assert db.create_db(7)['name'] == '7'


def test_create_table_shape(table: dict) -> None:
    assert table['tag'] == 'table'
    assert table['name'] == 'items'
    assert table['schema'] == {'name': 'Text', 'price': 'Number'}
    assert table['rows'] == []
    assert table['nextId'] == 1


def test_create_table_registered_in_database(database: dict, table: dict) -> None:
    assert database['tables']['items'] is table


def test_create_table_empty_schema_defaults(database: dict) -> None:
    t = db.create_table(database, 'empty', None)
    assert t['schema'] == {}


def test_create_table_panics_on_duplicate(database: dict, table: dict) -> None:
    assert table['name'] == 'items'
    with pytest.raises(core.PanicError):
        db.create_table(database, 'items', {})


def test_insert_assigns_auto_increment_ids(table: dict) -> None:
    first = db.insert(table, {'name': 'a'})
    second = db.insert(table, {'name': 'b'})
    assert first['id'] == 1
    assert second['id'] == 2
    assert [row['name'] for row in table['rows']] == ['a', 'b']


def test_insert_auto_id_wins_over_row_id(table: dict) -> None:
    row = db.insert(table, {'id': 99, 'name': 'a'})
    assert row['id'] == 1
    assert table['nextId'] == 2


def test_insert_none_row_becomes_id_only(table: dict) -> None:
    assert db.insert(table, None) == {'id': 1}


def test_select_all_returns_copy_of_rows(table: dict) -> None:
    db.insert(table, {'name': 'a'})
    result = db.select(table, None)
    assert len(result) == 1
    assert result is not table['rows']


def test_select_filters_by_predicate(table: dict) -> None:
    db.insert(table, {'name': 'a', 'n': 1})
    db.insert(table, {'name': 'b', 'n': 2})
    assert [r['name'] for r in db.select(table, lambda r: r['n'] > 1)] == ['b']


def test_update_returns_count_and_mutates_rows(table: dict) -> None:
    db.insert(table, {'name': 'a', 'n': 1})
    db.insert(table, {'name': 'b', 'n': 2})
    db.insert(table, {'name': 'c', 'n': 1})
    count = db.update(table, lambda r: r['n'] == 1, {'n': 9})
    assert count == 2
    assert [r['n'] for r in table['rows']] == [9, 2, 9]


def test_update_no_match_returns_zero(table: dict) -> None:
    db.insert(table, {'name': 'a'})
    assert db.update(table, lambda r: False, {'x': 1}) == 0


def test_update_none_patch_keeps_rows(table: dict) -> None:
    db.insert(table, {'name': 'a'})
    assert db.update(table, lambda r: True, None) == 1
    assert table['rows'][0] == {'name': 'a', 'id': 1}


def test_delete_returns_count_and_removes_rows(table: dict) -> None:
    db.insert(table, {'name': 'a', 'n': 1})
    db.insert(table, {'name': 'b', 'n': 2})
    removed = db.delete(table, lambda r: r['n'] == 1)
    assert removed == 1
    assert [r['name'] for r in table['rows']] == ['b']


def test_delete_no_match_returns_zero(table: dict) -> None:
    db.insert(table, {'name': 'a'})
    assert db.delete(table, lambda r: False) == 0
    assert db.table_size(table) == 1


def test_count_with_and_without_predicate(table: dict) -> None:
    db.insert(table, {'name': 'a', 'n': 1})
    db.insert(table, {'name': 'b', 'n': 2})
    assert db.count(table, None) == 2
    assert db.count(table, lambda r: r['n'] == 1) == 1
    assert db.count(table, lambda r: r['n'] == 9) == 0


def test_drop_table(database: dict, table: dict) -> None:
    assert table['tag'] == 'table'
    assert db.drop_table(database, 'items') is True
    assert 'items' not in database['tables']
    assert db.drop_table(database, 'items') is False


def test_schema_returns_original_map() -> None:
    schema = {'name': 'Text'}
    t = db.create_table(db.create_db('d'), 't', schema)
    assert db.schema(t) is schema


def test_table_size(table: dict) -> None:
    assert db.table_size(table) == 0
    db.insert(table, {})
    assert db.table_size(table) == 1
