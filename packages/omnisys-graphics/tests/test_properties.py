"""Hypothesis property tests for OMNISYS.graphics invariants."""

import omnisys_graphics as g
from hypothesis import given, settings
from hypothesis import strategies as st

_SETTINGS = settings(max_examples=150, deadline=None)

_DIM = st.integers(min_value=-1_000_000, max_value=1_000_000)
_NUM = st.integers(min_value=-1_000_000, max_value=1_000_000)
_COLOR = st.one_of(st.none(), st.text(max_size=16))
_TEXT = st.text(max_size=64)
_CONTENT = st.one_of(st.none(), _TEXT, _NUM)
_POINT = st.lists(_NUM, min_size=2, max_size=2)
_POINTS = st.lists(_POINT, max_size=20)


@_SETTINGS
@given(_DIM, _DIM)
def test_canvas_shape(width: int, height: int) -> None:
    c = g.canvas(width, height)
    assert c['tag'] == 'canvas'
    assert c['width'] == width
    assert c['height'] == height
    assert c['ops'] == []
    assert c['fillColor'] is None
    assert c['strokeColor'] is None


@_SETTINGS
@given(_NUM, _NUM, _NUM, _NUM, _COLOR)
def test_line_appends_exactly_one_op(x1: int, y1: int, x2: int, y2: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    assert g.line(c, x1, y1, x2, y2, color) is c
    assert len(c['ops']) == 1
    op = c['ops'][0]
    assert op['op'] == 'line'
    assert op['x1'] == x1
    assert op['y1'] == y1
    assert op['x2'] == x2
    assert op['y2'] == y2


@_SETTINGS
@given(_NUM, _NUM, _NUM, _NUM, _COLOR)
def test_line_color_falls_back_to_stroke(
    x1: int, y1: int, x2: int, y2: int, color: str | None
) -> None:
    c = g.canvas(1, 1)
    g.stroke(c, '#abc')
    op = g.line(c, x1, y1, x2, y2, color)['ops'][0]
    assert op['color'] == (color or '#abc')


@_SETTINGS
@given(_NUM, _NUM, _NUM, _NUM, _COLOR)
def test_rect_appends_exactly_one_op(x: int, y: int, w: int, h: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    assert g.rect(c, x, y, w, h, color) is c
    assert len(c['ops']) == 1
    op = c['ops'][0]
    assert op['op'] == 'rect'
    assert op['x'] == x
    assert op['y'] == y
    assert op['w'] == w
    assert op['h'] == h


@_SETTINGS
@given(_NUM, _NUM, _NUM, _NUM, _COLOR)
def test_rect_color_falls_back_to_fill(x: int, y: int, w: int, h: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    g.fill(c, '#def')
    op = g.rect(c, x, y, w, h, color)['ops'][0]
    assert op['color'] == (color or '#def')


@_SETTINGS
@given(_NUM, _NUM, _NUM, _COLOR)
def test_circle_appends_exactly_one_op(cx: int, cy: int, r: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    assert g.circle(c, cx, cy, r, color) is c
    assert len(c['ops']) == 1
    op = c['ops'][0]
    assert op['op'] == 'circle'
    assert op['cx'] == cx
    assert op['cy'] == cy
    assert op['r'] == r


@_SETTINGS
@given(_NUM, _NUM, _NUM, _COLOR)
def test_circle_color_falls_back_to_fill(cx: int, cy: int, r: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    g.fill(c, '#def')
    op = g.circle(c, cx, cy, r, color)['ops'][0]
    assert op['color'] == (color or '#def')


@_SETTINGS
@given(_POINTS, _COLOR)
def test_polygon_appends_exactly_one_op(points: list[list[int]], color: str | None) -> None:
    c = g.canvas(1, 1)
    assert g.polygon(c, points, color) is c
    assert len(c['ops']) == 1
    op = c['ops'][0]
    assert op['op'] == 'polygon'
    assert op['points'] == points


@_SETTINGS
@given(_POINTS, _COLOR)
def test_polygon_color_falls_back_to_fill(points: list[list[int]], color: str | None) -> None:
    c = g.canvas(1, 1)
    g.fill(c, '#def')
    op = g.polygon(c, points, color)['ops'][0]
    assert op['color'] == (color or '#def')


@_SETTINGS
@given(_CONTENT, _NUM, _NUM, _COLOR)
def test_text_appends_exactly_one_op(content: object, x: int, y: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    assert g.text(c, content, x, y, color) is c
    assert len(c['ops']) == 1
    op = c['ops'][0]
    assert op['op'] == 'text'
    assert op['content'] == str(content)
    assert op['x'] == x
    assert op['y'] == y


@_SETTINGS
@given(_TEXT, _NUM, _NUM, _COLOR)
def test_text_color_falls_back_to_fill(content: str, x: int, y: int, color: str | None) -> None:
    c = g.canvas(1, 1)
    g.fill(c, '#def')
    op = g.text(c, content, x, y, color)['ops'][0]
    assert op['color'] == (color or '#def')


@_SETTINGS
@given(_COLOR, _COLOR)
def test_fill_stroke_do_not_record_ops(color1: str | None, color2: str | None) -> None:
    c = g.canvas(1, 1)
    g.fill(c, color1)
    g.stroke(c, color2)
    assert c['ops'] == []
    assert c['fillColor'] == color1
    assert c['strokeColor'] == color2


@_SETTINGS
@given(_DIM, _DIM, _POINTS, _TEXT, _NUM, _NUM)
def test_ops_preserve_canvas_header(  # noqa: PLR0913, PLR0917
    width: int, height: int, points: list[list[int]], content: str, x: int, y: int
) -> None:
    c = g.canvas(width, height)
    g.line(c, 0, 0, 1, 1, 'black')
    g.rect(c, 0, 0, 1, 1, 'red')
    g.circle(c, 1, 1, 1, 'blue')
    g.polygon(c, points, 'green')
    g.text(c, content, x, y, 'purple')
    assert c['tag'] == 'canvas'
    assert c['width'] == width
    assert c['height'] == height
    assert [op['op'] for op in c['ops']] == ['line', 'rect', 'circle', 'polygon', 'text']


@_SETTINGS
@given(_POINTS, _TEXT)
def test_render_matches_ops_and_is_detached(points: list[list[int]], content: str) -> None:
    c = g.canvas(50, 50)
    g.polygon(c, points, None)
    g.text(c, content, 0, 0, None)
    result = g.render(c)
    assert result == c['ops']
    assert result is not c['ops']
    result.append({'op': 'hack', 'color': None})
    result.pop(0)
    assert len(c['ops']) == 2
    assert c['ops'][0] == {'op': 'polygon', 'points': points, 'color': None}
    assert c['ops'][1] == {'op': 'text', 'content': content, 'x': 0, 'y': 0, 'color': None}


@_SETTINGS
@given(_DIM, _DIM, _POINTS, _TEXT)
def test_to_json_shape_and_isolation(
    width: int, height: int, points: list[list[int]], _content: str
) -> None:
    c = g.canvas(width, height)
    g.fill(c, '#f00')
    g.stroke(c, '#0f0')
    g.polygon(c, points, None)
    result = g.to_json(c)
    assert result['tag'] == 'canvas'
    assert result['width'] == width
    assert result['height'] == height
    assert result['ops'] == c['ops']
    assert 'fillColor' not in result
    assert 'strokeColor' not in result
    result['ops'].append({'op': 'hack', 'color': None})
    assert len(c['ops']) == 1
    g.line(c, 0, 0, 1, 1, 'black')
    assert len(result['ops']) == 2
    assert result['ops'][1] == {'op': 'hack', 'color': None}
    assert c['ops'][1]['op'] == 'line'
