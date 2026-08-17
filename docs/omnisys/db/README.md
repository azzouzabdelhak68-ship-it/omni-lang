# OMNISYS.db

## Purpose

Data platform: SQL execution, query builder, migrations, transactions,
connection pooling, relationships, indexes, caching, serialization, and schema
management. Designed for both high-level ergonomics and low-level SQL access.

## Public API surface

```omni
import OMNISYS.db

fn query(sql: Text) -> Result
fn migrate(schema: Text) -> Result
fn transaction(body: fn) -> Result
```

## Dependencies

- `core`
- `async` (pooling, non-blocking I/O)

## Effects/capabilities used

- `reads database`
- `writes database`

## Status

planned

## Open Questions

- ORM escape-hatch boundary
- Migration versioning scheme

<!-- CAPABILITIES: database -->