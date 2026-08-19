# BENCHMARK_REASONING — Project 3.1 Interactive 2D Vector Drawing Canvas (RUN_001_DEEPSEEK_V4_FLASH_FREE)

Live investigation ledger. Entries appended in chronological order. NOT retroactively edited.

## 2026-08-17 — Entry 0: Initial context

Read (in order):
- `C:\Users\tiamat\AppData\Local\Temp\opencode\V7_PHASE3_REFERENCE.md` (verified ecosystem reference)
- `...\PROJECT_31_GRAPHICS_2D_CANVAS\TASK.md` (task brief)

Key task constraints from TASK.md:
- 2D canvas: shapes (rect/circle/line/polygon), fill/stroke colors, select/move/delete.
- Transforms: position/rotation/scale.
- Animation: continuous updates over time (simulated via tick advancing).
- Verification: `omni check` exit 0, `omni build --target js` runnable artifact, all pytest pass.

Key reference claims (to VERIFY, not assume):
- `OMNISYS.graphics` runtime records draw ops on a canvas; it has NO transform ops.
- No `x[i]` indexing → `omnisys.collections.list_get/list_set`.
- No map literals; no boolean `and`/`or`/`not`; text building only via interpolation.
- `show expr` → `console.log`; Node harness = reference document stub + extracted `<script>`.

## 2026-08-17 — Entry 1: Compiler source inspection

Inspected: `omni_compiler/omnisys_registry.py`, `omnisys/graphics.js`, `omnisys/collections.js`, `omnisys/core.js`, `omni_compiler/emitter.py`.

Verified facts from source:
- Registry (omnisys_registry.py ~275-288): `graphics.canvas`, `clear`, `rect`, `circle`, `line`, `polygon`, `render`, `to_json` all registered PURE (no GPU/network/etc. effects). No `transform`/`rotate`/`scale` ops exist in the graphics module.
- `omnisys/graphics.js` runtime: canvas = `{tag:"graphics.canvas", width, height, ops:[...]}`; each draw op pushes `{op:"rect",...}` records; `render(canvas)` returns the op list; `to_json(canvas)` returns `{tag, width, height, ops}`.
- `omnisys/collections.js`: `list_get(list,i)`, `list_set(list,i,v)` (mutates in place, returns list), `list_push`, `list_remove(list,i)` (splice), `map_get(map,key)`.
- `omnisys/core.js`: `length(list)` only; NO cos/sin/etc.
- `emitter.py` `_js_stmt`: `show` → `console.log(expr)`; for-loop → `for (const v of iterable)`; module-scope `let` for every assigned top-level name.
- Parser: `is`/`is not`/`greater than`/`less than` for comparisons; nested `if/else` required in place of boolean operators.

DECISION: since the graphics runtime has no transforms, every shape is a flat 12-field list
`[kind, x, y, w, h, fill, stroke, rotation, scale, vx, vy, vr]`, and position/rotation/scale
animation is pure list math in source. `Canvas` is the native `omnisys.graphics.canvas` type.

## 2026-08-17 — Entry 2: Probe P1 — graphics + collections basics

Probe `probe_01_basics.omni`:
```
canvas = omnisys.graphics.canvas(800, 600)
canvas = omnisys.graphics.clear(canvas, "#ffffff")
canvas = omnisys.graphics.rect(canvas, 10, 20, 100, 50, "#ff0000")
ops = omnisys.graphics.render(canvas)
count = omnisys.core.length(ops)      # -> probe1 opcount=N
shapes = list_push ... make_shape    # probe2 kind, probe3 count
canvas2 = omnisys.graphics.circle(...); render -> probe4 ops2=N
```
`check` exit 0, `build --target js` exit 0, Node run exit 0. Confirms: canvas op recording,
`render` returns op list, `list_push`/`list_get` round-trip, `omnisys.core.length`.

## 2026-08-17 — Entry 3: Probe P2 — mutation + loops + nested-if dispatch

Probe `probe_02_loops.omni`:
```
fn step(shapes, dt): for s in shapes: list_get vx/vy/vr; list_set x/y/rot += v*dt; end; return shapes
fn classify(shapes, index): kind dispatch via nested if is "rect" -> "rect-hit" / "circle-hit" / "other"
```
`check` exit 0. Node run verified: `after2=...` (x advanced 2 ticks), `classify0=rect-hit`,
`classify1=circle-hit`, `classify2=other`, `count=3`, `nested-if-ok`, `done`.
Confirms: `list_set` mutates a sub-list in place and the mutation is visible through the parent
list (JS reference semantics), `for` loops iterate the shape list, nested `if/else` implements
kind dispatch without boolean operators.

## 2026-08-17 — Entry 4: Design decisions for canvas_app.omni

- Shape model: `[kind, x, y, w, h, fill, stroke, rotation, scale, vx, vy, vr]` (12 fields).
- `add_shape`, `move_shape`, `delete_shape`, `select_shape`, `set_shape_color` — bounds-guarded
  helpers using nested `if` (index >= 0, index < length); `select_shape` returns `0 - 1` for
  invalid index (no unary minus semantics in the grammar, so `0 - 1`).
- `apply_transform` — position/rotation/scale deltas, scale clamped >= 0.1 via nested if.
- `tick(shapes, dt)` — integrates vx/vy/vr per shape per tick (animation).
- `render_scene(shapes, canvas)` — kind dispatch to `graphics.rect/circle/line/polygon`;
  polygon points computed by pure `make_polygon_points` (4 corners).
- App block: build 5 shapes; demo select/move/color/delete/transform/tick; render scene;
  `to_json` readback for width/height via `map_get`. Prints labeled `key=value` lines so the
  Node harness can assert exact values.

## 2026-08-17 — Entry 5: Tests + results

`tests/test_canvas_app.py`:
- Compiler pipeline tests: `omni check` exit 0; js/c/rust builds exit 0 + artifacts exist.
- Runtime tests: build JS, extract `<script>`, run under Node with reference document stub,
  assert labeled lines: `shape_count=5`, `moved_rect=20,25`, `colored_circle=#0000ff`,
  `selected_index=2`, `invalid_selection=-1`, `transformed_rect=25,22,0.5,1.5`,
  `count_after_delete=4`, `tickN_rect=...` progression, `rendered_ops=5`,
  `canvas_width=800`, `canvas_height=600`, `done`.
- ISSUE FOUND + FIXED: the shared `program_output` fixture returned a tuple from a
  subprocess wrapper; pytest raised the tuple-shaped-fixture error. Split into
  `program_stdout` (lines list) + `program_output` (captured raw) fixtures and routed
  each test to the correct one.

FINAL: **14/14 tests pass**, `check` exit 0, all three targets build, Node run exit 0.