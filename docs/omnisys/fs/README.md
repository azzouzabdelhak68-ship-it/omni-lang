# OMNISYS.fs

## Purpose

Filesystem access: path handling, file and directory operations, watching,
temporary files, atomic writes.

## Public API surface

```omni
import OMNISYS.fs

fn read(path: Path) -> Result
fn write(path: Path, data: Bytes) -> Result
fn watch(dir: Path) -> Result
```

## Dependencies

- `core`
- `async` (watchers, non-blocking I/O)

## Effects/capabilities used

- `reads filesystem`
- `writes filesystem`

## Status

planned

## Open Questions

- Atomic write semantics on all targets
- Symlink policy

<!-- CAPABILITIES: filesystem -->