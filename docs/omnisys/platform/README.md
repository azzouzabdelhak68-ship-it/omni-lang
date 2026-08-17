# OMNISYS.platform

## Purpose

Native platform APIs: OS integration for Windows, Linux, macOS, and mobile
targets, plus device access (camera, microphone).

## Public API surface

```omni
import OMNISYS.platform

fn os() -> Text
fn clipboard() -> Result
fn camera_device() -> Result
```

## Dependencies

- `core`

## Effects/capabilities used

- `uses camera`
- `uses microphone`
- `uses process`

## Status

planned

## Open Questions

- Feature detection for capability gating
- Permission model integration with effects system

<!-- CAPABILITIES: platform; camera; microphone; process -->