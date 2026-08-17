# OMNISYS.sim

## Purpose

Entity Component System (ECS), physics, and simulation loops.

## Public API surface

```omni
import OMNISYS.sim

type Entity = Int

fn spawn(spec: ComponentSpec) -> Entity
fn query(components: List) -> Result
fn system(fn update: fn(Entity)) -> Result
```

## Dependencies

- `core`
- `async`

## Effects/capabilities used

- `uses GPU` (optional physics)

## Status

planned

## Open Questions

- ECS adapter strategy (Flecs/Bevy/custom)
- Determinism guarantees for simulation

<!-- CAPABILITIES: simulation -->