"""OMNISYS.db — in-memory relational data platform with SQLite persistence.

Portable semantic core: databases and tables with schemas, row
insert/select/update/delete driven by predicate functions, counts and schema
introspection. Mirrors the JS reference lane ``omnisys/db.js`` as locked by the
compiler registry (``OMNISYS_MODULES["db"]``). Real backends (SQLite, Postgres)
are escape hatches behind this same semantic API; the ``database``
capability is declared by the registry, not enforced at runtime here.
"""

from collections.abc import Callable
from typing import Any, TypeAlias, cast

import sqlite3

from omnisys_core import panic

__all__ = [
    'create_db',
    'create_table',
    'insert',
    'select',
    'update',
    'delete',
    'count',
    'drop_table',
    'schema',
    'table_size',
    'db_open',
    'db_query',
    'db_exec',
    'db_close',
]

Database: TypeAlias = dict[str, Any]
Table: TypeAlias = dict[str, Any]
Predicate: TypeAlias = Callable[[dict[str, Any]], bool]

_SQLITE_CONN: sqlite3.Connection | None = None
_SQLITE_IN_MEMORY: bool = False


def create_db(name: str) -> Database:
    """Create a database value named ``name`` with no tables."""
    return {'tag': 'database', 'name': str(name), 'tables': {}}


def create_table(database: Database, name: str, schema: dict[str, Any] | None) -> Table:
    """Create and register a table with ``schema``; panic if it already exists."""
    if database['tables'].get(str(name)):
        panic('db: table already exists: ' + name)
    table: Table = {
        'tag': 'table',
        'name': str(name),
        'schema': schema or {},
        'rows': [],
        'nextId': 1,
    }
    database['tables'][str(name)] = table
    return table


def insert(table: Table, row: dict[str, Any] | None) -> dict[str, Any]:
    """Insert ``row`` with a fresh auto-increment ``id`` and return the stored row."""
    stored = dict(row or {})
    stored['id'] = table['nextId']
    table['nextId'] += 1
    table['rows'].append(stored)
    return stored


def select(table: Table, predicate: Predicate | None) -> list[dict[str, Any]]:
    """Return rows matching ``predicate`` (all rows when it is None)."""
    if predicate is None:
        return cast(list[dict[str, Any]], table['rows'][:])
    return [row for row in table['rows'] if predicate(row)]


def update(table: Table, predicate: Predicate, patch: dict[str, Any] | None) -> int:
    """Merge ``patch`` into every matching row and return the count updated."""
    count = 0
    for row in table['rows']:
        if predicate(row):
            row.update(patch or {})
            count += 1
    return count


def delete(table: Table, predicate: Predicate) -> int:
    """Remove rows matching ``predicate`` and return the count removed."""
    before = len(table['rows'])
    table['rows'] = [row for row in table['rows'] if not predicate(row)]
    return before - len(table['rows'])


def count(table: Table, predicate: Predicate | None) -> int:
    """Count rows matching ``predicate`` (all rows when it is None)."""
    if predicate is None:
        return len(table['rows'])
    return sum(1 for row in table['rows'] if predicate(row))


def drop_table(database: Database, name: str) -> bool:
    """Remove the table ``name``; return False when it does not exist."""
    if not database['tables'].get(str(name)):
        return False
    del database['tables'][str(name)]
    return True


def schema(table: Table) -> dict[str, Any]:
    """Return the schema map the table was created with."""
    return cast(dict[str, Any], table['schema'])


def table_size(table: Table) -> int:
    """Return the number of rows currently stored in ``table``."""
    return len(table['rows'])


def _get_conn() -> sqlite3.Connection:
    """Get the current SQLite connection, raising if none is open."""
    global _SQLITE_CONN
    if _SQLITE_CONN is None:
        raise RuntimeError('No SQLite database open. Call db_open() first.')
    return _SQLITE_CONN


def db_open(path: str | None = None) -> None:
    """Open (or create) a SQLite database at ``path``.

    When ``path`` is ``None`` or ``:memory:``, an in-memory database is used.
    Only one database can be open at a time; opening a new one closes the previous.
    """
    global _SQLITE_CONN, _SQLITE_IN_MEMORY
    db_close()
    if path is None or path == ':memory:':
        _SQLITE_CONN = sqlite3.connect(':memory:')
        _SQLITE_IN_MEMORY = True
    else:
        _SQLITE_CONN = sqlite3.connect(path)
        _SQLITE_IN_MEMORY = False
    _SQLITE_CONN.row_factory = sqlite3.Row
    _SQLITE_CONN.execute('PRAGMA foreign_keys = ON')


def db_query(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT query and return rows as a list of dicts.

    Args:
        sql: SQL query string with ``?`` placeholders.
        params: Optional tuple of parameter values for the placeholders.

    Returns:
        List of row dictionaries (column name -> value).
    """
    conn = _get_conn()
    cursor = conn.execute(sql, params or ())
    return [dict(row) for row in cursor.fetchall()]


def db_exec(sql: str, params: tuple[Any, ...] | None = None) -> int:
    """Execute a DDL/DML statement (CREATE, INSERT, UPDATE, DELETE, etc.).

    Args:
        sql: SQL statement string with ``?`` placeholders.
        params: Optional tuple of parameter values for the placeholders.

    Returns:
        Number of rows affected (for DML) or 0 for DDL.
    """
    conn = _get_conn()
    cursor = conn.execute(sql, params or ())
    conn.commit()
    return cursor.rowcount


def db_close() -> None:
    """Close the currently open SQLite database, if any."""
    global _SQLITE_CONN, _SQLITE_IN_MEMORY
    if _SQLITE_CONN is not None:
        _SQLITE_CONN.close()
        _SQLITE_CONN = None
        _SQLITE_IN_MEMORY = False
