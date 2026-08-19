"""OMNISYS.audio — a portable audio model: buffers, synthesis, mixing, WAV encoding.

Python reference implementation of the OMNISYS ``audio`` module (v6): an audio
buffer is a plain dict of samples plus an optional ``sampleRate`` key; ``tone``
and ``silence`` synthesise, ``mix``/``append``/``gain`` transform, and
``encode_wav`` emits a base64 16-bit mono PCM WAV string. Mirrors the JS
reference lane ``omnisys/audio.js`` and satisfies the registry contract
(``OMNISYS_MODULES["audio"]``): all ten functions are pure (zero declared
effects) and depend on ``omnisys_core`` per the registry. Hardware audio I/O
(Web Audio nodes, PortAudio, SDL_audio) is an escape and is not ported.
"""

import base64
import math
import struct
from typing import Any, TypeAlias, cast

__all__ = [
    'buffer',
    'tone',
    'silence',
    'sample',
    'mix',
    'append',
    'gain',
    'encode_wav',
    'duration',
    'length',
]

AudioBuffer: TypeAlias = dict[str, Any]

_DEFAULT_RATE = 44100


def buffer(length: float) -> AudioBuffer:
    """Return a buffer of ``length`` zero samples (negative lengths clamp to empty)."""
    return {'tag': 'audio.buffer', 'samples': [0] * max(0, int(length))}


def tone(freq: float, duration: float, rate: float = _DEFAULT_RATE) -> AudioBuffer:
    """Return a sine-wave buffer of ``freq`` Hz for ``duration`` seconds at ``rate``."""
    sample_rate = rate or _DEFAULT_RATE
    n = max(1, math.floor(duration * sample_rate + 0.5))
    samples = [math.sin(2 * math.pi * freq * i / sample_rate) for i in range(n)]
    return {'tag': 'audio.buffer', 'samples': samples, 'sampleRate': sample_rate}


def silence(duration: float, rate: float = _DEFAULT_RATE) -> AudioBuffer:
    """Return ``duration`` seconds of silence (zero samples) at ``rate``."""
    sample_rate = rate or _DEFAULT_RATE
    n = max(1, math.floor(duration * sample_rate + 0.5))
    return {'tag': 'audio.buffer', 'samples': [0] * n, 'sampleRate': sample_rate}


def sample(buffer: AudioBuffer, index: int) -> float:
    """Return the sample of ``buffer`` at ``index``, or 0 when out of range."""
    samples = _samples_of(buffer)
    if index < 0 or index >= len(samples):
        return 0
    return samples[index]


def mix(a: AudioBuffer, b: AudioBuffer) -> AudioBuffer:
    """Return a buffer whose samples sum ``a`` and ``b`` (missing samples count as zero)."""
    samples_a = _samples_of(a)
    samples_b = _samples_of(b)
    n = max(len(samples_a), len(samples_b))
    out: list[float] = []
    for i in range(n):
        value = 0.0
        if i < len(samples_a):
            value += samples_a[i]
        if i < len(samples_b):
            value += samples_b[i]
        out.append(value)
    sample_rate = _rate_of(a) or _rate_of(b) or _DEFAULT_RATE
    return {'tag': 'audio.buffer', 'samples': out, 'sampleRate': sample_rate}


def append(a: AudioBuffer, b: AudioBuffer) -> AudioBuffer:
    """Return a buffer concatenating ``a`` then ``b``, keeping ``a``'s sample rate."""
    samples = _samples_of(a) + _samples_of(b)
    return {'tag': 'audio.buffer', 'samples': samples, 'sampleRate': _rate_of(a) or _DEFAULT_RATE}


def gain(buffer: AudioBuffer, factor: float) -> AudioBuffer:
    """Return a buffer with every sample of ``buffer`` scaled by ``factor``."""
    samples = [s * factor for s in _samples_of(buffer)]
    return {
        'tag': 'audio.buffer',
        'samples': samples,
        'sampleRate': _rate_of(buffer) or _DEFAULT_RATE,
    }


def encode_wav(buffer: AudioBuffer) -> str:
    """Return a base64 WAV string (44-byte header, mono 16-bit PCM) for ``buffer``."""
    samples = _samples_of(buffer)
    sample_rate = _rate_of(buffer) or _DEFAULT_RATE
    data_size = len(samples) * 2
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        data_size + 36,
        b'WAVE',
        b'fmt ',
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b'data',
        data_size,
    )
    body = b''.join(
        struct.pack('<h', math.floor(max(-1.0, min(1.0, s)) * 32767 + 0.5)) for s in samples
    )
    return base64.b64encode(header + body).decode('ascii')


def duration(buffer: AudioBuffer) -> float:
    """Return the duration of ``buffer`` in seconds at its sample rate."""
    return len(_samples_of(buffer)) / (_rate_of(buffer) or _DEFAULT_RATE)


def length(buffer: AudioBuffer) -> int:
    """Return the number of samples in ``buffer``."""
    return len(_samples_of(buffer))


def _samples_of(buffer: AudioBuffer) -> list[float]:
    """Return the samples list of an audio buffer."""
    return cast(list[float], buffer['samples'])


def _rate_of(buffer: AudioBuffer) -> int:
    """Return the integer sample rate of an audio buffer, or 0 when absent."""
    return int(buffer.get('sampleRate') or 0)
