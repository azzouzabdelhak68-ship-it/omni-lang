# RESULTS — Project 3.2 Interactive 3D Solar System

- Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
- Model: DEEPSEEK_V4_FLASH_FREE
- Date: 2026-08-17

## Objective

3D solar system in OmniScript: central star + planets, hierarchical moon,
directional light, orbiting camera, body highlight, and tick-advancing orbital
animation. Orbital/hierarchical math must be PURE functions; the `scene:` block
declares the 3D shapes.

## Deliverables

- `source/solar_system.omni` — OmniScript program
- `tests/test_solar_system.py` — pytest suite (15 tests)
- `BENCHMARK_REASONING.md` — investigation ledger (7 entries, incl. probes P1-P3)

## Verification

| Check | Result |
|---|---|
| `omni check` exit code | 0 (OK) |
| `omni build --target js` exit code | 0 (artifact produced) |
| `omni build --target c` exit code | 0 (artifact produced) |
| `omni build --target rust` exit code | 0 (artifact produced) |
| Node runtime run | exit 0, expected stdout |
| pytest | **15/15 passed** |

## Program output (Node run, extracted from built JS artifact)

```
scene-bodies=sun,mercury,venus,earth,moon,mars
scene-lights=1
scene-cameras=1
color:sun=#fbbf24
color:mercury=#9ca3af
...
tick=0 mercury=1.433004733688409,0.4432803099920093
tick=1 mercury=1.4079041001157636,0.5596659040427124
...
tick=0 moon=...
...
highlight earth idx=3
highlight pluto idx=-1
camera-orbit-radius=10
done
```

(Taylor-series orbital math — verified equal to Python `math.cos/sin` reference to
abs < 1e-3 across all bodies and all 5 ticks.)

## Observations

- `import OMNISYS.scene` is STRUCTURALLY IMPOSSIBLE: `scene` is a reserved keyword
  token, and `parse_import` requires IDENTIFIER tokens after `OMNISYS.` (E-SYNTAX-001
  confirmed by probe P1). The registry advertises a `scene` module but the parser can
  never reach it. The built-in `scene:` block is the only 3D surface.
- `pos="{var}"` slots do NOT reach the emitted scene (`position.set` is only emitted
  for literal `pos="x,y,z"`); `color="{var}"` slots DO work. Source therefore uses
  literal positions + literal colors, and motion is demonstrated via app-block output.
- Node harness for scene-bearing programs must AUGMENT the reference document stub with
  `createElement`, `head.appendChild`, `body.appendChild` — otherwise the top-level
  `document.createElement("script")` in emitted scene code crashes. `initScene()` never
  fires under Node (three.onload never runs), so no Three.js API is touched.
- No `cos`/`sin` in `omnisys.core` → Taylor polynomial approximations implemented in
  source (parameters chosen so angles stay small → error < ~5e-6).

## Known limitations

- The JS fallback lane cannot exercise the real Three.js render loop (needs a browser);
  the Node harness validates the program logic and scene-block emission instead.
- Moon hierarchy is pure-math composition (planet position + moon offset), since the
  scene block has no parent/child transform model in the JS fallback.