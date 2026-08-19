# OMNISYS.ai

Python reference implementation of the OMNISYS `ai` module: dense tensors,
linear algebra, activations, and inference — a portable tensor core where
tensors are plain JSON values.

- **Registry**: `OMNISYS_MODULES["ai"]` — 15 functions, all pure.
  `js_deps` = `("core",)`.
- **Import**: `from omnisys_ai import tensor, tensor_zeros, tensor_ones,
  tensor_shape, tensor_add, tensor_scale, tensor_matmul, tensor_relu,
  tensor_sigmoid, tensor_sum, tensor_to_json, tensor_from_json, linear,
  softmax, predict` — add `packages/omnisys-ai/src` to `PYTHONPATH`, or rely
  on the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: Tensor = `{"tag": "tensor", "shape": [...], "data": [...]}`
  (row-major dense data). Layer = `{"weights": [[...], ...], "bias": number}`.
- **Semantics**: mirrors `omnisys/ai.js` — `tensor` panics (via
  `omnisys_core.panic`) when data length ≠ shape product; `tensor_add` and
  `linear` panic on length mismatch; `tensor_matmul` panics on inner-dim
  mismatch. `softmax` uses the max-subtracted stable form and returns `[]` for
  empty input. `predict` passes input through each layer's neurons (each
  neuron = a weight row; `bias` defaults to 0).
- **Note**: GPU/WebNN acceleration and autograd are documented escapes; this
  is the portable deterministic core. The registry types `linear` as returning
  a List, but both lanes return a scalar Number (dot product + bias).

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.