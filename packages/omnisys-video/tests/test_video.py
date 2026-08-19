"""Unit tests for OMNISYS.video."""

from __future__ import annotations

import omnisys_video as video
import pytest
from omnisys_core import PanicError


def test_frame_shape() -> None:
    f = video.frame(2, 3)
    assert f['tag'] == 'video.frame'
    assert f['width'] == 2
    assert f['height'] == 3
    assert f['pixels'] == [
        ['#000000', '#000000'],
        ['#000000', '#000000'],
        ['#000000', '#000000'],
    ]


def test_frame_single_row() -> None:
    f = video.frame(3, 1)
    assert f['pixels'] == [['#000000', '#000000', '#000000']]


def test_frame_clamps_negative_dimensions() -> None:
    f = video.frame(-4, -2)
    assert f['pixels'] == []
    assert f['width'] == -4
    assert f['height'] == -2


def test_frame_clamps_mixed_negative_dimension() -> None:
    f = video.frame(2, -1)
    assert f['pixels'] == []
    f2 = video.frame(-1, 2)
    assert f2['pixels'] == [[], []]


def test_frame_truncates_float_dimensions() -> None:
    f = video.frame(2.9, 3.9)
    assert f['width'] == 2.9
    assert f['height'] == 3.9
    assert len(f['pixels']) == 3
    assert len(f['pixels'][0]) == 2


def test_frame_from_ascii_basic() -> None:
    f = video.frame_from_ascii(['# ', ' #'])
    assert f['tag'] == 'video.frame'
    assert f['width'] == 2
    assert f['height'] == 2
    assert f['pixels'] == [
        ['#ffffff', '#000000'],
        ['#000000', '#ffffff'],
    ]


def test_frame_from_ascii_blank_row_is_all_black() -> None:
    f = video.frame_from_ascii(['   '])
    assert f['pixels'] == [['#000000', '#000000', '#000000']]


def test_frame_from_ascii_empty_rows_have_zero_width() -> None:
    f = video.frame_from_ascii([])
    assert f['tag'] == 'video.frame'
    assert f['width'] == 0
    assert f['height'] == 0
    assert f['pixels'] == []


def test_frame_from_ascii_coerces_row_values_to_string() -> None:
    f = video.frame_from_ascii(['ab', 7])
    assert f['pixels'] == [
        ['#ffffff', '#ffffff'],
        ['#ffffff'],
    ]


def test_set_pixel_writes_str_color_and_returns_frame() -> None:
    f = video.frame(2, 2)
    result = video.set_pixel(f, 1, 0, '#ff0000')
    assert result is f
    assert f['pixels'][0][1] == '#ff0000'


def test_set_pixel_coerces_color_to_string() -> None:
    f = video.frame(1, 1)
    video.set_pixel(f, 0, 0, 123)
    assert f['pixels'][0][0] == '123'


def test_set_pixel_panics_on_negative_x() -> None:
    f = video.frame(2, 2)
    with pytest.raises(PanicError, match='video.set_pixel: out of bounds'):
        video.set_pixel(f, -1, 0, '#fff')


def test_set_pixel_panics_on_negative_y() -> None:
    f = video.frame(2, 2)
    with pytest.raises(PanicError, match='video.set_pixel: out of bounds'):
        video.set_pixel(f, 0, -1, '#fff')


def test_set_pixel_panics_on_x_out_of_bounds() -> None:
    f = video.frame(2, 2)
    with pytest.raises(PanicError, match='video.set_pixel: out of bounds'):
        video.set_pixel(f, 2, 0, '#fff')


def test_set_pixel_panics_on_y_out_of_bounds() -> None:
    f = video.frame(2, 2)
    with pytest.raises(PanicError, match='video.set_pixel: out of bounds'):
        video.set_pixel(f, 0, 2, '#fff')


def test_timeline_shape_and_default_fps() -> None:
    t = video.timeline(None)
    assert t == {'tag': 'video.timeline', 'fps': 30, 'frames': []}


def test_timeline_keeps_explicit_fps() -> None:
    t = video.timeline(60)
    assert t['fps'] == 60


def test_timeline_zero_fps_defaults_to_30() -> None:
    t = video.timeline(0)
    assert t['fps'] == 30


def test_add_frame_appends_and_returns_timeline() -> None:
    t = video.timeline(30)
    f = video.frame(1, 1)
    result = video.add_frame(t, f)
    assert result is t
    assert video.frame_count(t) == 1
    assert t['frames'][0] == f


def test_add_frame_deep_copies_source_frame() -> None:
    t = video.timeline(30)
    f = video.frame(2, 2)
    video.add_frame(t, f)
    video.set_pixel(f, 0, 0, '#ffffff')
    assert t['frames'][0]['pixels'][0][0] == '#000000'


def test_add_frame_stored_copy_is_independent() -> None:
    t = video.timeline(30)
    f = video.frame(2, 2)
    video.add_frame(t, f)
    stored = t['frames'][0]
    video.set_pixel(stored, 1, 1, '#ffffff')
    assert f['pixels'][1][1] == '#000000'


def test_seek_returns_stored_frames_in_order() -> None:
    t = video.timeline(30)
    a = video.frame(1, 1)
    b = video.frame(1, 1)
    video.add_frame(t, a)
    video.add_frame(t, b)
    assert video.seek(t, 0) == a
    assert video.seek(t, 1) == b
    assert video.seek(t, 1) is t['frames'][1]


def test_seek_panics_on_negative_index() -> None:
    t = video.timeline(30)
    video.add_frame(t, video.frame(1, 1))
    with pytest.raises(PanicError, match='video.seek: frame out of range'):
        video.seek(t, -1)


def test_seek_panics_past_end() -> None:
    t = video.timeline(30)
    video.add_frame(t, video.frame(1, 1))
    with pytest.raises(PanicError, match='video.seek: frame out of range'):
        video.seek(t, 1)


def test_seek_panics_on_empty_timeline() -> None:
    t = video.timeline(30)
    with pytest.raises(PanicError):
        video.seek(t, 0)


def test_frame_count_tracks_added_frames() -> None:
    t = video.timeline(30)
    assert video.frame_count(t) == 0
    video.add_frame(t, video.frame(1, 1))
    video.add_frame(t, video.frame(1, 1))
    assert video.frame_count(t) == 2


def test_fps_of_returns_timeline_fps() -> None:
    t = video.timeline(24)
    assert video.fps_of(t) == 24


def test_metadata_empty_timeline() -> None:
    t = video.timeline(None)
    assert video.metadata(t) == {
        'frames': 0,
        'fps': 30,
        'duration': 0.0,
        'width': 0,
        'height': 0,
    }


def test_metadata_populated_timeline() -> None:
    t = video.timeline(24)
    video.add_frame(t, video.frame(4, 3))
    video.add_frame(t, video.frame(4, 3))
    assert video.metadata(t) == {
        'frames': 2,
        'fps': 24,
        'duration': 2 / 24,
        'width': 4,
        'height': 3,
    }


def test_metadata_uses_first_frame_dimensions() -> None:
    t = video.timeline(30)
    video.add_frame(t, video.frame(4, 3))
    video.add_frame(t, video.frame(8, 6))
    m = video.metadata(t)
    assert m['width'] == 4
    assert m['height'] == 3


def test_metadata_zero_fps_defaults_to_30_in_duration() -> None:
    t: dict = {'tag': 'video.timeline', 'fps': 0, 'frames': [video.frame(2, 2)]}
    m = video.metadata(t)
    assert m['fps'] == 0
    assert m['duration'] == 1 / 30
