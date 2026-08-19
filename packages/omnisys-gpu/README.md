# OMNISYS.gpu

Python reference implementation of the OMNISYS `gpu` module: a portable,
data-parallel compute model over explicit buffers, with a deterministic CPU
fallback so programs run and test everywhere.

- **Registry**: `OMNISYS_MODULES["gpu"]` — `compute`, `parallel`, `add`,
  `scale`, `dot`, `matmul`, `normalize`, `device_info` declare the `GPU`
  capability; `buffer` is pure. The `GPU` effect is metadata here: every
  function is a plain synchronous Python function with no hardware access.
- **Import**: `from omnisys_gpu import buffer, compute, ...` — add
  `packages/omnisys-gpu/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Buffer = `{"tag": "gpu.buffer", "data": [...]}` (a copy of
  the input list); `device_info()` = `{"tag": "gpu.device", "name":
  "portable-cpu", "lanes": ["js-fallback"], "cores": 1}`; `compute` and
  `parallel` return plain lists of kernel results.
- **Semantics**: mirrors `omnisys/gpu.js` exactly — `buffer` copies its input,
  `compute` runs `kernel(i, input)` for each `i` in `range(max(0, int(size)))`,
  `parallel` enumerates its input in order, `add`/`dot`/`matmul` panic on
  length/shape mismatch, `normalize` returns a copy of the zero vector, and
  arithmetic returns fresh lists (never aliasing the inputs).

Registry deps are `("core", "graphics")`. This lane imports `omnisys_core`
(for `panic`) only; the `graphics` dependency is documentation — hardware lanes
(WebGPU/CUDA/Metal/Vulkan) are escapes that consume the same kernel model.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.