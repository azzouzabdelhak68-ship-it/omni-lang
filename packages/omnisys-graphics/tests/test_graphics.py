"""Unit tests for every OMNISYS.graphics function."""

import omnisys_graphics as g


def test_canvas_builds_value_shape() -> None:
    result = g.canvas(800, 600)
    assert result == {
        'tag': 'canvas',
        'width': 800,
        'height': 600,
        'ops': [],
        'fillColor': None,
        'strokeColor': None,
    }


def test_canvas_accepts_float_dimensions() -> None:
    result = g.canvas(2.5, 3.0)
    assert result['width'] == 2.5
    assert result['height'] == 3.0


def test_clear_appends_op_and_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.clear(c, 'white') is c
    assert c['ops'] == [{'op': 'clear', 'color': 'white'}]


def test_clear_accepts_none_color() -> None:
    c = g.canvas(10, 10)
    g.clear(c, None)
    assert c['ops'] == [{'op': 'clear', 'color': None}]


def test_fill_sets_fill_color_and_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.fill(c, '#111') is c
    assert c['fillColor'] == '#111'


def test_fill_does_not_record_op() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'red')
    assert c['ops'] == []


def test_stroke_sets_stroke_color_and_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.stroke(c, '#222') is c
    assert c['strokeColor'] == '#222'


def test_stroke_does_not_record_op() -> None:
    c = g.canvas(10, 10)
    g.stroke(c, 'blue')
    assert c['ops'] == []


def test_line_appends_op_with_color() -> None:
    c = g.canvas(10, 10)
    g.line(c, 1, 2, 3, 4, 'red')
    assert c['ops'] == [{'op': 'line', 'x1': 1, 'y1': 2, 'x2': 3, 'y2': 4, 'color': 'red'}]


def test_line_none_color_inherits_stroke() -> None:
    c = g.canvas(10, 10)
    g.stroke(c, 'blue')
    g.line(c, 0, 0, 5, 5, None)
    assert c['ops'][0]['color'] == 'blue'


def test_line_empty_string_color_inherits_stroke() -> None:
    c = g.canvas(10, 10)
    g.stroke(c, 'blue')
    g.line(c, 0, 0, 5, 5, '')
    assert c['ops'][0]['color'] == 'blue'


def test_line_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.line(c, 0, 0, 1, 1, 'red') is c


def test_rect_appends_op_with_color() -> None:
    c = g.canvas(10, 10)
    g.rect(c, 10, 20, 30, 40, '#eee')
    assert c['ops'] == [{'op': 'rect', 'x': 10, 'y': 20, 'w': 30, 'h': 40, 'color': '#eee'}]


def test_rect_none_color_inherits_fill() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'green')
    g.rect(c, 1, 2, 3, 4, None)
    assert c['ops'][0]['color'] == 'green'


def test_rect_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.rect(c, 0, 0, 1, 1, 'red') is c


def test_circle_appends_op_with_color() -> None:
    c = g.canvas(10, 10)
    g.circle(c, 5, 5, 3, 'blue')
    assert c['ops'] == [{'op': 'circle', 'cx': 5, 'cy': 5, 'r': 3, 'color': 'blue'}]


def test_circle_none_color_inherits_fill() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'navy')
    g.circle(c, 1, 1, 2, None)
    assert c['ops'][0]['color'] == 'navy'


def test_circle_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.circle(c, 0, 0, 1, 'red') is c


def test_polygon_appends_op_with_points() -> None:
    c = g.canvas(10, 10)
    points = [[0, 0], [1, 1], [2, 0]]
    g.polygon(c, points, 'gold')
    assert c['ops'] == [{'op': 'polygon', 'points': points, 'color': 'gold'}]


def test_polygon_none_color_inherits_fill() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'purple')
    g.polygon(c, [[0, 0], [5, 5]], None)
    assert c['ops'][0]['color'] == 'purple'


def test_polygon_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.polygon(c, [[0, 0]], 'red') is c


def test_text_stringifies_integer_content() -> None:
    c = g.canvas(10, 10)
    g.text(c, 42, 5, 6, 'navy')
    assert c['ops'] == [{'op': 'text', 'content': '42', 'x': 5, 'y': 6, 'color': 'navy'}]


def test_text_stringifies_float_content() -> None:
    c = g.canvas(10, 10)
    g.text(c, 1.5, 0, 0, None)
    assert c['ops'][0]['content'] == '1.5'


def test_text_keeps_text_content() -> None:
    c = g.canvas(10, 10)
    g.text(c, 'hello', 1, 2, None)
    assert c['ops'][0]['content'] == 'hello'


def test_text_none_color_inherits_fill() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'coral')
    g.text(c, 'x', 0, 0, None)
    assert c['ops'][0]['color'] == 'coral'


def test_text_returns_same_canvas() -> None:
    c = g.canvas(10, 10)
    assert g.text(c, 'x', 0, 0, 'red') is c


def test_ops_accumulate_in_call_order() -> None:
    c = g.canvas(10, 10)
    g.clear(c, 'white')
    g.fill(c, 'black')
    g.stroke(c, 'gray')
    g.line(c, 0, 0, 1, 1, 'red')
    g.rect(c, 0, 0, 1, 1, 'blue')
    g.circle(c, 2, 2, 1, 'green')
    g.polygon(c, [[0, 0], [1, 1]], 'gold')
    g.text(c, 'hi', 3, 3, 'purple')
    assert [op['op'] for op in c['ops']] == ['clear', 'line', 'rect', 'circle', 'polygon', 'text']
    assert c['fillColor'] == 'black'
    assert c['strokeColor'] == 'gray'


def test_render_returns_copy_of_ops() -> None:
    c = g.canvas(10, 10)
    g.line(c, 0, 0, 1, 1, 'red')
    result = g.render(c)
    assert result == c['ops']
    assert result is not c['ops']
    result.append({'op': 'line', 'x1': 9, 'y1': 9, 'x2': 9, 'y2': 9, 'color': None})
    assert len(c['ops']) == 1


def test_render_empty_canvas() -> None:
    assert g.render(g.canvas(10, 10)) == []


def test_to_json_shape() -> None:
    c = g.canvas(800, 600)
    g.line(c, 0, 0, 1, 1, 'red')
    result = g.to_json(c)
    assert result == {
        'tag': 'canvas',
        'width': 800,
        'height': 600,
        'ops': [{'op': 'line', 'x1': 0, 'y1': 0, 'x2': 1, 'y2': 1, 'color': 'red'}],
    }


def test_to_json_excludes_paint_colors() -> None:
    c = g.canvas(10, 10)
    g.fill(c, 'black')
    g.stroke(c, 'gray')
    result = g.to_json(c)
    assert 'fillColor' not in result
    assert 'strokeColor' not in result


def test_to_json_ops_is_detached_copy() -> None:
    c = g.canvas(10, 10)
    g.line(c, 0, 0, 1, 1, 'red')
    result = g.to_json(c)
    result['ops'].append({'op': 'clear', 'color': None})
    assert len(c['ops']) == 1
    g.line(c, 2, 2, 3, 3, 'blue')
    assert len(result['ops']) == 2
    assert result['ops'][1] == {'op': 'clear', 'color': None}


def test_to_json_empty_canvas() -> None:
    assert g.to_json(g.canvas(1, 2)) == {'tag': 'canvas', 'width': 1, 'height': 2, 'ops': []}
