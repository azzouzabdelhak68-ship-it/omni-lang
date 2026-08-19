"""Unit tests for OMNISYS.ui."""

import omnisys_ui as ui


def test_element_builds_tagged_value() -> None:
    el = ui.element('span', {'class': 'x'}, [ui.text('hi')])
    assert el == {
        'tag': 'element',
        'kind': 'span',
        'attrs': {'class': 'x'},
        'children': [ui.text('hi')],
    }


def test_element_coerces_kind_and_defaults() -> None:
    el = ui.element(42, None, None)
    assert el['kind'] == '42'
    assert el['attrs'] == {}
    assert el['children'] == []


def test_text_node() -> None:
    assert ui.text('hello') == {'tag': 'text', 'content': 'hello'}


def test_text_coerces_content() -> None:
    assert ui.text(7) == {'tag': 'text', 'content': '7'}


def test_button_with_action() -> None:
    seen: list[str] = []

    def action() -> None:
        seen.append('clicked')

    btn = ui.button('Go', action)
    assert btn['tag'] == 'element'
    assert btn['kind'] == 'button'
    assert btn['attrs'] == {}
    assert btn['children'] == [ui.text('Go')]
    assert btn['action'] is action


def test_button_without_action_stores_none() -> None:
    assert ui.button('Go', None)['action'] is None


def test_button_with_non_callable_action_stores_none() -> None:
    assert ui.button('Go', 'nope')['action'] is None


def test_row_and_column() -> None:
    child = ui.text('a')
    assert ui.row([child]) == ui.element('row', {}, [child])
    assert ui.column([child]) == ui.element('column', {}, [child])


def test_input() -> None:
    assert ui.input('v', 'ph') == ui.element('input', {'value': 'v', 'placeholder': 'ph'}, [])


def test_bind_adds_attribute_on_copy() -> None:
    el = ui.input('', 'Search')
    bound = ui.bind(el, 'class', 'big')
    assert bound['attrs']['class'] == 'big'
    assert el['attrs'] == {'value': '', 'placeholder': 'Search'}


def test_bind_deep_copies_children() -> None:
    el = ui.row([ui.text('x')])
    bound = ui.bind(el, 'id', 'r')
    bound['children'].append(ui.text('y'))
    assert len(el['children']) == 1


def test_bind_drops_action_like_json_stringify() -> None:
    btn = ui.button('Go', lambda: None)
    bound = ui.bind(btn, 'class', 'btn')
    assert 'action' not in bound
    assert bound['attrs']['class'] == 'btn'


def test_state_get_set() -> None:
    st = ui.state(1)
    assert st == {'tag': 'state', 'value': 1, '_on_change': None}
    assert ui.state_get(st) == 1
    assert ui.state_set(st, 2) is st
    assert ui.state_get(st) == 2


def test_render_text_escapes_special_chars() -> None:
    assert ui.render(ui.text('<a>&"')) == '&lt;a&gt;&amp;&quot;'


def test_render_none_is_empty() -> None:
    assert ui.render(None) == ''


def test_render_row_and_column_styles() -> None:
    assert (
        ui.render(ui.row([ui.text('a')])) == '<div style="display:flex;flex-direction:row">a</div>'
    )
    assert (
        ui.render(ui.column([ui.text('a')]))
        == '<div style="display:flex;flex-direction:column">a</div>'
    )


def test_render_button_and_input() -> None:
    assert ui.render(ui.button('Go', None)) == '<button>Go</button>'
    assert ui.render(ui.input('', 'Search')) == '<input value="" placeholder="Search" />'


def test_render_custom_kind() -> None:
    el = ui.element('section', {'class': 'main'}, [ui.text('body')])
    assert ui.render(el) == '<section class="main">body</section>'


def test_render_unknown_kind_defaults_to_div() -> None:
    assert ui.render({'tag': 'element'}) == '<div></div>'


def test_render_ignores_non_whitelisted_attrs() -> None:
    el = ui.element('p', {'data-x': '1', 'id': 'p1'}, [])
    assert ui.render(el) == '<p id="p1"></p>'


def test_render_escapes_attribute_values() -> None:
    el = ui.element('p', {'id': 'a"b&c'}, [])
    assert ui.render(el) == '<p id="a&quot;b&amp;c"></p>'


def test_render_nested_tree() -> None:
    tree = ui.column([ui.row([ui.text('a'), ui.button('b', None)]), ui.input('', '')])
    assert ui.render(tree) == (
        '<div style="display:flex;flex-direction:column">'
        '<div style="display:flex;flex-direction:row">a<button>b</button></div>'
        '<input value="" placeholder="" />'
        '</div>'
    )


def test_to_html_is_render_alias() -> None:
    assert ui.to_html(ui.text('x')) == ui.render(ui.text('x'))
