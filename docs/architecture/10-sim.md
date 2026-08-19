# OMNISYS Simulation / ECS Architecture

**Deliverable §14K.** ECS, physics, and simulation — the Omni semantic model,
portable across runtimes.

Module README: [`../omnisys/sim/README.md`](../omnisys/sim/README.md).
Spec: [`../../OMNI_SPEC.md`](../../OMNI_SPEC.md) §13.5, §17.

---

## 1. The Rule: OmniScript Defines the Model; Runtimes Implement It

OMNISYS is **not** a Flecs frontend nor a Bevy frontend. The Omni semantic
model (entities, components, systems, queries, schedules) is spec-defined and
runtime-agnostic. Concrete ECS runtimes — Flecs (first adapter, C API), Bevy
(future, Rust lane), or a custom runtime — implement the *same* semantics
behind adapters.

No concrete ECS's scheduling, query, borrowing, command-buffer, or world
semantics leak into the spec. If a runtime cannot express the model, the
runtime is at fault.

## 2. Semantic Model Contents (spec §13.5)

- **Entities** — typed, ID-based simulation objects.
- **Components** — typed data attached to entities.
- **Systems** — functions over sets of components, run per schedule step.
- **Queries** — declarative selection of entities by component set.
- **Schedules** — deterministic ordering of systems per frame/tick.
- **Determinism** — fixed, reproducible execution order; no data races; same
  inputs → same state. Guaranteed per fixed backend, not bit-identical across
  backends (float rounding may differ).
- **Parallelism** — systems MAY run in parallel when the model proves they
  cannot conflict; ordering is spec-defined.
- **Data-oriented layouts** — SoA / cache-friendly storage as the first-class
  layout; the runtime chooses physical layout, the spec defines observable
  semantics.

## 3. OMNISYS.sim API

```omni
import OMNISYS.sim

w      = world()
entity(w, "player")
component(w, "player", "Position", {x: 0, y: 0, z: 0})
system(w, move_system)
run(w, 60)               # 60 ticks
pos    = get(w, "player", "Position")
snapshot(w)
```

- `world`, `entity`, `component`, `get`, `system`, `run`, `query`,
  `remove_entity`, `snapshot`, `entities`.
- Systems are **ordinary functions** passed to the API — no new keywords
  (spec §17.2). Access declarations (`reads`/`writes` on components) make
  system access explicit and verifiable (spec §17.5).

## 4. Language-Level `sim.*` and OMNISYS.sim

Two surfaces coexist:

1. The language-level `sim.*` standard library (spec §17) used by game code
   (e.g. `sim.entity(name, [components])`, `sim.for_each(...)`).
2. The OMNISYS.sim module (world/entity/component/system), the platform-native
   expression of the same model.

Both compile through the same MIR; the `omni` API reports against the Omni
semantic model so `inspect`/`trace` understand entities, systems, and queries
as first-class concepts.

## 5. Capabilities

- `sim` → `simulation` (pure model operations)
- optional `uses GPU` for accelerated physics

## 6. Determinism Contract

- Within one tick, systems execute in spec-defined order.
- Two systems that both write the same component MUST NOT run in parallel; the
  compiler rejects the schedule otherwise (spec §17.4).
- Same inputs + same tick count → same state (per fixed backend).

## 7. Open Design Questions (carried from README)

- ECS adapter strategy (Flecs/Bevy/custom) sequencing
- Determinism guarantees across heterogeneous hardware