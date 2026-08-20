# OMNISYS.platform

## Purpose

Native platform APIs: OS integration for Windows, Linux, macOS, and mobile
targets. Device access (camera, microphone) is surfaced via `capabilities()`.

## Public API surface

```omni
import OMNISYS.platform

fn now() -> Number
fn os() -> Text
fn arch() -> Text
fn env(key: Text, default: Text?) -> Text
fn info() -> Map
fn sleep_ms(ms: Number) -> Number
fn capabilities() -> List
```

## Dependencies

- `core`

## Effects/capabilities used

- `uses process`

## Status

stable

## Open Questions

- Feature detection for capability gating
- Permission model integration with effects system

<!-- CAPABILITIES: platform; process -->