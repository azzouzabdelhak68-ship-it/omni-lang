# OMNISYS.ai — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/ai.js` and the compiler registry `OMNISYS_MODULES["ai"]`.

## 1. Ecosystems studied

- **NumPy / PyTorch** — the reference tensor vocabulary (shape + row-major
  data, matmul, elementwise ops, activations). Kept: shape/data tensor model
  and the same op names.
- **ONNX** — portable model interchange; mirrors the "tensor as data" idea
  (models are data, runnable anywhere).
- **WebNN / TFJS** — the JS acceleration story; the lane these ops target in
  the browser (an escape; this lane is the pure portable core).
- **PyTorch `softmax`** — the stable max-subtracted softmax form adopted
  here.

## 2. What was adopted

- Tensor as a JSON value `{"tag": "tensor", "shape": [...], "data": [...]}`
  (row-major dense, matching the JS lane exactly).
- Elementwise add/scale/relu/sigmoid/sum over flat data; matmul over
  m×k @ k×n with the same panic semantics.
- Panic messages verbatim from the JS lane (`ai.tensor: ...`, 
  `ai.tensor_add: length mismatch`, `ai.tensor_matmul: inner dims mismatch`,
  `ai.linear: input/weights length mismatch`).
- Stable softmax (subtract max before exp); empty input → `[]`.
- `predict` (manual per-layer forward pass over `{weights, bias}` layers).

## 3. Strengths / weaknesses of the studied ecosystems

- NumPy/PyTorch: complete, fast, GPU; dependency-backed (escape for real
  training/inference).
- ONNX: portable; needs a runtime.
- WebNN/TFJS: hardware acceleration; browser-bound.
- Pure tensor core: dependency-free, JSON-friendly, AI-debuggable; slow for
  large tensors (documented).

## 4. Performance

- Elementwise ops are O(n); matmul is O(m·n·k) triple loop; softmax is O(n).
  No vectorization (portability first); documented escape to NumPy/GPU.

## 5. Type-system interaction / portability

- Registry types: `fn(List, List) -> Tensor`, `fn(Tensor, Tensor) -> Tensor`,
  `fn(Tensor, Number) -> Tensor`, `fn(Tensor) -> Number`, `fn(Tensor) -> Map`,
  `fn(fn ...)`. Python uses `Tensor`/`Layer` aliases over `dict[str, Any]`.
- Registry declares `linear` as `fn(List, List, List) -> List`; the JS lane
  returns a scalar Number, so Python returns `float` (deviation #5).

## 6. Lifecycle / error / concurrency model

- All functions are pure; shape/length errors raise `omnisys_core.PanicError`
  with the exact JS message. No shared mutable state, no concurrency concerns.

## 7. AI usability

- Tensors, layers, and predictions are plain JSON — an agent can build a
  tensor, matmul/relu/softmax it, and run inference end-to-end without a
  runtime, and verify results numerically.

## 8. Interop requirements

- Future escapes: NumPy/PyTorch backends, ONNX export, WebNN/GPU — all consume
  the same shape/data tensor model.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/ai.js`) | Python (this package) | Reason |
|---|----------------------|-----------------------|--------|
| 1 | `new Array(sizeOf(shape)).fill(0)` | `[0] * _size_of(shape)` | Same |
| 2 | `Math.max(0, v)` | `max(0.0, v)` | Same |
| 3 | `a.data.reduce(...)` | `sum(a['data'])` then `float()` | Same for numbers |
| 4 | `Math.max.apply(null, values)` on empty → `-Infinity`/NaN | explicit `if not values: return []` | Same observable result (JS returns `[]` too), no NaN |
| 5 | `linear` returns a scalar Number (registry says List) | returns `float` | Matches the JS lane's actual behavior |

## 10. Verification

- `python -m pytest packages/omnisys-ai/tests -q -W error` — all tests pass,
  zero warnings.
- Coverage: `packages/omnisys-ai/src` **100% branch**.
- `mypy --strict packages/omnisys-ai/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-ai` — clean.