# OMNISYS.ai

## Purpose

AI/ML: tensors, autograd, inference pipelines, tool use.

## Public API surface

```omni
import OMNISYS.ai

fn tensor(shape: List, data: List) -> Tensor
fn autograd(loss: fn) -> Result
fn infer(model: Model, input: Tensor) -> Result
```

## Dependencies

- `core`
- `gpu` (accelerated compute)

## Effects/capabilities used

- `uses GPU`

## Status

planned

## Open Questions

- Model format/interop
- On-device vs. remote inference split

<!-- CAPABILITIES: AI; GPU -->