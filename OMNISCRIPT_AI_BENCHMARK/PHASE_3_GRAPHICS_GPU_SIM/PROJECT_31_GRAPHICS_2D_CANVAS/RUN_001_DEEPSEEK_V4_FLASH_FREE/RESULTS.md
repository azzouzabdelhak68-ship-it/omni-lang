# RESULTS — Project 3.1 Interactive 2D Vector Drawing Canvas

- Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
- Model: DEEPSEEK_V4_FLASH_FREE
- Date: 2026-08-17

## Objective

Build an interactive 2D vector drawing canvas in OmniScript: shape model
(rect/circle/line/polygon), fill/stroke colors, select/move/delete, position/
rotation/scale transforms, and tick-based animation. All math is pure functions;
`OMNISYS.graphics` only records draw ops.

## Deliverables

- `source/canvas_app.omni` — OmniScript program (230 lines)
- `tests/test_canvas_app.py` — pytest suite (14 tests)
- `BENCHMARK_REASONING.md` — investigation ledger
- `probe_01_basics.omni`, `probe_02_loops.omni` — verification probes

## Verification

| Check | Result |
|---|---|
| `omni check` exit code | 0 (OK) |
| `omni build --target js` exit code | 0 (artifact produced) |
| `omni build --target c` exit code | 0 (artifact produced) |
| `omni build --target rust` exit code | 0 (artifact produced) |
| Node runtime run | exit 0, expected stdout |
| pytest | **14/14 passed** |

## Program output (Node run, extracted from built JS artifact)

```
shape_count=5
moved_rect=20,25
colored_circle=#0000ff
selected_index=2
invalid_selection=-1
transformed_rect=25,22,0.5,1.5
count_after_delete=4
tick1_rect=25.2,22.1,0.55
tick2_rect=25.4,22.2,0.6
tick3_rect=25.6,22.3,0.65
rendered_ops=5
canvas_width=800
canvas_height=600
done
```

## Observations

- `OMNISYS.graphics` has NO transform ops — all rotation/scale/animation math lives in
  pure OmniScript list functions (documented in BENCHMARK_REASONING.md).
- `list_set` mutates sub-lists in place (JS reference semantics) and mutation is visible
  through the parent list.
- Invalid selection returns `0 - 1` (no unary-minus token in the grammar).
- `rendered_ops=5` after deleting the 5th shape confirms the op stream tracks the
  live shape list.
- `canvas_width/height` read back through `to_json` + `map_get` (no map literals needed).

## Known limitations

- Animation is simulated by explicitly advancing ticks (no frame callback in the
  JS fallback lane); the runtime `requestAnimationFrame` path only exists behind the
  browser `initScene`/`onload` path, which Node harnesses cannot reach.