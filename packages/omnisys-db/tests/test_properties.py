"""Property-based tests for OMNISYS.db."""

import omnisys_db as db
from hypothesis import given, settings
from hypothesis import strategies as st


@given(st.lists(st.text(), max_size=20))
def test_insert_table_size_and_unique_ids(names: list[str]) -> None:
    database = db.create_db('d')
    table = db.create_table(database, 't', {})
    for name in names:
        db.insert(table, {'name': name})
    assert db.table_size(table) == len(names)
    ids = [row['id'] for row in db.select(table, None)]
    assert ids == list(range(1, len(names) + 1))


@given(st.lists(st.integers(), max_size=20))
def test_count_matches_inserts(values: list[int]) -> None:
    database = db.create_db('d')
    table = db.create_table(database, 't', {})
    for value in values:
        db.insert(table, {'v': value})
    assert db.count(table, None) == len(values)


@given(st.lists(st.booleans(), max_size=20))
def test_delete_preserves_matching_rows(flags: list[bool]) -> None:
    database = db.create_db('d')
    table = db.create_table(database, 't', {})
    for flag in flags:
        db.insert(table, {'flag': flag})
    removed = db.delete(table, lambda r: r['flag'] is True)
    assert removed == sum(1 for f in flags if f)
    assert db.table_size(table) == sum(1 for f in flags if not f)


@settings(max_examples=50)
@given(st.lists(st.integers(min_value=-10, max_value=10), max_size=20))
def test_update_only_touches_matching_rows(values: list[int]) -> None:
    database = db.create_db('d')
    table = db.create_table(database, 't', {})
    for value in values:
        db.insert(table, {'v': value})
    updated = db.update(table, lambda r: r['v'] < 0, {'sign': 'neg'})
    assert updated == sum(1 for v in values if v < 0)
    for row in db.select(table, None):
        if row['v'] < 0:
            assert row['sign'] == 'neg'
        else:
            assert 'sign' not in row
