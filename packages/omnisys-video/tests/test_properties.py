"""Property tests for OMNISYS.video."""

from __future__ import annotations

import omnisys_video as video
from hypothesis import assume, given
from hypothesis import strategies as st
from omnisys_core import PanicError


@given(st.integers(min_value=-4, max_value=16), st.integers(min_value=-4, max_value=16))
def test_frame_dimensions_match_metadata(width: int, height: int) -> None:
    t = video.timeline(30)
    video.add_frame(t, video.frame(width, height))
    m = video.metadata(t)
    assert m['frames'] == 1
    assert m['width'] == width
    assert m['height'] == height
    assert m['duration'] == 1 / 30


@given(st.integers(min_value=0, max_value=16))
def test_add_frame_increments_frame_count(n: int) -> None:
    t = video.timeline(30)
    for _ in range(n):
        video.add_frame(t, video.frame(1, 1))
    assert video.frame_count(t) == n
    assert video.metadata(t)['frames'] == n


@given(st.lists(st.integers(min_value=0, max_value=4), max_size=4))
def test_seek_round_trips_added_frames(dims: list[int]) -> None:
    t = video.timeline(30)
    frames = [video.frame(2, 2) for _ in dims]
    for f in frames:
        video.add_frame(t, f)
    for i, f in enumerate(frames):
        assert video.seek(t, i) == f
    assert video.frame_count(t) == len(frames)


@given(st.integers(min_value=0, max_value=3), st.integers(min_value=0, max_value=3))
def test_set_pixel_in_bounds_round_trips(x: int, y: int) -> None:
    f = video.frame(4, 4)
    result = video.set_pixel(f, x, y, '#ff0000')
    assert result is f
    assert f['pixels'][y][x] == '#ff0000'


@given(
    st.integers(),
    st.integers(),
    st.integers(min_value=1, max_value=4),
    st.integers(min_value=1, max_value=4),
)
def test_set_pixel_out_of_bounds_always_panics(x: int, y: int, width: int, height: int) -> None:
    assume(not (0 <= x < width and 0 <= y < height))
    f = video.frame(width, height)
    try:
        video.set_pixel(f, x, y, '#fff')
    except PanicError:
        return
    raise AssertionError(f'set_pixel did not panic for x={x}, y={y}')


@given(st.lists(st.text(), max_size=5))
def test_frame_from_ascii_shape_matches_rows(rows: list[str]) -> None:
    f = video.frame_from_ascii(rows)
    assert f['height'] == len(rows)
    assert f['width'] == (len(rows[0]) if rows else 0)


@given(st.lists(st.text(max_size=8), min_size=1, max_size=8))
def test_frame_from_ascii_pixels_match_characters(rows: list[str]) -> None:
    f = video.frame_from_ascii(rows)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            assert f['pixels'][y][x] == ('#000000' if ch == ' ' else '#ffffff')


@given(st.integers(min_value=0, max_value=8), st.integers(min_value=1, max_value=120))
def test_metadata_duration_is_frames_over_fps(n: int, fps: int) -> None:
    t = video.timeline(fps)
    for _ in range(n):
        video.add_frame(t, video.frame(1, 1))
    m = video.metadata(t)
    assert m['frames'] == n
    assert m['fps'] == fps
    assert m['duration'] == n / fps


@given(st.integers(min_value=1, max_value=60))
def test_fps_of_round_trips_timeline(fps: int) -> None:
    assert video.fps_of(video.timeline(fps)) == fps
