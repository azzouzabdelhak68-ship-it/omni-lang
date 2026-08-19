# OMNISYS.scene — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/07-graphics-gpu-scene.md`. Grounded in the JS reference
`omnisys/scene.js` and the compiler registry `OMNISYS_MODULES["scene"]`.

## 1. Ecosystems studied

- **Three.js / Babylon.js** — scene graphs as object hierarchies with
  `scene.add(node)`-style composition, per-node transforms, cameras, lights,
  and meshes. Pattern kept: a `Scene` value owns a node map + an insertion
  order + a `transform` triad.
- **glTF** — a portable, JSON-serializable scene description: nodes with
  names, transform arrays, mesh/geometry references, and a scene-level
  structure. Pattern kept: `snapshot()`/`to_json()` are pure JSON-able scene
  exports a hardware renderer can consume.
- **Unity / game-engine scene graphs** — a flat node registry with
  parent-child edges (not a strict tree); nodes exist independently and are
  linked by `add`. Pattern kept: `add(parent, child)` wires edges once and
  auto-creates missing nodes as groups.

## 2. What was adopted

- One `Scene` value `{"tag": "scene", "nodes", "order", "nextId"}` (JSON
  friendly — the AI-native mandate).
- Node kinds `group`/`mesh`/`camera`/`light` with a single transform triad
  (position/rotation/scale) — matching the module README's `scene:` block
  vocabulary (box/camera/light).
- Idempotent node creation (`node`/`mesh`/`camera`/`light` create-or-return),
  with `str()` key coercion exactly like JS `String(id)`.
- Deep-copy snapshots (JS `JSON.parse(JSON.stringify(...))` → Python
  `copy.deepcopy`), exporting only `nodes` + `order`.
- Deterministic `update(s, dt)` stepping (per-node `_elapsed` clock).

## 3. Strengths / weaknesses of the studied ecosystems

- Three.js: ergonomic object composition; JS-only, imperative mutation.
- glTF: portable + serializable; static, no runtime semantics.
- Unity: rich tooling; heavy, binary, proprietary.

OMNISYS keeps the portable *semantic* layer only: a JSON-able scene value
that any hardware renderer (Vulkan/Metal/DX/WebGPU) can consume as an escape.

## 4. Performance

- Node ops are O(1) dict lookups; `add` dedupes edges in O(children);
  `update` is O(n); `snapshot`/`to_json` are O(n) deep copies. All
  allocations are copies of the output only.

## 5. Type-system interaction / portability

- Registry types: `fn() -> Scene`, `fn(Scene, Text) -> Node`, `fn(Scene,
  Text, Map) -> Scene`, etc. Python typing uses `Scene`/`Node` aliases over
  `dict[str, Any]`.
- `transform` writes only the keys present. JS truthiness
  (`attrs.position`) vs Python `is not None`: an empty array is truthy in JS
  but falsy in Python — the Python lane uses key-presence + `is not None`,
  which is identical for the in-contract `[x,y,z]` arrays.

## 6. Lifecycle / error / concurrency model

- Scenes are mutable values; nodes are owned by their scene map. `remove`
  deletes a node and its order entry.
- Errors: `add` on an unknown parent and `transform` on an unknown node raise
  `omnisys_core.PanicError` with the exact JS messages. No other paths raise.

## 7. AI usability

- The whole scene is a JSON graph: an agent can build nodes, wire edges, set
  transforms, step time, and export a snapshot without any runtime — and
  every function is value-in/value-out over plain dicts.

## 8. Interop requirements

- Future escapes: hardware renderers (Vulkan/Metal/DX/WebGPU) and engine
  adapters (Three.js/glTF) consume the same scene value; `snapshot()` is the
  interop seam (`07-graphics-gpu-scene.md` §"backends as escapes").

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/scene.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `JSON.parse(JSON.stringify(...))` deep copy | `copy.deepcopy` | Same result for JSON-able values |
| 2 | `String(id)` / `String(geometry)` / `String(kind || "directional")` | `str(...)`, `kind or 'directional'` | Same for str/int; None handled identically |
| 3 | `attrs.position` truthiness (arrays always truthy) | key-presence + `is not None` | Same for in-contract `[x,y,z]` arrays |
| 4 | `delete s.nodes[id]` (unconditional) | key-guarded `del` | Tolerates unknown ids; documented |
| 5 | `node._elapsed = (node._elapsed || 0) + dt` | `node_.get('_elapsed', 0) + dt` | Same result |
| 6 | `to_json = snapshot` alias | `to_json` calls `snapshot` | Identical |
| 7 | `s.order.filter(...)` | list comprehension | Same |

## 10. Verification

- `python -m pytest packages/omnisys-scene/tests -q -W error` — 70 tests
  pass, zero warnings.
- Coverage: `packages/omnisys-scene/src` **100% branch**.
- `mypy --strict packages/omnisys-scene/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-scene` — clean.