# OMNISYS.gpu — Research Gate

Deliverable per `docs/architecture/07-graphics-gpu-scene.md` (portable GPU
core + explicit backend escapes) and `docs/architecture/04-api-design-principles.md`
(§4 capability honesty, §5 portable core + escapes, §7 registry as contract).
Grounded in the JS reference `omnisys/gpu.js` and the compiler registry
`OMNISYS_MODULES["gpu"]` (deps `("core", "graphics")`).

## 1. Ecosystems studied

- **WebGPU / WGSL** — portable device + buffer + compute-shader pipeline.
  `buffer` and `compute(kernel, input, size)` mirror the device/input-buffer
  split; WGSL shaders map to `kernel(i, input)`.
- **CUDA** — host/device split, block/thread indexing; `kernel(i, input)` is a
  flattened single-index invocation over a launch size.
- **Metal compute / Vulkan compute** — dispatch + pipeline objects with
  explicit buffers; confirms the "explicit buffer, indexed kernel, dispatch
  count" shape as the portable common core.
- **Data-parallel model** (map/reduce/scatter) — `compute`/`parallel` are
  maps; `add`/`scale`/`dot`/`matmul`/`normalize` are pure element-wise and
  reduction kernels over list values.
- **GPU.js and WebGL GPGPU fallbacks** — JS kernels compiled to GLSL/WGSL at
  runtime with a CPU fallback when a GPU is unavailable; OMNISYS makes that
  fallback the *default* lane (deterministic, testable).

## 2. What was adopted

- Portable data-parallel kernel model: `kernel(i, input)` + explicit `buffer`,
  with a dispatch count (`compute`) and an enumerated input (`parallel`).
- Deterministic CPU fallback as the default lane (`device_info` reports
  `"portable-cpu"` / `["js-fallback"]`) so programs test identically
  everywhere.
- Hardware lanes (WebGPU/CUDA/Metal/Vulkan) as *escapes* that consume the same
  kernel model — never the default (04-api-design-principles §5).
- The `GPU` capability declared on every compute op (07 §5); it is metadata in
  this Python lane.

## 3. Strengths / weaknesses of the studied ecosystems

- WebGPU: portable and modern; heavy pipeline ceremony and async API.
- CUDA: huge performance headroom; vendor-bound, host/device copies leak.
- Metal/Vulkan: explicit and fast; enormous setup surface per dispatch.
- GPU.js/WebGL: hide the GPU behind a kernel lambda; silently depend on
  browser availability and driver quirks.

OMNISYS keeps only the *semantic* model: an indexed kernel over explicit
buffers plus the pure vector/matrix primitives, running on a deterministic CPU
fallback. Hardware (dispatch, memory, async) stays behind named escapes.

## 4. Performance

- `compute`/`parallel` are O(n) with one call per index.
- `add`/`scale`/`normalize` are O(n); `dot` is O(n); `matmul` is O(m·n·k).
- No allocation beyond the output list(s): inputs are never mutated or copied
  except `buffer` (which copies by contract) and `normalize`'s zero-vector
  copy. Pure Python loops — no NumPy dependency.

## 5. Type-system interaction / portability

- Registry types: `fn(List) -> Buffer`, `fn(fn, List, Number) -> List`,
  `fn(List, Number) -> List`, `fn(List, List) -> Number`, `fn() -> Map`.
- Python typing: `Buffer = dict[str, Any]`; arithmetic lists are
  `list[float]` (ints are valid `float`s); `compute`'s kernel is
  `Callable[[int, object], Any]`, `parallel`'s is `Callable[[int, Any], Any]`.
- The tagged shape `{"tag": "gpu.buffer", "data": [...]}` is the portable
  buffer contract a WebGPU/CUDA/Metal/Vulkan backend would consume.

## 6. Lifecycle / error / concurrency model

- Stateless module: no module-level mutable state (unlike the net/http
  registry hooks); nothing to reset between tests.
- Errors: length/shape mismatches raise `omnisys_core.PanicError` with the
  exact JS messages (`gpu.add: length mismatch`, `gpu.dot: length mismatch`,
  `gpu.matmul: incompatible matrices`).
- Single-threaded and deterministic by default; parallelism is the kernel
  model's *semantics*, not Python threads.

## 7. AI usability

- Pure list-in/list-out kernels: an agent writes `compute`/`parallel` lambdas,
  feeds plain lists, and inspects plain lists — no device, dispatch, or async
  vocabulary to learn. `buffer`/`device_info` give inspectable tagged values.

## 8. Interop requirements

- WebGPU/CUDA/Metal/Vulkan backends consume the same kernel model: a `buffer`
  value maps to a device buffer, `compute` maps to a dispatch with the kernel
  compiled to WGSL/CUDA/MSL/GLSL, and `device_info` reports the active lane.
  Backends only change `device_info`, never the calling convention.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/gpu.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `(data \|\| []).slice()` | `list(data or [])` | Same copy-on-falsy semantics |
| 2 | `size \| 0` | `int(size)` | Same truncation; `int` also types `size` cleanly |
| 3 | `Math.max(0, size)` | `max(0, int(size))` | Identical clamp |
| 4 | `(list \|\| []).map((item, i) => ...)` | `enumerate(list(list_ or []))` | Identical order + index |
| 5 | `Math.sqrt` | `math.sqrt` | Identical |
| 6 | `a.reduce((s, v) => s + v * v, 0)` | explicit `total` loop | Identical float sum order |
| 7 | `.map((v, i) => v + b[i])` / `.map(v => v * factor)` | list comprehensions / `zip` | Identical |
| 8 | panic via `core.panic(...)` | `omnisys_core.panic(...)` raising `PanicError` | Same messages |
| 9 | matmul `a[0].length !== k` guard | `len(a[0]) != len(b)` | Same guard (empty `a` raises `IndexError` in both lanes) |
| 10 | `kernel(i, input)` / `kernel(i, item)` | same `Callable` calls | Identical |

## 10. Verification

- `python -m pytest packages/omnisys-gpu/tests -q -W error` — 30 tests pass,
  zero warnings.
- Coverage: `packages/omnisys-gpu/src` **100% branch** (49 stmts, 18 branches).
- `mypy --strict packages/omnisys-gpu/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-gpu` — clean.