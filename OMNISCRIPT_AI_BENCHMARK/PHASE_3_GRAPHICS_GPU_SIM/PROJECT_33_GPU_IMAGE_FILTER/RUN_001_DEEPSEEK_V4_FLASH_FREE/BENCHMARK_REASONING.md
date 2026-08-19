# Benchmark 3.3 — GPU Image Processing Pipeline — Reasoning Ledger

Model: DEEPSEEK_V4_FLASH_FREE
Run dir: RUN_001_DEEPSEEK_V4_FLASH_FREE
Start: 2026-08-17

## Question 1 — How is OMNISYS.gpu registered, and which ops carry the GPU capability?
Hypothesis: `compute`/`parallel`/math ops carry `GPU`; `buffer` may or may not.
Probe: inspected `omni_compiler/omnisys_registry.py` (lines 275-288).
Observed:
- `gpu.buffer` is registered `_pure("fn(List) -> Buffer")` — NO GPU capability.
- `gpu.compute`, `parallel`, `add`, `scale`, `dot`, `matmul`, `normalize`, `device_info` are registered with `"GPU"` effect.
- gpu module js_deps = ("core", "graphics") → importing OMNISYS.gpu also inlines core.js and graphics.js in the JS artifact.
Decision: device-buffer creation is pure; only the dispatch + device-info must be inside `uses GPU` functions. Documented as ecosystem finding (buffer tagged pure).

## Question 2 — What does the JS runtime for omnisys.gpu actually do?
Probe: read `E:\simualtion\omnisys\gpu.js`.
Observed:
- `gpu.buffer(data)` returns `{tag:"gpu.buffer", data:[...].slice()}`.
- `gpu.compute(kernel, input, size)` loops i in 0..size-1 and pushes `kernel(i, input)` into `out`; returns `out`.
- `gpu.device_info()` returns `{tag:"gpu.device", name:"portable-cpu", lanes:["js-fallback"], cores:1}`.
Decision: deterministic CPU-fallback lane. Kernels receive `(i, input)` and must read input via list_get. Input must be a PLAIN list (reference doc verified).

## Question 3 — How do effects get enforced when the app block calls a uses-GPU function?
Probe: read `omni_compiler/checker.py` `_walk_call` / `_enforce`.
Observed:
- `_walk_call` with `app_scope=True`: user function calls do NOT propagate the callee's declared uses; only BUILTIN_CAPABILITIES and omnisys effects propagate. So `when app starts:` can safely call `apply_filter` (declares `uses GPU`).
- Calling `omnisys.gpu.compute` directly in the app block WOULD add `GPU` to actual → E-EFFECT-003. Must wrap.
- `pure` fn calling any gpu.* → E-EFFECT-001.
- `_enforce`: over-declaration (declaring uses GPU without using) is allowed.

## Question 4 — Parser constraints that affect kernel design
Probe: read `omni_compiler/parser.py`, `lexer.py`.
Observed:
- Comparisons: `is`, `is not`, `greater than`, `less than`, `greater or equal`, `less or equal`. NO `and`/`or`/`not`.
- No `%` modulo operator. Arithmetic is `+ - * /` only. `omnisys.core.floor(x)` is available (pure).
- No `x[i]` indexing → `omnisys.collections.list_get(list, i)`.
- Effect clause `uses GPU` parsed as identifiers on the same line (`GPU` is a plain IDENTIFIER token).
Decision: compute per-output column via `col = i - floor(i/w) * w` so left/right bounds guards can be nested `if`s without boolean operators. Row guards: up exists iff `i greater or equal w`; down exists iff `i + 1 + w less or equal n` (n = pixels count).

## Question 5 — Buffer read-back mechanism
Probe: read `omnisys/collections.js` `map_get`.
Observed: `map_get(map, key)` returns `map[String(key)]`. A gpu.buffer value `{tag, data}` is a plain object → `map_get(buf, "data")` yields the pixel array. This is the read-back path. NO `free`/`release` op exists in the registry or runtime → "release" is implicit/GC-managed. Ecosystem finding.

## Decision — Kernel math (kept integer-exact for the chosen dataset)
Input image: 4x4 = 16 pixels, values `10,20,...,160`. w=4 prepended → input list `[4, p0..p15]`.
- blur: `(center + left + right + up + down) / 5`, missing neighbor → replicate center. All sums are multiples of 10 → outputs integers.
- sharpen: `center * 5 - (left + right + up + down)`, missing neighbor → center. Integer.
- edge: `abs(up - down) + abs(left - right)`, missing neighbor → center (diff 0). Integer.
All results deterministic; CPU reference computed in Python uses identical guard logic.

## Decision — Program structure (3-3 required surface)
- `import OMNISYS.gpu` + `OMNISYS.collections` + `OMNISYS.core`.
- Three pure kernels: `blur_kernel`, `sharpen_kernel`, `edge_kernel`.
- `apply_filter(pixels, mode) -> List` with `uses GPU` — dispatch via mode (1/2/3), calls `omnisys.gpu.compute(kernel, data, n)`.
- `transfer_and_readback(pixels) -> List` with `uses GPU` — demonstrates buffer allocate + readback via map_get("data").
- `select_backend(desired: Text) -> Text` — pure backend selector (cuda/metal/vulkan/webgpu → fallback portable-cpu).
- `query_device() -> Text` with `uses GPU` — calls `omnisys.gpu.device_info()`.
- `run_pipeline(pixels, mode, backend) -> List` with `uses GPU` — ties backend selection into the filter dispatch.
- App block: loads image, shows blur/sharpen/edge joined output, readback, device info, backend selections, pipeline output.

## Question 6 — Does `check` accept this before I write tests?
Pending: run `python -m omni_compiler.cli check` on source/gpu_filter.omni once written.
## DISCOVERY (2026-08-17) � Emitter drops parentheses in binary expressions
Built `--target js` to probes/gpu_filter_build.html and READ the emitted JS.
Observed (line ~492): source `return (center + left + right + up + down) / 5`
emitted as `return center + left + right + up + down / 5;` and source
`center * 5 - (left + right + up + down)` emitted as
`center * 5 - left + right + up + down;`. The `_js_expr` BinaryExpr branch
f-strings left and right WITHOUT grouping parens, so source parens are lost
and JS operator precedence wins. This is a compiler bug (wrong semantics for
grouped arithmetic).
Correction: avoid grouped subexpressions; hoist the group into a temporary:
  s = center + left + right + up + down ; return s / 5
  s = left + right + up + down ; return center * 5 - s
Single-identifier operands survive `_js_expr` unchanged. After the fix,
rebuild + node run gave outputs that match the hand-computed CPU reference:
  blur   20,28,38,46,52,60,70,78,92,100,110,118,124,132,142,150
  sharpen -40,-20,-10,10,40,60,70,90,80,100,110,130,160,180,190,210
  edge   50,60,60,50,90,100,100,90,90,100,100,90,50,60,60,50
  readback = original 16 pixels (buffer allocate + map_get("data") round-trip)
  device  backend=portable-cpu cores=1
  select_backend("cuda") -> cuda ; select_backend("directx") -> portable-cpu
  run_pipeline(mode=1) == blur output
Also observed: the app block variable `pixels` is NOT in the emitter's
module-level `let` list (excluded because it is a function parameter name),
so the JS creates an implicit global in sloppy mode � works, but a latent
name-collision hazard worth documenting.
CHECK_EXIT=0, BUILD_EXIT=0 for the fixed source.

## Probe results � effect enforcement boundaries (2026-08-17)
Probe A (probes/probe_pure_buffer.omni): `pure` fn calls omnisys.gpu.buffer
  + omnisys.collections.map_get. `omni check` -> EXIT 0, "OK".
  => CONFIRMS gpu.buffer is registered PURE; a capability gap (device-memory
     transfer requires no GPU declaration). Ecosystem finding.
Probe B (probes/probe_pure_compute.omni): `pure` fn calls omnisys.gpu.compute.
  `omni check` -> EXIT 1, diagnostic E-EFFECT-001
  "Function declared 'pure' but uses ['GPU']".
  => CONFIRMS compute carries the GPU capability and purity is enforced.
