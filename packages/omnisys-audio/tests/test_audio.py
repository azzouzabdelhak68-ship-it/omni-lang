"""Unit tests for OMNISYS.audio."""

from __future__ import annotations

import base64
import math
import struct

import omnisys_audio as audio


def test_buffer_shape() -> None:
    buf = audio.buffer(4)
    assert buf == {'tag': 'audio.buffer', 'samples': [0, 0, 0, 0]}
    assert 'sampleRate' not in buf


def test_buffer_truncates_fractional_length() -> None:
    assert audio.buffer(3.9)['samples'] == [0, 0, 0]


def test_buffer_clamps_negative_length() -> None:
    assert audio.buffer(-5)['samples'] == []


def test_buffer_zero_length() -> None:
    assert audio.buffer(0)['samples'] == []


def test_tone_default_rate_and_length() -> None:
    buf = audio.tone(440.0, 1.0)
    assert buf['sampleRate'] == 44100
    assert len(buf['samples']) == 44100


def test_tone_explicit_rate() -> None:
    buf = audio.tone(440.0, 0.1, 8000)
    assert buf['sampleRate'] == 8000
    assert len(buf['samples']) == 800


def test_tone_rounds_half_up_not_bankers() -> None:
    assert len(audio.tone(440.0, 2.5 / 16384, 16384)['samples']) == 3
    assert len(audio.tone(440.0, 4.5 / 16384, 16384)['samples']) == 5


def test_tone_minimum_one_sample() -> None:
    assert len(audio.tone(440.0, 0.0)['samples']) == 1
    assert len(audio.tone(440.0, -1.0)['samples']) == 1


def test_tone_zero_rate_falls_back_to_default() -> None:
    buf = audio.tone(440.0, 1.0, 0)
    assert buf['sampleRate'] == 44100


def test_tone_sample_values() -> None:
    freq = 440.0
    rate = 8000
    buf = audio.tone(freq, 1.0, rate)
    for i in (0, 1, 100, 2000, len(buf['samples']) - 1):
        assert buf['samples'][i] == math.sin(2 * math.pi * freq * i / rate)
    assert buf['samples'][0] == 0.0


def test_silence_default_rate_and_zeros() -> None:
    buf = audio.silence(0.5)
    assert buf['sampleRate'] == 44100
    assert len(buf['samples']) == 22050
    assert all(s == 0 for s in buf['samples'])


def test_silence_explicit_rate() -> None:
    buf = audio.silence(0.25, 8000)
    assert buf['sampleRate'] == 8000
    assert len(buf['samples']) == 2000


def test_silence_minimum_one_sample() -> None:
    assert len(audio.silence(0.0)['samples']) == 1


def test_silence_zero_rate_falls_back_to_default() -> None:
    assert audio.silence(0.5, 0)['sampleRate'] == 44100


def test_sample_in_range() -> None:
    buf = audio.tone(440.0, 0.1, 8000)
    assert audio.sample(buf, 100) == buf['samples'][100]


def test_sample_negative_index_returns_zero() -> None:
    buf = audio.buffer(4)
    assert audio.sample(buf, -1) == 0
    assert audio.sample(buf, -100) == 0


def test_sample_past_end_returns_zero() -> None:
    buf = audio.buffer(4)
    assert audio.sample(buf, 4) == 0
    assert audio.sample(buf, 100) == 0


def test_mix_equal_lengths_sums_samples() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0, 2.0, 3.0], 'sampleRate': 8000}
    b = {'tag': 'audio.buffer', 'samples': [0.5, 0.5, 0.5], 'sampleRate': 8000}
    out = audio.mix(a, b)
    assert out['samples'] == [1.5, 2.5, 3.5]
    assert out['sampleRate'] == 8000
    assert out['tag'] == 'audio.buffer'


def test_mix_a_shorter_than_b() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0, 2.0]}
    b = {'tag': 'audio.buffer', 'samples': [0.5, 0.5, 0.5, 0.5]}
    assert audio.mix(a, b)['samples'] == [1.5, 2.5, 0.5, 0.5]


def test_mix_b_shorter_than_a() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0, 2.0, 3.0, 4.0]}
    b = {'tag': 'audio.buffer', 'samples': [0.5, 0.5]}
    assert audio.mix(a, b)['samples'] == [1.5, 2.5, 3.0, 4.0]


def test_mix_rate_fallbacks() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0]}
    b = {'tag': 'audio.buffer', 'samples': [1.0]}
    assert audio.mix(a, b)['sampleRate'] == 44100
    a_rate = {'tag': 'audio.buffer', 'samples': [1.0], 'sampleRate': 48000}
    b_plain = {'tag': 'audio.buffer', 'samples': [1.0]}
    assert audio.mix(a_rate, b_plain)['sampleRate'] == 48000
    a_plain = {'tag': 'audio.buffer', 'samples': [1.0]}
    b_rate = {'tag': 'audio.buffer', 'samples': [1.0], 'sampleRate': 22050}
    assert audio.mix(a_plain, b_rate)['sampleRate'] == 22050


def test_append_concatenates_and_keeps_a_rate() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0, 2.0], 'sampleRate': 8000}
    b = {'tag': 'audio.buffer', 'samples': [3.0], 'sampleRate': 44100}
    out = audio.append(a, b)
    assert out['samples'] == [1.0, 2.0, 3.0]
    assert out['sampleRate'] == 8000


def test_append_defaults_rate_when_a_has_none() -> None:
    a = {'tag': 'audio.buffer', 'samples': [1.0]}
    b = {'tag': 'audio.buffer', 'samples': [2.0], 'sampleRate': 44100}
    assert audio.append(a, b)['sampleRate'] == 44100


def test_gain_scales_samples_and_preserves_rate() -> None:
    buf = {'tag': 'audio.buffer', 'samples': [1.0, -1.0, 0.5], 'sampleRate': 8000}
    out = audio.gain(buf, 2.0)
    assert out['samples'] == [2.0, -2.0, 1.0]
    assert out['sampleRate'] == 8000


def test_gain_defaults_rate_when_missing() -> None:
    buf = {'tag': 'audio.buffer', 'samples': [1.0, 2.0]}
    assert audio.gain(buf, 3.0)['sampleRate'] == 44100


def test_duration_is_length_over_rate() -> None:
    buf = audio.tone(440.0, 0.5, 8000)
    assert audio.duration(buf) == len(buf['samples']) / 8000
    assert audio.duration(buf) == 0.5


def test_duration_defaults_rate_when_missing() -> None:
    buf = {'tag': 'audio.buffer', 'samples': [0.0, 0.0, 0.0]}
    assert audio.duration(buf) == 3 / 44100


def test_length() -> None:
    assert audio.length(audio.buffer(7)) == 7
    assert audio.length(audio.silence(0.5, 8000)) == 4000
    assert audio.length({'tag': 'audio.buffer', 'samples': []}) == 0


def test_encode_wav_decodes_and_has_valid_magic() -> None:
    buf = audio.tone(440.0, 0.1, 8000)
    raw = base64.b64decode(audio.encode_wav(buf))
    assert raw[:4] == b'RIFF'
    assert raw[8:12] == b'WAVE'
    assert raw[12:16] == b'fmt '
    assert raw[36:40] == b'data'
    assert len(raw) == 44 + 2 * len(buf['samples'])


def test_encode_wav_header_fields() -> None:
    buf = audio.tone(440.0, 0.1, 8000)
    raw = base64.b64decode(audio.encode_wav(buf))
    fields = struct.unpack('<4sI4s4sIHHIIHH4sI', raw[:44])
    (
        riff,
        riff_size,
        wave,
        fmt,
        fmt_size,
        audio_format,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        data,
        data_size,
    ) = fields
    assert riff == b'RIFF'
    assert wave == b'WAVE'
    assert fmt == b'fmt '
    assert data == b'data'
    assert data_size == len(buf['samples']) * 2
    assert riff_size == 36 + data_size
    assert fmt_size == 16
    assert audio_format == 1
    assert channels == 1
    assert sample_rate == 8000
    assert byte_rate == 8000 * 2
    assert block_align == 2
    assert bits == 16


def test_encode_wav_default_rate_when_missing() -> None:
    buf = audio.buffer(10)
    raw = base64.b64decode(audio.encode_wav(buf))
    assert struct.unpack('<I', raw[24:28])[0] == 44100


def test_encode_wav_clamps_and_scales() -> None:
    buf = {'tag': 'audio.buffer', 'samples': [2.0, -2.0, 0.5, -0.5], 'sampleRate': 8000}
    raw = base64.b64decode(audio.encode_wav(buf))
    body = struct.unpack('<' + 'h' * 4, raw[44:])
    assert body == (32767, -32767, 16384, -16383)


def test_encode_wav_empty_buffer() -> None:
    raw = base64.b64decode(audio.encode_wav(audio.buffer(0)))
    assert len(raw) == 44
    assert struct.unpack('<I', raw[4:8])[0] == 36
    assert struct.unpack('<I', raw[40:44])[0] == 0
