# OMNISYS.sim — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/10-sim.md`. Grounded in the JS reference `omnisys/sim.js`
and the compiler registry `OMNISYS_MODULES["sim"]`.

## 1. Ecosystems studied

- **Unity DOTS / ECS** — entities as index-like handles, components as plain
  data, systems iterating over matching entities per frame/step. Pattern
  kept: a world value with entities (component maps) and an ordered system
  chain stepped deterministically.
- **Flecs** (also adopted for the v3.1 C lane) — an entity/component/query
  vocabulary with `world` as the root object. Pattern kept: `world()`,
  `component(world, name, key, value)`, `query(world, component)`.
- **Bevy** (v3.2 Rust lane) — `World`/`Query`/`System`/`Schedule`
  terminology. Pattern kept: `system` + `run` as the schedule.
- **This repo's v5.3 `sim.actor` runtime** — the distributed actor model in
  `simulation_engine/runtime.js`; the JS `sim` lane bridges to it when
  running under Node (`sim.actor = createRuntime().sim.actor`).

## 2. What was adopted

- One `World` value `{"tag": "world", "entities", "order", "systems",
  "step"}` (JSON friendly — the AI-native mandate).
- Entities as dicts of component maps; component names `str()`-coerced (JS
  `String(component)`); entity names used raw (JS does not coerce).
- Deterministic stepped `run(world, steps)`: systems run in registration
  order, once per step; `step` counts completed steps.
- Queries by component presence over the insertion order.
- Deep-copied snapshots (JS `JSON.parse(JSON.stringify(...))` → Python
  `copy.deepcopy`) exporting the state only (no system chain).

## 3. Strengths / weaknesses of the studied ecosystems

- Unity DOTS: high performance, archetype-based; engine-bound, C#-only.
- Flecs: portable C, tiny; C-centric ergonomics for scripting.
- Bevy: expressive Rust ECS; compile-time heavy, Rust-only.
- sim.actor (v5.3): distributed actors, deterministic chaos testing; Node
  runtime-bound.

OMNISYS keeps the portable *semantic* core only: entity/component/query on a
JSON world value. Flecs/Bevy backends and the distributed actor bridge are
escapes that consume the same model.

## 4. Performance

- Entity/component ops are O(1) dict lookups; `run` is O(steps × systems)
  plus system cost; `query`/`entities` are O(n) scans; `snapshot` is an O(n)
  deep copy. No locking in the single-threaded script model.

## 5. Type-system interaction / portability

- Registry types: `fn() -> World`, `fn(World, Text, Text, any) -> World`,
  `fn(World, Text, Text) -> any`, `fn(World, Text) -> List`, etc. Python
  typing uses `World`/`Entity`/`SystemFn` aliases over `dict[str, Any]` /
  `Callable[[World], Any]`.
- `get` returns `None` when the entity lacks the component (JS returns
  `undefined`).

## 6. Lifecycle / error / concurrency model

- Worlds are mutable values; entities are owned by the world map. `run` is
  the only stepping function and is idempotent-free (each call advances).
- Errors: `get` on an unknown entity raises `omnisys_core.PanicError` with
  the exact JS message. No other paths raise.

## 7. AI usability

- The whole world is JSON: an agent can spawn entities, attach components,
  register systems, step, query, and snapshot without any runtime — and the
  snapshot is directly inspectable/verifiable.

## 8. Interop requirements

- Future escapes: Flecs/Bevy adapters (`10-sim.md` §"backends as escapes")
  consume the same entity/component model; the distributed `sim.actor`
  bridge is documented as Node-only and not ported to Python (registry
  surface has no `actor` symbol).

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/sim.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `JSON.parse(JSON.stringify(...))` deep copy | `copy.deepcopy` | Same result for JSON-able values |
| 2 | `steps \| 0` + `Math.max(0, ...)` | `max(0, int(steps))` | Same for ints; `int` truncates like `| 0` |
| 3 | `hasOwnProperty(entity.components, String(component))` | `str(component) in entity['components']` | Same |
| 4 | `delete world.entities[name]` (unconditional) | `pop(name, None)` | Tolerates unknown names; documented |
| 5 | `sim.actor` Node bridge (v5.3 runtime) | not ported | Node-only escape; registry has no `actor` symbol |
| 6 | `world.order.filter(...)` | list comprehension | Same |

## 10. Verification

- `python -m pytest packages/omnisys-sim/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-sim/src` **100% branch**.
- `mypy --strict packages/omnisys-sim/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-sim` — clean.