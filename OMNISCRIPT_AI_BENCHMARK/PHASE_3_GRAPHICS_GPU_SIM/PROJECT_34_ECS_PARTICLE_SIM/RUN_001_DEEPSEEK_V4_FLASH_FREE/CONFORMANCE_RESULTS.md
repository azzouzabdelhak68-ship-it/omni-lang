# CONFORMANCE_RESULTS — Project 3.4 Integrated ECS Simulation & 3D Scene Coexistence

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE` — findings verified by probes + compiler source
inspection + pytest. An ecosystem finding is a mismatch between what the platform
advertises/specifies and what the implementation actually does.

## Compiler / language findings

### C-01 — `import OMNISYS.*` blocks C and Rust backends (E-BACKEND-001) — CONFIRMED
Any `import OMNISYS.<module>` in source raises `E-BACKEND-001` for `--target c` and
`--target rust`. Task 3.4 requires ALL THREE targets → a conformant 3.4 program must
use the v5.3 flat `sim.*` API with NO imports. This is a platform constraint, not a
programming choice. (Also pins the whole phase-3 cohort: OMNISYS imports and
multi-target builds are mutually exclusive.)

### C-02 — JS lane has NO inlined ECS runtime for `sim.*` — CONFIRMED
`simulation_engine/runtime.js` exports only ACTOR aliases (cluster/node/spawn/send/run/
partition/heal/fail/members). There is no `sim.entity`/`sim.system`/`sim.run`/`sim.query`.
Consequence: a program that calls `sim.system(...)` compiles and builds, but the built
JS artifact cannot run in a plain browser/Node harness — a global `sim` object must be
provided externally. The platform advertises ECS via the `sim.*` flat API but ships no
JS runtime for it. WORKAROUND: harness-defined portable ECS runtime.

### C-03 — `import OMNISYS.scene` is unreachable — CONFIRMED
`omnisys_registry.py` line ~289 registers a `scene` module, but `scene` is a reserved
keyword token in `lexer.py`, and `parse_import` (parser.py:340-346) consumes only
IDENTIFIER tokens → `import OMNISYS.scene` fails at parse time with E-SYNTAX-001
("Expected IDENTIFIER, got SCENE"). The registry advertises a module the parser can
never import. The built-in `scene:` block is the only 3D surface.

### C-04 — Scene `pos="{var}"` slots are dropped at build time — CONFIRMED
`_js_attr_value(pos)` splits the value on commas at BUILD time; a slot renders to a JS
identifier → split yields length-1 → no `position.set` emitted. Literal `pos="x,y,z"`
works; `color="{var}"` slots DO work (runtime variable reference). Programs must use
literal positions in the scene block.

### C-05 — Emitter drops grouping parentheses in binary expressions — CONFIRMED (bug)
`_js_expr` BinaryExpr branch emits `left <op> right` without grouping parens.
`(a + b + c) / 5` → `a + b + c / 5` and `center * 5 - (l + r + u + d)` →
`center * 5 - l + r + u + d` (JS precedence wins). Source-level grouped arithmetic is
silently mis-compiled for the JS target. WORKAROUND: hoist the group into a temporary
before the operator. (Found in 3.3, applies to all targets that reuse `_js_expr`.)

## Runtime / harness findings

### C-06 — Scene-bearing JS artifacts require an augmented document stub — CONFIRMED
Emitted scene code calls `document.createElement("script")` at top level and appends to
`document.head`. The reference 2-field stub (getElementById/querySelectorAll) CRASHES
after program output. Node harness must add `createElement`, `head.appendChild`,
`body.appendChild`. `initScene()` only runs from `three.onload`, which never fires under
Node — the Three.js render loop is therefore never exercised by the harness.

### C-07 — `gpu.buffer` is registered PURE (no GPU capability) — CONFIRMED (3.3 cohort)
Device-memory "transfer" requires no `uses GPU` declaration, while `gpu.compute` etc.
do. Capability tagging is per-op and asymmetric (transfer is free, dispatch is gated).

## ECS lowering findings

### C-08 — `sim.*` lowerings differ per target — CONFIRMED
- JS: emitted verbatim (`sim.entity(...)` etc.) → needs external runtime (C-02).
- C: `sim.system`/`sim.entity` → `ECS_SYSTEM`/Flecs scaffolding under
  `#ifdef OMNI_HAVE_FLECS`; `sim.run`/`sim.query` are omitted from main.
- Rust: `sim.entity`/`sim.system`/`sim.for_each` → Bevy scaffolding comments.
Conformance: builds exit 0 for all three; runtime ECS behavior is only provable on the
JS lane.

## Updates — v6 Phase 7 resolutions (2026-08-18)

The findings above were recorded against the compiler as of the 3.4 run. The v6
Phase 7 (Emitter Correctness & Codegen) session closed several of them:

- **C-04 (pos slots dropped at build)** — FIXED. `_js_scene_pos_set` keeps
  slot-valued `pos` as a runtime expression (comma-split at runtime), so
  `position.set` is emitted for `pos="{var}"` and `camera pos={var}`.
- **C-06 (augmented document stub required)** — FIXED. The scene artifact is now
  self-contained: the Three.js loader is DOM-guarded and auto-inits when `THREE` is
  already present; `renderUI`/`bindClicks` guard missing DOM. The artifact runs under
  the bare 2-field stub.
- **C-08 (sim.* lowerings differ per target)** — RESOLVED for C/Rust. C lowers
  `sim.run` to a world tick loop (`ecs_progress` + fallback systems) and `sim.query`
  to a compilable `OmniList` stub, emitting the full main body in source order; Rust
  emits Bevy scaffolding comments + compilable stubs. No raw `sim.*` identifiers leak
  into native output.
- **E-EFFECT-004 (new, post-run)** — RESOLVED. `integrated_sim.omni`'s
  `motion_system` read module data `dt` without declaring it under the tightened
  checker; the effect clause now declares
  `reads sim dt x1 y1 x2 y2 x3 y3 vx1 vy1 vx2 vy2 vx3 vy3` /
  `writes sim x1 y1 x2 y2 x3 y3`. `omni check` exit 0, builds exit 0 for js|c|rust.

Re-verified 2026-08-18: check exit 0 on all 3 targets; JS artifact ticks 3x under Node
with correct finals + `scene-bodies:3`; benchmark suite 10/10.
