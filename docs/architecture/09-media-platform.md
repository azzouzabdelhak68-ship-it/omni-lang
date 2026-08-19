# OMNISYS Media & Platform Architecture

**Deliverable §14J.** Audio, video, and native platform device access.

Module READMEs: [`../omnisys/audio/README.md`](../omnisys/audio/README.md),
[`../omnisys/video/README.md`](../omnisys/video/README.md),
[`../omnisys/platform/README.md`](../omnisys/platform/README.md).

---

## 1. Scope

| Module | Owns |
|--------|------|
| `audio` | Audio I/O, synthesis, processing |
| `video` | Video decode/encode/streaming, camera buffers |
| `platform` | OS integration, device access (camera, microphone), process |

The separation (spec §17.6.3): a semantic media model, a backend device layer,
and portable escapes for codec/hardware specifics.

## 2. OMNISYS.audio

```omni
import OMNISYS.audio

buf = buffer(44100 * 2)          # seconds of stereo silence
tone(440, 2, 0.5)                # sine at 440 Hz
mixed = mix(buf, tone(330, 1, 0.5))
wav   = encode_wav(mixed)        # → bytes
```

- `buffer`, `tone`, `silence`, `sample`, `mix`, `append`, `gain`,
  `encode_wav`, `duration`, `length`.
- Capture (`record`) and playback (`play`) map to platform device access.

## 3. OMNISYS.video

```omni
import OMNISYS.video

f = frame(1280, 720)
f = set_pixel(f, 100, 100, "#ffffff")
tl = add_frame(timeline(30), f)  # 30 fps
f2 = seek(tl, 1)
```

- `frame`, `set_pixel`, `timeline`, `add_frame`, `seek`, `frame_count`,
  `fps_of`, `metadata`.
- Decode/encode and streaming map to per-backend codec escapes (hardware
  acceleration when available).

## 4. OMNISYS.platform

```omni
import OMNISYS.platform

info()          # OS/arch/env map
now()           # monotonic clock
sleep_ms(50)    # cooperative sleep
capabilities()  # what this target can do
```

- `info`, `os`, `arch`, `env`, `now`, `sleep_ms`, `capabilities` —
  feature detection for capability gating.
- Device access (camera/microphone) lives behind platform, so the same
  semantic call maps to native, browser, and mobile backends.

## 5. Capabilities

- `audio` → `uses audio`, `uses microphone`
- `video` → `uses camera`, `uses video`
- `platform` → `uses platform`, `uses camera`, `uses microphone`, `uses process`

The permission model integrates with the effect system — device access must be
declared at the function boundary (spec §17.4, §17.5).

## 6. Open Design Questions (carried from READMEs)

- Latency budget and sample format standardization
- Codec support matrix and hardware acceleration path
- Feature detection for capability gating