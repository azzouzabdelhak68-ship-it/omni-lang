# BENCHMARK_REASONING — Task 3.4 Integrated ECS Simulation & 3D Scene Coexistence

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE` — observable investigation ledger (not polished).

## 2026-08-17 Session

### Q1. What is the exact compiler invocation & target surface?
Verified from `V7_PHASE3_REFERENCE.md` and `omni_compiler/cli.py`:
- `python -m omni_compiler.cli check <file.omni>` -> exit 0 on success.
- `python -m omni_compiler.cli build <file.omni> --target {js,c,rust} -o <artifact>`.
- Node v24.17.0, Python 3.11.9 confirmed on PATH from E:\simualtion.

### Q2. Can the primary source import OMNISYS modules and still build all three targets?
NO — VERIFIED in reference (E-BACKEND-001): any `import OMNISYS.*` blocks `--target c` and `--target rust`.
Task requires ALL THREE targets to build. Decision: NO imports at all; use the v5.3 flat
`sim.*` standard library. This also means `omnisys.collections.list_get`/`list_set` are
UNAVAILABLE (they require `import OMNISYS.collections`). So list-index-based state access
is also ruled out. Per-entity scalar variables chosen as the simulation state model.

### Q3. What does the JS emitter do with `sim.*` calls?
Inspected `omni_compiler/emitter.py`. `sim.entity(...)`/`sim.system(...)`/`sim.run(...)`/
`sim.query(...)` are ordinary function-call expressions/stmts in MIR; the JS emitter emits
them verbatim as `sim.entity(...)` etc. (`_js_stmt` op=="call" -> `name(...);`). So a Node
harness must define a global `sim` object providing `entity`, `system`, `run`, `query`,
`for_each`. VERIFIED: `simulation_engine/runtime.js` only provides ACTOR aliases
(cluster/node/spawn/send/run/partition/heal/fail/members) — no ECS `sim.entity/system/run/query`.
So the harness MUST supply its own ECS `sim` runtime. Confirmed by reading runtime.js header.

### Q4. What does the scene: block emit in JS, and what stubs does Node need?
Inspected `_js_scene` (emitter.py:184-278). Emits at script top-level:
```
const three = document.createElement("script");
three.src = ".../three.min.js";
three.onload = function() { initScene(); };
document.head.appendChild(three);
```
`initScene()` (which uses THREE / window / requestAnimationFrame) is ONLY invoked via
`three.onload`, which never fires under `node`. So the document stub MUST add
`createElement`, `head.appendChild`, and `body.appendChild` (renderer only runs inside
initScene, but stub body too for safety). The reference recipe's 2-field stub
(`getElementById`, `querySelectorAll`) is INSUFFICIENT for a program that has a `scene:` block.
This is a new discovery to record in CONFORMANCE_RESULTS.

### Q5. Can a `sim.system`-registered function read/mutate app-block or top-level variables?
Checker `analyze()` order (checker.py:144-176): functions are analyzed (line 166) BEFORE
top-level `prog.statements` (line 170); `analyze_app_block` pushes/pops its own scope so
app-block symbols are NOT visible to functions. `check_identifier` (line 423-446) raises
`NameError` for any identifier not in the symbol table, functions, or `sim.*`.
HYPOTHESIS: a function body referencing `x1`/`vx1` declared only in `when app starts:`
will fail `omni check` with NameError. NEEDS PROBE (probe_01). If confirmed, the motion
system must not reference app-block scalars directly.

### Q6. What signature does `sim.system` need for the C/Flecs emitter to accept it?
Inspected `c_emitter._emit_sim_lowering` (c_emitter.py:347-428):
- `sim.system` requires `len(args) >= 3`: args[0] = system-name Text literal,
  args[1] = function ident, args[2] = list of components. Emits `ECS_SYSTEM(world, fn, ...)`
  under `#ifdef OMNI_HAVE_FLECS` and a plain `fn();` call in the `#else` fallback.
- `sim.entity` requires `len(args) >= 2`: args[0] = name Text, args[1] = list of components.
  Components resolve via `_component_name` (struct construct or ident of a struct var, else
  skipped). A list of Text names like `["position", "velocity", "render"]` is ACCEPTED and
  simply skipped (no struct construct) — but still satisfies the arity requirement.
- `sim.run` / `sim.query` are SKIPPED in C main (line 522-524) — lowered to comments/omitted.
CONCLUSION: call `sim.system("motion", motion_system, ["position", "velocity"])` and
`sim.entity("particle1", ["position", "velocity", "render"])`.

### Q7. Rust emitter handling of sim.*
Inspected `rust_emitter.py` lines 82, 109-119: `sim.entity`/`sim.system`/`sim.for_each` lower
to Bevy comments. `sim.run`/`sim.query` handled similarly (generic). Unknown sim.* names
fall through to a generic comment lowering. No imports needed. Build must exit 0.
```
```