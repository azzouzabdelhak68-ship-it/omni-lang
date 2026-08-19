# RESULTS — Project 3.4 Integrated ECS Simulation & 3D Scene Coexistence

- Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
- Model: DEEPSEEK_V4_FLASH_FREE
- Date: 2026-08-17

## Objective

Prove ECS simulation and a 3D scene can coexist in ONE OmniScript program:
entities with position/velocity components, a registered motion system, a stepped
simulation, AND a `scene:` block rendering one body per entity — with all three
compiler targets (js/c/rust) building successfully.

## Deliverables

- `source/integrated_sim.omni` — OmniScript program (ECS + scene in one source)
- `tests/test_integrated_sim.py` — pytest suite (10 tests)
- `BENCHMARK_REASONING.md` — investigation ledger (Q1-Q7)
- `CONFORMANCE_RESULTS.md` — conformance / ecosystem findings

## Verification

| Check | Result |
|---|---|
| `omni check` exit code | 0 (OK) |
| `omni build --target js` exit code | 0 (artifact produced) |
| `omni build --target c` exit code | 0 (artifact produced) |
| `omni build --target rust` exit code | 0 (artifact produced) |
| Node runtime run | exit 0, expected stdout |
| pytest | **10/10 passed** |

## Program output (Node run, 3 particles, dt=0.25, 3 steps)

```
tick:0 ...   tick:1 ...   tick:2 ...
final:p1:0.75,0.375
final:p2:-1.8125,1.5625
final:p3:1.625,-0.0625
scene-bodies:3
```

Motion-system update math (position += velocity * dt per step) matches the Python
reference to abs < 1e-9; one scene body is emitted per simulated entity.

## Observations

- Any `import OMNISYS.*` blocks `--target c`/`--target rust` (E-BACKEND-001), so 3.4
  uses the v5.3 flat `sim.*` API with NO imports — `sim.entity/system/run/query` lower
  to Flecs (C) and Bevy (Rust) constructs, and emit verbatim (JS) for a harness to run.
- The JS lane ships NO inlined ECS runtime for `sim.*` (only actor aliases in
  simulation_engine/runtime.js) — the Node harness must define a portable `sim` ECS
  runtime (entity/system/run/query). This is the single most consequential conformance
  finding (see CONFORMANCE_RESULTS.md).
- Scene-bearing JS artifacts need the augmented document stub
  (createElement/head/body.appendChild); `initScene` never fires under Node.
- Per-entity scalar variables are the simulation state model (list-index access via
  `omnisys.collections.*` is unavailable without imports, and imports are blocked).

## Known limitations

- `sim.run`/`sim.query` are lowered to comments in C/Rust main (documented in
  BENCHMARK_REASONING.md Q6); the Flecs/Bevy wiring is emitted as compile-time
  scaffolding only — runtime ECS behavior is proven on the JS lane.
- No shared mutable state between the scene runtime and the sim runtime in the JS
  fallback; consistency is asserted by matching emitted `scene-bodies:N` count to the
  simulated entity count.