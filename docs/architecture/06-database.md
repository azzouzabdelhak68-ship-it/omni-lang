# OMNISYS.db — Database Architecture

**Deliverable §14G.** The Omni-native data platform.

Module README: [`../omnisys/db/README.md`](../omnisys/db/README.md).

---

## 1. Design Intent

Study SQL, query builders, ORMs, migrations, transactions, connection pools,
prepared statements, relationships, indexes, caching, serialization,
validation, schema management, and introspection (spec §17.6.1) — and design a
platform that serves both **high-level ergonomics AND low-level SQL access**.

Do not assume an ORM is always correct. The platform offers the semantic
layer *and* the raw escape hatch.

## 2. Architecture Layers

```
Semantic data layer (schema, query builder, migrations, transactions)
        │
        ▼
   Execution engine (prepared statements, pooling, caching)
        │
        ▼
   Storage backends: SQL (primary) · in-memory · WASI · browser
```

- The **semantic model** (schema types, query AST, migration plan) is portable.
- The **execution engine** is per-backend, behind a stable interface.
- **Schema** is inspectable: `schema(table) -> Map` round-trips the declared
  shape.

## 3. API Shape

```omni
import OMNISYS.db

db   = create_db("app.db")
tbl  = create_table(db, "items", {id: "Number", name: "Text"})
insert(tbl, {id: 1, name: "bolt"})
rows = select(tbl, (r) -> r["id"] greater than 0)
```

- `create_db`, `create_table`, `drop_table` — lifecycle.
- `insert`, `select`, `update`, `delete`, `count` — data operations; predicates
  are ordinary OmniScript functions (queries are composable, not string-built).
- `schema`, `table_size` — introspection.

## 4. Transactions & Migrations

- Transactions group operations atomically; the platform maps them to the
  backend's native transaction primitives.
- Migrations are versioned plans applied in order, with schema introspection
  for verification.

## 5. Capabilities

- `reads database`
- `writes database`

Both map directly to the §17.5 effect table; `create_db` and every
read/write path declare them.

## 6. Open Design Questions (carried from README)

- ORM escape-hatch boundary (when raw SQL wins over the semantic layer)
- Migration versioning scheme