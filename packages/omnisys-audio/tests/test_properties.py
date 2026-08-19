"""Property tests for OMNISYS.audio."""

from __future__ import annotations

import base64
import math
import struct

import omnisys_audio as audio
from hypothesis import assume, given, settings
from hypothesis import strategies as st


@st.composite
def buffers(draw: st.DrawFn) -> dict:
    samples = draw(
        st.lists(
            st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
            max_size=40,
        )
    )
    rate = draw(st.one_of(st.none(), st.integers(min_value=1000, max_value=48000)))
    buf: dict = {'tag': 'audio.buffer', 'samples': samples}
    if rate is not None:
        buf['sampleRate'] = rate
    return buf


@given(buffers(), buffers())
def test_append_length_is_sum(a: dict, b: dict) -> None:
    assert audio.length(audio.append(a, b)) == audio.length(a) + audio.length(b)


@given(buffers(), buffers())
def test_mix_samples_are_commutative(a: dict, b: dict) -> None:
    assert audio.mix(a, b)['samples'] == audio.mix(b, a)['samples']


@given(buffers(), buffers())
def test_mix_length_is_max(a: dict, b: dict) -> None:
    assert audio.length(audio.mix(a, b)) == max(audio.length(a), audio.length(b))


@given(buffers())
def test_mix_with_empty_returns_other_samples(a: dict) -> None:
    empty = {'tag': 'audio.buffer', 'samples': []}
    assert audio.mix(empty, a)['samples'] == a['samples']


@given(buffers())
def test_append_with_empty_preserves_samples(a: dict) -> None:
    empty = {'tag': 'audio.buffer', 'samples': []}
    assert audio.append(a, empty)['samples'] == a['samples']


@given(
    buffers(),
    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_gain_scales_each_sample(a: dict, factor: float) -> None:
    out = audio.gain(a, factor)
    for i, s in enumerate(a['samples']):
        assert out['samples'][i] == s * factor


@given(buffers(), st.integers())
def test_sample_out_of_range_returns_zero(a: dict, index: int) -> None:
    assume(index < 0 or index >= audio.length(a))
    assert audio.sample(a, index) == 0


@given(buffers(), st.integers(min_value=0, max_value=50))
def test_sample_in_range_matches_sample(a: dict, index: int) -> None:
    assume(index < audio.length(a))
    assert audio.sample(a, index) == a['samples'][index]


@given(st.floats(min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
def test_buffer_length_clamps_negative(length: float) -> None:
    assert audio.length(audio.buffer(length)) == max(0, int(length))


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=1000), st.integers(min_value=0, max_value=2))
def test_tone_length_is_exact_for_integer_product(freq: int, seconds: int) -> None:
    assert audio.length(audio.tone(freq, seconds, 44100)) == max(1, seconds * 44100)


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=3), st.integers(min_value=1000, max_value=48000))
def test_silence_length_is_exact_for_integer_product(seconds: int, rate: int) -> None:
    assert audio.length(audio.silence(seconds, rate)) == max(1, seconds * rate)


@settings(deadline=None)
@given(
    st.integers(min_value=1, max_value=2000),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=1000, max_value=48000),
)
def test_tone_length_uses_math_round(freq: int, duration: float, rate: int) -> None:
    assert audio.length(audio.tone(freq, duration, rate)) == max(
        1, math.floor(duration * rate + 0.5)
    )


@given(buffers())
def test_duration_is_length_over_rate(a: dict) -> None:
    rate = a.get('sampleRate') or 44100
    assert audio.duration(a) == audio.length(a) / rate


@given(buffers())
def test_encode_wav_decodes_to_valid_wav(a: dict) -> None:
    raw = base64.b64decode(audio.encode_wav(a))
    assert raw[:4] == b'RIFF'
    assert raw[8:12] == b'WAVE'
    assert len(raw) == 44 + 2 * audio.length(a)
    assert struct.unpack('<I', raw[40:44])[0] == 2 * audio.length(a)


@given(buffers())
def test_encode_wav_samples_are_int16_and_clamped(a: dict) -> None:
    raw = base64.b64decode(audio.encode_wav(a))
    values = struct.unpack('<' + 'h' * audio.length(a), raw[44:])
    for i, s in enumerate(a['samples']):
        expected = int(math.floor(max(-1.0, min(1.0, s)) * 32767 + 0.5))
        assert values[i] == expected
