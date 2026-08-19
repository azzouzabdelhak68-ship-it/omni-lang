# OMNISYS.db — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/06-database.md`. Grounded in the JS reference
`omnisys/db.js` and the compiler registry `OMNISYS_MODULES["db"]`.

## 1. Ecosystems studied

- **SQLite** — serverless, file-backed relational engine; schemas are
  first-class (`CREATE TABLE`), rows are maps of column → value, primary keys
  are auto-increment integers by convention. Pattern kept: tables own a
  schema map and an auto-increment id counter (`nextId`).
- **PostgreSQL** — richer type system and transactions; the portable subset
  here is table CRUD + predicate-based row selection. Pattern kept: predicate
  functions as the query vocabulary (no SQL strings in the portable core).
- **Query builders / ORMs** — SQLAlchemy, Knex: composition of operations
  over a table value. Pattern kept: `select`/`update`/`delete` take a
  predicate callable and return plain JSON data.

## 2. What was adopted

- One `Database`/`Table` value pair, JSON-friendly (a `database` is a dict of
  tables; a `table` is a dict of schema + rows + counter).
- Predicate-function filtering (`select(table, fn)`), not SQL text — keeps
  the API language-agnostic and effect-checkable at compile time.
- Deterministic auto-increment ids (`id` always wins over a supplied key).
- Mutating ops are in-place on the passed table value (single owner, no
  aliasing surprises for the script model).

## 3. Strengths / weaknesses of the studied ecosystems

- SQLite: maximal portability, minimal semantics; weak concurrent writers.
- Postgres: rich features but heavyweight and host-specific.
- ORMs: ergonomic but leak their host language idioms (Python/JS classes).

OMNISYS keeps the *relational core* only: table CRUD on JSON rows, with real
backends (SQLite, Postgres) as future escapes behind the same API.

## 4. Performance

- In-memory dict/list operations: `select`/`count` are O(n) scans over
  `rows`; `insert`/`table_size` are O(1). No locking needed in the
  single-threaded script model.

## 5. Type-system interaction / portability

- Registry types: `fn(Database, Text, Map) -> Table`, `fn(Table, fn) -> List`,
  etc. Python typing uses `Database`/`Table`/`Predicate` aliases over
  `dict[str, Any]` / `Callable[[dict[str, Any]], bool]`.
- `insert` returns the stored row (with `id`); `select(table, None)` returns
  a shallow copy of the row list (rows stay the same objects, matching JS
  `slice()`).

## 6. Lifecycle / error / concurrency model

- Tables live as long as their parent `Database` value does; `drop_table`
  removes a name and returns `False` when absent.
- Errors: `create_table` on a duplicate name raises `omnisys_core.PanicError`
  with the exact JS message. All other paths return values, never raise.

## 7. AI usability

- Whole data model is JSON: an agent can create a schema, insert rows, and
  inspect counts/schema without any runtime; predicates are the only
  executable surface and are trivially comprehensible.

## 8. Interop requirements

- Future escapes: real SQL engines behind the same table value model
  (`06-database.md` §"backend escapes"); migration/transaction layers are
  Phase-2+ concerns, not part of this portable core.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/db.js`) | Python (this package) | Reason |
|---|----------------------|-----------------------|--------|
| 1 | `String(name)` everywhere | `str(name)` | Same for str/int |
| 2 | `Object.assign({id: nextId++}, row || {})` | `dict(row or {})`, then `stored['id'] = nextId` | Same result: auto id always wins |
| 3 | `table.rows.slice()` (no predicate) | `table['rows'][:]` | Same shallow copy |
| 4 | `typeof predicate === "function"` | `predicate is None` sentinel | Python callable check made explicit via `None` |
| 5 | `update`/`delete` throw if predicate missing | `update`/`delete` require a predicate (typed) | Same observable contract |

## 10. Verification

- `python -m pytest packages/omnisys-db/tests -q -W error` — 29 tests pass,
  zero warnings.
- Coverage: `packages/omnisys-db/src` **100% branch**.
- `mypy --strict packages/omnisys-db/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-db` — clean.