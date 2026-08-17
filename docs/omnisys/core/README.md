# OMNISYS.core

## Purpose

Provides the implicit root namespace exported by `import OMNISYS` (no separate
sub-import required). `core` internally subsumes the §17.7 Phase 1 items
`collections`, `serde`, and `error` as internal submodules — they are NOT
separate top-level OMNISYS imports. This reconciles §17.7's Phase 1 list with
the 18-module documentation count: `core` (containing `collections`, `serde`,
`error`), `async`, `fs`, `test`.

## Public API surface

```omni
import OMNISYS            # brings core into scope

type Result = ok(value) | err(error)
type Option = some(value) | none

fn option(value: any) -> Option
fn ok(value: any) -> Result
fn err(error: Error) -> Result
```

## Dependencies

- None (foundational; loaded by the umbrella `import OMNISYS`)

## Effects/capabilities used

- None

## Status

planned

## Open Questions

- Which prelude symbols are exported at the top level vs. behind `OMNISYS.core`?

<!-- CAPABILITIES: core -->