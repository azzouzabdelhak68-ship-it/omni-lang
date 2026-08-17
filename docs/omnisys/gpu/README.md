# OMNISYS.gpu

## Purpose

General-purpose GPU compute: CUDA, Metal, Vulkan, WebGPU. Portable GPU
concepts with backend-specific capabilities explicitly exposed through the
capability system.

## Public API surface

```omni
import OMNISYS.gpu

fn launch(kernel: Kernel, grid: Grid, args: List) -> Result
fn buffer(size: Int) -> Result
```

## Dependencies

- `core`
- `graphics` (shared device/host management)

## Effects/capabilities used

- `uses GPU`

## Status

planned

## Open Questions

- Memory model (unified vs. explicit)
- Kernel compilation pipeline

<!-- CAPABILITIES: GPU -->