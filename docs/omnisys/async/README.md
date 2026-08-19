# OMNISYS.async

## Purpose

Async/concurrency: Task, Future, Stream, Channel, Select, Timeout. Advanced
mode adds distributed actors, message passing, clustering.

## Public API surface

```omni
import OMNISYS.async

fn spawn(body: fn) -> Task
fn select(channels: List) -> Result
fn timeout(ms: Int, body: fn) -> Result
```

## Dependencies

- `core`

## Effects/capabilities used

- `uses network` (advanced mode — distributed actors/clustering)

## Status

planned

Python reference implementation shipped in `packages/omnisys-async`:

- **Portable core** (`omnisys_async`): `task`, `delay`, `all`, `race`, `any`,
  `timeout`, `channel`, `channel_send`, `channel_recv`, `is_promise` — mirrors
  the registry contract in `omni_compiler/omnisys_registry.py`.
- **Advanced mode** (`omnisys_async.actor`, v6 escape): deterministic
  distributed actors + clustering ported from the JS v5.3 `sim.actor` runtime
  (`simulation_engine/runtime.js`). Not part of the registry surface; exposed
  as an importable submodule. See `packages/omnisys-async/README.md`.

## Open Questions

- Scheduler model (work-stealing?)
- Cancellation propagation semantics
- Stream API (registry has no stream functions yet)

<!-- CAPABILITIES: async -->