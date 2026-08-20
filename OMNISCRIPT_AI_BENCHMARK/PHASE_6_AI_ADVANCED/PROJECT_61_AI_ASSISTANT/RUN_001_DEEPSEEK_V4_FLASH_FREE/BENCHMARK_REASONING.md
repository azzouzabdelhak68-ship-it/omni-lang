# BENCHMARK REASONING LEDGER — Phase 6 Project 6.1: Local AI Inference Assistant

Model: deepseek-v4-flash-free (opencode). Run dir: `RUN_001_DEEPSEEK_V4_FLASH_FREE`.

## Initial Investigation (2026-08-19)

### Mission contract
Read `PROJECT_61_AI_ASSISTANT/TASK.md`. STATUS is `BLOCKED` with "Missing: `OMNISYS.ai` — tensors, autograd, inference, tool use, structured outputs, model interaction." However, I verified in `omni_compiler/omnisys_registry.py` (lines 448-467) that the `ai` module IS registered with:
- `tensor`, `tensor_zeros`, `tensor_ones`, `tensor_shape` (all pure)
- `tensor_add`, `tensor_scale`, `tensor_matmul`, `tensor_relu`, `tensor_sigmoid`, `tensor_sum` (all pure)
- `tensor_to_json`, `tensor_from_json` (pure)
- `linear`, `softmax`, `predict` (pure)

And `omnisys/ai.js` implements all of these. So the TASK.md "BLOCKED" status is stale — the registry is the single source of truth the compiler uses.

### Questions being investigated
1. Is `OMNISYS.ai` fully usable through `omni check`? (arity + pure enforcement since all functions are pure).
2. How does `tensor_matmul` work with 2D tensors? (shape [m,k] x [k,n] -> [m,n]).
3. How does `predict` work with layers structure? (layers = list of {weights: [...], bias: number}).
4. How does `linear` work? (input list, weights list, bias list/number -> sum + bias).
5. Can we chain tensor operations for inference? (tensor creation -> matmul -> activation -> softmax -> predict).
6. How to represent structured outputs with confidence scores?
7. How to implement tool dispatch based on structured output?

### Hypotheses & assumptions
- All `OMNISYS.ai` functions are `pure` (no capability declarations needed).
- `tensor` takes shape list and data list; `tensor_zeros`/`tensor_ones` take shape list.
- `tensor_matmul` expects 2D tensors (matrices); `tensor_add`/`tensor_scale` are elementwise.
- `linear` operates on flat lists (vectors); `predict` takes layers and input list.
- `softmax` takes a list of numbers and returns normalized probabilities.
- We can build a small classifier: input -> linear layer -> relu -> linear layer -> softmax -> argmax -> structured action.
- Structured output can be a map with `action`, `confidence`, `reasoning` fields.

### Files inspected
- `PROJECT_61_AI_ASSISTANT/TASK.md` — mission brief.
- `omni_compiler/omnisys_registry.py` — OMNISYS.ai module registration (lines 448-467).
- `omnisys/ai.js` — runtime implementation of all AI functions.
- `PROJECT_51_CRYPTO_FILE_VAULT/RUN_001_DEEPSEEK_V4_FLASH_FREE/source/file_vault.omni` — reference program structure.
- `PROJECT_51_CRYPTO_FILE_VAULT/RUN_001_DEEPSEEK_V4_FLASH_FREE/tests/test_file_vault.py` — reference test structure.
- `omni_compiler/cli.py` — check/build/verify/inspect semantics.
- `omni_compiler/checker.py` — effect enforcement (pure functions only call pure).
- `omni_compiler/emitter.py` — JS emission for map literals, tensor ops, etc.

### Discovered language rules (so far)
- All `OMNISYS.ai` functions are `pure` — no capability declarations needed.
- Map literals `{k: v}` emit as plain JS objects; read with `m["key"]`.
- Arrays `xs[0]`, `%` modulo, `while`/`for` loops available.
- Structs `type Name = { field: Type }` for type definitions.
- Keywords to avoid: `box`, `end`, `on`, `error`, `try`, `while`, `global`, `result`, `tensor` (avoid as local var name).
- `omnisys.ai.tensor` creates tensor with shape and data; `tensor_zeros`/`tensor_ones` create filled tensors.
- `tensor_matmul` only works on 2D tensors (shape length 2).
- `predict` expects layers as list of maps with `weights` (list of lists) and `bias` (number).
- `linear` is for single neuron: input list, weights list, bias number -> single number.

## Probe 1 — AI tensor basics (`probes/probe_ai.omni`)

Verified all AI operations work:
- `tensor` creation with shape/data, `tensor_shape` returns shape list
- `tensor_zeros`/`tensor_ones` create filled tensors
- `tensor_add` elementwise addition, `tensor_scale` scalar multiplication
- `tensor_matmul` 2D matrix multiply: [2,3] x [3,2] -> [2,2] with correct values
- `tensor_relu`/`tensor_sigmoid` activations work elementwise
- `tensor_sum` reduces tensor to scalar
- `tensor_to_json`/`tensor_from_json` round-trip preserves data exactly
- `linear` computes dot product + bias: [1,2,3] · [0.5,0.5,0.5] + 1 = 4
- `softmax` normalizes to probabilities summing to 1
- `predict` runs multi-layer forward pass: 3->4->2 layers produces 2 outputs

Command + raw output (workdir E:\simualtion):
```
python -m omni_compiler.cli check ...\probes\probe_ai.omni
-> omni check: OK — probe_ai.omni

python -m omni_compiler.cli run ...\probes\probe_ai.omni
-> shape: [2,3]
   zeros shape: [3,4]
   ones shape: [2,2]
   add: {"tag":"tensor","shape":[2,2],"data":[6,8,10,12]}
   scale: {"tag":"tensor","shape":[2,2],"data":[2,4,6,8]}
   matmul: {"tag":"tensor","shape":[2,2],"data":[58,64,139,154]}
   relu: {"tag":"tensor","shape":[2,2],"data":[0,2,0,4]}
   sigmoid: {"tag":"tensor","shape":[2,2],"data":[0.5,0.7310585786300049,0.2689414213699951,0.8807970779778823]}
   sum: 10
   roundtrip: {"tag":"tensor","shape":[2,3],"data":[1,2,3,4,5,6]}
   linear: 4
   softmax: [0.6590011388859679,0.24243297070471392,0.09856589040931818]
   predict: [0.7500000000000001,1.7100000000000002]
```

KEY DISCOVERY: `OMNISYS.ai` is fully functional and all operations are `pure`. No capability declarations needed. The `predict` function enables multi-layer inference directly.

## Probe 2 — Structured output and tool dispatch design

Now I need to design the AI assistant with:
1. A small neural network classifier (e.g., intent classification)
2. Structured output mapping (action + confidence + reasoning)
3. Tool dispatch based on classified intent

Let me design a classifier that takes a feature vector and classifies into intents like:
- `GREETING` -> respond with greeting
- `QUERY_WEATHER` -> call weather tool
- `QUERY_TIME` -> call time tool
- `CALCULATE` -> call calculator tool
- `UNKNOWN` -> fallback

The structured output will be a map: `{action: Text, confidence: Number, reasoning: Text, params: Map}`.