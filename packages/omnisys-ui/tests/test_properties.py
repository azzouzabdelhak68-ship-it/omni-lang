"""Property-based tests for OMNISYS.ui."""

import omnisys_ui as ui
from hypothesis import assume, given, settings
from hypothesis import strategies as st


@given(st.text())
def test_text_content_round_trips(content: str) -> None:
    assert ui.text(content)['content'] == content


@settings(max_examples=100)
@given(
    st.text(max_size=10),
    st.dictionaries(st.text(max_size=5), st.one_of(st.text(), st.integers()), max_size=4),
    st.lists(st.text(max_size=5), max_size=4),
)
def test_element_shape_invariant(
    kind: str, attrs: dict[str, str | int], children: list[str]
) -> None:
    el = ui.element(kind, attrs, children)
    assert set(el) == {'tag', 'kind', 'attrs', 'children'}
    assert el['kind'] == kind
    assert el['attrs'] == attrs
    assert el['children'] == children


@settings(max_examples=100)
@given(
    st.dictionaries(st.text(max_size=5), st.text(), max_size=4),
    st.text(max_size=10),
    st.one_of(st.text(), st.integers()),
)
def test_bind_sets_slot_and_preserves_original(
    attrs: dict[str, str], slot: str, value: str | int
) -> None:
    assume(slot not in attrs)
    el = ui.element('div', attrs, [])
    bound = ui.bind(el, slot, value)
    assert bound is not el
    assert bound['attrs'][slot] == value
    assert slot not in el['attrs']


@given(st.integers(), st.integers())
def test_state_set_get_round_trip(old: int, new: int) -> None:
    st = ui.state(old)
    ui.state_set(st, new)
    assert ui.state_get(st) == new


@given(st.text())
def test_render_never_leaves_raw_special_chars(content: str) -> None:
    html = ui.render(ui.text(content))
    cleaned = (
        html.replace('&amp;', '').replace('&lt;', '').replace('&gt;', '').replace('&quot;', '')
    )
    assert '<' not in cleaned
    assert '>' not in cleaned
    assert '&' not in cleaned
    assert '"' not in cleaned
