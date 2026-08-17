# OMNISYS.video

## Purpose

Video encoding, decoding, and streaming, including camera buffer handling.

## Public API surface

```omni
import OMNISYS.video

fn decode(stream: Bytes) -> Result
fn encode(frame: Frame, codec: Text) -> Result
```

## Dependencies

- `core`
- `platform`

## Effects/capabilities used

- `uses camera`

## Status

planned

## Open Questions

- Codec support matrix
- Hardware acceleration path

<!-- CAPABILITIES: camera; video -->