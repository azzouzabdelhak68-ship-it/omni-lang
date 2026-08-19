# OMNISYS.audio — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/09-media-platform.md` §2. Grounded in the JS reference
`omnisys/audio.js` and the compiler registry `OMNISYS_MODULES["audio"]`.

## 1. Ecosystems studied

- **Web Audio API** — `AudioBuffer` with a sample rate and channel data,
  `OscillatorNode` for synthesis, `GainNode`/`ChannelMergerNode` for mixing,
  `OfflineAudioContext` for rendering to a buffer without a device. Pattern
  kept: a buffer value with samples plus an optional `sampleRate`, sine
  synthesis, gain, and mix as pure transformations.
- **PortAudio** — cross-platform device streaming with blocking and
  callback I/O; the reference for why real capture/playback belongs behind a
  device layer (platform), not in the portable model.
- **SDL_audio** — push/pull audio queues with format negotiation (16-bit PCM
  mono/stereo, sample rates); the 16-bit PCM mono WAV wire format matches the
  portable model's minimum.
- **librosa / soundfile** — Python DSP and codec ecosystems; `soundfile`
  writes WAV headers with the same RIFF/fmt/data layout adopted here, and
  `librosa` consumes plain `float32` sample arrays — both are escapes that
  the pure buffer value can bridge to.

## 2. What was adopted

- One `AudioBuffer` value `{"tag": "audio.buffer", "samples": [...]}` with an
  optional `"sampleRate"` key, set only by `tone`/`silence` (JSON friendly —
  the AI-native mandate).
- `buffer(length)`, `tone(freq, duration, rate)` (rate defaults 44100),
  `silence(duration, rate)`, `sample(buffer, index)`, `mix(a, b)`, `append(a,
  b)`, `gain(buffer, factor)`, `encode_wav(buffer)`, `duration(buffer)`,
  `length(buffer)` — the full registry surface, all pure.
- `Math.round` half-up rounding for `tone`/`silence` lengths (not Python's
  banker's `round`), so lengths match the JS lane exactly.
- `encode_wav` emitting a base64 string: 44-byte RIFF/WAVE header (`fmt ` +
  PCM-1, mono, 16-bit) followed by clamped `[-1, 1]` samples scaled by 32767
  and written as little-endian `int16`.

## 3. Strengths / weaknesses of the studied ecosystems

- Web Audio: powerful node graph and device integration; browser-bound, and
  buffers/channels are tied to a rendering context.
- PortAudio: low-latency cross-platform device I/O; C-style host APIs, no
  portable data value.
- SDL_audio: simple push/pull audio with explicit formats; game-loop bound,
  minimal DSP vocabulary.
- librosa/soundfile: mature codec/DSP workhorses; heavy native dependencies
  and no portable in-memory buffer contract.

OMNISYS keeps the portable *semantic* core only: buffers and pure transforms
on JSON-able values. Node graphs, device streaming, and codec backends are
escapes that consume the same model.

## 4. Performance

- All ops are O(n) in sample count (build, transform, encode); `sample` is
  O(1); `mix`/`append` allocate a new samples list (pure, no mutation).
- `encode_wav` builds one 44 + 2n byte buffer and base64s it once.
- No locks in the single-threaded script model; buffers are plain lists, so
  numpy-style vectorisation is an escape, not a dependency.

## 5. Type-system interaction / portability

- Registry types: `fn(Number) -> AudioBuffer`, `fn(Number, Number, Number) ->
  AudioBuffer`, `fn(AudioBuffer, Number) -> Number`, `fn(AudioBuffer) ->
  Text`, etc. Python typing uses the `AudioBuffer = dict[str, Any]` alias and
  float/int parameters with `rate` defaulting to 44100.
- `sample` requires an integral index (typed `int`); the JS lane's
  fractional-index `undefined` behaviour is not representable.
- `duration` returns a float; `length` returns an int; `encode_wav` returns a
  base64 ASCII `str`.

## 6. Lifecycle / error / concurrency model

- Buffers are immutable-by-convention values; every transform returns a new
  dict and never mutates its inputs (mirrors the JS lane's fresh arrays).
- No function panics and none raises: out-of-range `sample` returns 0,
  negative `buffer` lengths clamp to empty, and missing rates fall back to
  44100. `encode_wav` clamps instead of erroring.
- The only unsupported inputs are NaN rates/samples (documented in §9); the
  pure model never produces them.

## 7. AI usability

- A buffer is plain JSON: an agent can synthesise a tone, mix and append
  buffers, gain-scale, and ask for a base64 WAV — the WAV string is directly
  decodable/playable and verifiable by any host, with no audio device or
  runtime required.

## 8. Interop requirements

- `encode_wav` output is standard 16-bit mono PCM RIFF — playable by Web
  Audio, SDL_audio, PortAudio, and `soundfile` without conversion.
- Future escapes: `record`/`play` map to platform device access
  (`09-media-platform.md` §2) with declared `uses microphone`/`uses audio`
  capabilities; librosa/soundfile and the Web Audio node graph consume the
  same buffer value.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/audio.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `Math.round(x)` for tone/silence lengths | `math.floor(x + 0.5)` | Identical for all doubles: rounds half toward +∞, unlike Python's banker's `round` |
| 2 | `length \| 0` (ToInt32) in `buffer` | `int(length)` | Same truncation toward zero for in-range numbers |
| 3 | `rate \|\| 44100` | `rate or _DEFAULT_RATE` | Same for 0/omitted; NaN stays NaN in Python while JS treats it as falsy — NaN rates unsupported |
| 4 | `(a.samples[i] \|\| 0)` in `mix` | length-guarded adds (`if i < len(...)`) | Same semantics; Python list indexing raises instead of yielding `undefined` |
| 5 | `view.setInt16(44 + i*2, Math.round(clamp(v) * 32767), true)` | `struct.pack('<h', math.floor(clamp(v) * 32767 + 0.5))` | Identical little-endian int16 bytes |
| 6 | `btoa(binary)` / `Buffer.from(...).toString('base64')` | `base64.b64encode(...).decode('ascii')` | Same base64 string |
| 7 | `samples[i]` with fractional `i` returns `undefined` (0 under `\|\|`) | `index` typed `int`; no fractional indexing | Not representable; out of scope for the pure model |
| 8 | NaN sample: `setInt16(NaN)` writes 0 | `min/max` keep NaN → `floor(NaN)` fails | NaN samples are unreachable in the pure model; documented, not handled |
| 9 | Web Audio node graph, PortAudio/SDL device I/O, librosa analysis | not ported | Hardware audio I/O is an escape (`uses audio`/`uses microphone` via platform) |

## 10. Verification

- `python -m pytest packages/omnisys-audio/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-audio/src` **100% branch**.
- `mypy --strict packages/omnisys-audio/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-audio` — clean.
- Registry conformance: `tests/test_conformance.py` locks the 10 functions,
  zero effects, and `js_deps == ('core',)`.