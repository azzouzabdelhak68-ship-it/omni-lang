# OMNISYS.collections

Python reference implementation of the OMNISYS `collections` module:
List / Map / Set / Deque / Heap / RingBuffer operations.

- **Dependency**: requires `omnisys_core` (only for `panic`, matching the JS
  lane which inlines `omnisys/core.js` first).
- **Import**: `from omnisys_collections import list_push, map_set, ...` — add
  `packages/omnisys-collections/src` (and `packages/omnisys-core/src`) to
  `PYTHONPATH`, or rely on the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: List = Python `list`; Map = Python `dict`; Set = Python
  `list` of unique items; Deque = `{"tag": "deque", "items": [...]}`;
  Heap = `{"tag": "heap", "items": [...]}` (min-heap); RingBuffer =
  `{"tag": "ring", "capacity": int, "items": [...]}`.
- **Semantics**: pure operations mirroring `omnisys/collections.js`; mutating
  ops return the same value, non-mutating ops return new values; panic
  conditions raise `omnisys_core.PanicError` with the exact JS messages.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.