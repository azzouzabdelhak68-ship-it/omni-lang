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

- `uses network` (distributed mode)

## Status

planned

## Open Questions

- Scheduler model (work-stealing?)
- Cancellation propagation semantics

<!-- CAPABILITIES: async -->