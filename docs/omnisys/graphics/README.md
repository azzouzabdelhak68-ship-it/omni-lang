# OMNISYS.graphics

## Purpose

Portable rendering abstraction over Vulkan, Metal, DirectX, and WebGPU.
Provides a semantic rendering model separated from platform backends.

## Public API surface

```omni
import OMNISYS.graphics

fn create_pipeline(config: PipelineConfig) -> Result
fn begin_frame() -> Result
fn submit(cmd: CommandBuffer) -> Result
```

## Dependencies

- `core`
- `platform` (backend selection)

## Effects/capabilities used

- `uses GPU`

## Status

planned

## Open Questions

- Semantic rendering model scope
- Backend escape-hatch surface

<!-- CAPABILITIES: GPU -->