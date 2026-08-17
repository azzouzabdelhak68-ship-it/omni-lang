# OMNISYS.audio

## Purpose

Audio I/O, synthesis, and processing: capture, playback, synthesis graphs,
effects.

## Public API surface

```omni
import OMNISYS.audio

fn play(sample: AudioBuffer) -> Result
fn record(duration: Int) -> Result
```

## Dependencies

- `core`
- `platform` (device access)

## Effects/capabilities used

- `uses audio`
- `uses microphone`

## Status

planned

## Open Questions

- Latency budget
- Sample format standardization

<!-- CAPABILITIES: audio; microphone -->