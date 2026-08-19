# OMNISYS.sim

Python reference implementation of the OMNISYS `sim` module: a portable
ECS/simulation model — a world value with entities (component maps), an
insertion-ordered system chain, and deterministic stepped runs.

- **Registry**: `OMNISYS_MODULES["sim"]` — 10 pure functions (zero declared
  effects). The JS lane's `sim.actor` distributed bridge (v5.3
  `simulation_engine/runtime.js`) is a **Node-only escape** and is not
  ported.
- **Import**: `from omnisys_sim import world, entity, component, get, system,
  run, query, remove_entity, snapshot, entities` — add
  `packages/omnisys-sim/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: World = `{"tag": "world", "entities": {}, "order": [],
  "systems": [], "step": 0}`; Entity = `{"tag": "entity", "name": ..., "components":
  {}}`; `snapshot` exports `tag`/`step`/`entities`/`order` only (no system
  chain), deep-copied.
- **Semantics**: mirrors `omnisys/sim.js` — `entity` is an idempotent
  create-or-return keyed by the raw name (no `String()` coercion, unlike
  component names which ARE `str()`-coerced); `get` panics on unknown
  entities and returns `None` for missing components; `system` appends in
  registration order; `run` executes every system once per step and
  increments `step`; `query` returns insertion-ordered entity names holding
  the component; `remove_entity` drops the entity and its order entry.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.