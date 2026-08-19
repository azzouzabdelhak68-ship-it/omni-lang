# OMNISYS.db

Python reference implementation of the OMNISYS `db` module: an in-memory
relational data platform — databases, tables with schemas, and row
insert/select/update/delete driven by predicate functions.

- **Registry**: `OMNISYS_MODULES["db"]` — 10 functions, all declaring the
  `database` capability (metadata here; every function is a plain synchronous
  Python function).
- **Import**: `from omnisys_db import create_db, create_table, insert,
  select, ...` — add `packages/omnisys-db/src` to `PYTHONPATH`, or rely on
  the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: Database = `{"tag": "database", "name": str, "tables":
  {}}`; Table = `{"tag": "table", "name": str, "schema": {}, "rows": [],
  "nextId": 1}`; rows are plain dicts with an auto-increment `id` that always
  wins over a caller-supplied `id`.
- **Semantics**: mirrors `omnisys/db.js` exactly — `create_table` panics on
  duplicate names; `insert` assigns the next `id`; `select`/`count` take an
  optional predicate (all rows when `None`); `update` merges a patch into
  matching rows and returns the count; `delete` returns the count removed;
  `drop_table` returns `False` when the table is absent.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.