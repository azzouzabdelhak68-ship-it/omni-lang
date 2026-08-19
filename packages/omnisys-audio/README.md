# OMNISYS.audio

Python reference implementation of the OMNISYS `audio` module: a portable
audio model — buffers of samples with an optional sample rate, sine synthesis,
silence, mixing, concatenation, gain, and base64 WAV encoding.

- **Registry**: `OMNISYS_MODULES["audio"]` — 10 pure functions (zero declared
  effects). Hardware audio I/O (Web Audio nodes, PortAudio, SDL_audio,
  librosa/soundfile) is an **escape** and is not ported.
- **Import**: `from omnisys_audio import buffer, tone, silence, sample, mix,
  append, gain, encode_wav, duration, length` — add
  `packages/omnisys-audio/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: AudioBuffer = `{"tag": "audio.buffer", "samples": [...]}`
  plus an optional `"sampleRate"` set by `tone`/`silence`; `encode_wav`
  returns a base64 string wrapping a 44-byte RIFF/WAVE header and mono 16-bit
  PCM sample data.
- **Semantics**: mirrors `omnisys/audio.js` — `buffer` clamps negative
  lengths to empty; `tone(freq, duration, rate)` synthesises `max(1,
  round(duration * rate))` sine samples at rate 44100 by default; `silence`
  is all zeros; `sample` returns 0 out of range; `mix` sums sample-wise over
  the longer buffer (missing samples count as zero) with rate fallback `a or
  b or 44100`; `append` concatenates and keeps `a`'s rate (or 44100); `gain`
  scales every sample and preserves the rate; `duration` is
  `len / (rate or 44100)`; `length` is the sample count; `encode_wav` clamps
  samples to `[-1, 1]`, scales by 32767, and emits a base64 WAV string.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.