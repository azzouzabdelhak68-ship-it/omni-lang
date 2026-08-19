# RESULTS — Project 3.3 GPU Image Processing Pipeline

- Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
- Model: DEEPSEEK_V4_FLASH_FREE
- Date: 2026-08-17

## Objective

GPU image processing pipeline in OmniScript: buffer allocation, blur/sharpen/edge
filter kernels dispatched through `OMNISYS.gpu.compute`, buffer read-back, device
query, and backend selection. GPU-capability boundaries must be respected
(`uses GPU` effect declarations).

## Deliverables

- `source/gpu_filter.omni` — OmniScript program
- `tests/test_gpu_filter.py` — pytest suite (12 tests)
- `BENCHMARK_REASONING.md` — investigation ledger (incl. effect-enforcement probes A/B)
- `probes/` — probe sources (`probe_pure_buffer.omni`, `probe_pure_compute.omni`,
  `gpu_filter_build.html`)

## Verification

| Check | Result |
|---|---|
| `omni check` exit code | 0 (OK) |
| `omni build --target js` exit code | 0 (artifact produced) |
| `omni build --target c` exit code | 0 (artifact produced) |
| `omni build --target rust` exit code | 0 (artifact produced) |
| Node runtime run | exit 0, expected stdout |
| pytest | **12/12 passed** |

## Program output (Node run, 4x4 image, pixels 10..160)

```
blur    20,28,38,46,52,60,70,78,92,100,110,118,124,132,142,150
sharpen -40,-20,-10,10,40,60,70,90,80,100,110,130,160,180,190,210
edge    50,60,60,50,90,100,100,90,90,100,100,90,50,60,60,50
readback = original 16 pixels (buffer allocate + read-back round-trip OK)
device  backend=portable-cpu cores=1
select_backend("cuda") -> cuda ; select_backend("directx") -> portable-cpu
run_pipeline(mode=1) == blur output
```

## Observations

- `gpu.buffer` is registered PURE (no GPU capability) — device-memory transfer needs no
  `uses GPU`; only `gpu.compute`/`gpu.parallel`/math ops carry the GPU capability
  (probe A/B: E-EFFECT-001 enforced on pure fn calling `gpu.compute`).
- The app block CAN call a `uses GPU` function without declaring effects (only
  BUILTIN_CAPABILITIES and omnisys effects propagate from user-function calls).
- `OMNISYS.gpu` js_deps = (core, graphics) → importing it inlines those runtimes.
- **COMPILER BUG FOUND**: `_js_expr` emits binary expressions WITHOUT grouping parens, so
  `(a + b + c) / 5` becomes `a + b + c / 5` (JS precedence wins) and
  `center * 5 - (l + r + u + d)` becomes `center * 5 - l + r + u + d`. Workaround:
  hoist grouped sub-expressions into a temporary before the operator. (Documented as an
  ecosystem finding; this affects the whole v7 Phase 3 cohort.)
- `map_get` on a `gpu.buffer` value yields `{tag, data}` → `map_get(buf, "data")` is the
  read-back path. No `free`/`release` op exists (GC-managed).
- Runtime GPU lane is a deterministic portable-CPU fallback (kernel gets `(i, input)`
  and must read input via `list_get`).

## Known limitations

- Kernel inputs must be plain lists (buffers are convenience wrappers).
- The device is always `portable-cpu` in the JS fallback; real GPU backends are
  selected-but-stubbed.