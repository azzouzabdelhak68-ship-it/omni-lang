# OMNISYS.scene

Python reference implementation of the OMNISYS `scene` module: a pure,
deterministic 3D scene graph. A scene is a plain dict
(`{"tag": "scene", "nodes": {}, "order": [], "nextId": 1}`) holding nodes
(`group`/`mesh`/`camera`/`light`) with transforms (position/rotation/scale),
parent-child edges, an insertion-order `order` list, and a JSON-able
snapshot surface for hardware renderers.

- **Registry**: `OMNISYS_MODULES["scene"]` — all eleven functions declare
  zero effects (`_pure`); the JS lane depends only on `core`. `add` and
  `transform` report unknown parent/node ids via `omnisys.core.panic`
  (`omnisys_core.PanicError` in Python). The effects are metadata only:
  every function is a plain synchronous Python function.
- **Import**: `from omnisys_scene import new_scene, node, mesh, camera,
  light, add, transform, remove, snapshot, update, to_json` — add
  `packages/omnisys-scene/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Scene = `{"tag": "scene", "nodes": {...}, "order": [...],
  "nextId": 1}` (nextId is vestigial but present, as in JS); Node =
  `{"id": ..., "kind": ..., "children": [], "transform": {"position":
  [0,0,0], "rotation": [0,0,0], "scale": [1,1,1]}}`, plus kind fields
  (`geometry` on meshes, `lightType` on lights) and the `_elapsed` clock
  field written by `update`. `snapshot`/`to_json` return a deep copy of
  `{"nodes", "order"}` only — no `tag`, no `nextId` (matches JS
  `JSON.parse(JSON.stringify(...))`).
- **Semantics**: mirrors `omnisys/scene.js` exactly — every mutating op
  returns the same scene value; `node`/`mesh`/`camera`/`light` are
  idempotent creates (`str(id)` key coercion, as JS `String(id)`); `add`
  wires a parent->child edge once (no duplicates), auto-creates the child as
  a `group`, and panics on an unknown parent; `transform` writes only the
  position/rotation/scale keys present (JS truthiness vs Python
  `is not None`, see `RESEARCH.md` §5) and panics on an unknown node;
  `remove` deletes the node and its order entry; `update` increments every
  node's `_elapsed` by `dt` in order.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.