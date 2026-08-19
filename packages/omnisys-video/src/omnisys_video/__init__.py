"""OMNISYS.video — a portable video model: frames, timelines, seeking, metadata.

Python reference implementation of the OMNISYS ``video`` module (v6): a frame
is a JSON-friendly grid of pixel color cells, a timeline is an ordered list of
frames with an fps. Mirrors the JS reference lane ``omnisys/video.js`` and
satisfies the registry contract (``OMNISYS_MODULES["video"]``): all nine
functions are pure (zero declared effects) and depend on ``omnisys_core.panic``
for the shared out-of-bounds errors. Real codec decode/encode is an escape
(FFmpeg/WebCodecs backends); this is the portable semantic core.
"""

from copy import deepcopy
from typing import Any, TypeAlias, cast

from omnisys_core import panic

__all__ = [
    'frame',
    'frame_from_ascii',
    'set_pixel',
    'timeline',
    'add_frame',
    'seek',
    'frame_count',
    'fps_of',
    'metadata',
]

VideoFrame: TypeAlias = dict[str, Any]
Timeline: TypeAlias = dict[str, Any]


def frame(width: Any, height: Any) -> VideoFrame:
    """Return a black ``VideoFrame`` with ``int(width)`` by ``int(height)`` pixels."""
    pixels = [['#000000'] * max(0, int(width)) for _ in range(max(0, int(height)))]
    return {'tag': 'video.frame', 'width': width, 'height': height, 'pixels': pixels}


def frame_from_ascii(rows: Any) -> VideoFrame:
    """Return a frame from ASCII art: ``' '`` → black, any other char → white."""
    pixels = [['#000000' if ch == ' ' else '#ffffff' for ch in str(row)] for row in rows]
    return {
        'tag': 'video.frame',
        'width': len(pixels[0]) if pixels else 0,
        'height': len(pixels),
        'pixels': pixels,
    }


def set_pixel(frame: VideoFrame, x: Any, y: Any, color: Any) -> VideoFrame:
    """Set pixel ``(x, y)`` to ``str(color)``; panic when out of bounds."""
    rows = cast(list[Any], frame['pixels'])
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[y]):
        panic('video.set_pixel: out of bounds')
    rows[y][x] = str(color)
    return frame


def timeline(fps: Any) -> Timeline:
    """Return an empty timeline value with ``fps`` (default 30)."""
    return {'tag': 'video.timeline', 'fps': fps or 30, 'frames': []}


def add_frame(timeline: Timeline, frame_: VideoFrame) -> Timeline:
    """Append a deep copy of ``frame_`` and return the same timeline."""
    cast(list[Any], timeline['frames']).append(deepcopy(frame_))
    return timeline


def seek(timeline: Timeline, index: Any) -> VideoFrame:
    """Return the stored ``index`` frame; panic when out of range."""
    frames = cast(list[Any], timeline['frames'])
    if index < 0 or index >= len(frames):
        panic('video.seek: frame out of range')
    return cast(VideoFrame, frames[index])


def frame_count(timeline: Timeline) -> int:
    """Return the number of frames in ``timeline``."""
    return len(cast(list[Any], timeline['frames']))


def fps_of(timeline: Timeline) -> Any:
    """Return the ``fps`` of ``timeline``."""
    return timeline['fps']


def metadata(timeline: Timeline) -> dict[str, Any]:
    """Return ``{frames, fps, duration, width, height}`` for ``timeline``."""
    frames = cast(list[Any], timeline['frames'])
    first = cast(VideoFrame, frames[0]) if frames else None
    return {
        'frames': len(frames),
        'fps': timeline['fps'],
        'duration': len(frames) / (timeline['fps'] or 30),
        'width': first['width'] if first else 0,
        'height': first['height'] if first else 0,
    }
