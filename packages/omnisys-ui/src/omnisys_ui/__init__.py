"""OMNISYS.ui — portable semantic UI model (SwiftUI/WPF/Qt/web principles).

Elements are JSON-friendly trees that render to HTML. Mirrors the JS reference
lane ``omnisys/ui.js`` as locked by the compiler registry
(``OMNISYS_MODULES["ui"]``): ``element``/``text``/``row``/``column``/``input``
build values, ``bind`` deep-copies an element with one attribute added,
``state*`` manage a mutable cell, and ``render``/``to_html`` serialize a tree
to an HTML string. ``button`` stores its action callback on the element value.
"""

import json
from collections.abc import Callable
from typing import Any, TypeAlias, cast

__all__ = [
    'element',
    'text',
    'button',
    'row',
    'column',
    'input',
    'render',
    'to_html',
    'bind',
    'state',
    'state_get',
    'state_set',
    'state_on_change',
    'get_value',
    'get_form_data',
]

Element: TypeAlias = dict[str, Any]
State: TypeAlias = dict[str, Any]

_HTML_ESCAPES = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}
_WHITELISTED_ATTRS = frozenset({'value', 'placeholder', 'class', 'id'})


def element(kind: str, attrs: dict[str, Any] | None, children: list[Any] | None) -> Element:
    """Build an element node with ``kind``, ``attrs`` and ``children``."""
    return {'tag': 'element', 'kind': str(kind), 'attrs': attrs or {}, 'children': children or []}


def text(content: Any) -> Element:
    """Build a text leaf node holding the string form of ``content``."""
    return {'tag': 'text', 'content': str(content)}


def button(label: str, action: Callable[[], Any] | None) -> Element:
    """Build a button element with ``label`` text and an optional ``action``."""
    return {
        'tag': 'element',
        'kind': 'button',
        'attrs': {},
        'children': [text(label)],
        'action': action if callable(action) else None,
    }


def row(children: list[Any]) -> Element:
    """Build a horizontal flex container element."""
    return element('row', {}, children)


def column(children: list[Any]) -> Element:
    """Build a vertical flex container element."""
    return element('column', {}, children)


def input(value: str, placeholder: str) -> Element:
    """Build an input element with ``value`` and ``placeholder`` attributes."""
    return element('input', {'value': str(value), 'placeholder': str(placeholder)}, [])


def bind(element_: Element, slot: str, value: Any) -> Element:
    """Deep-copy ``element_`` and return the copy with ``attrs[slot]`` set."""
    out = json.loads(json.dumps(_jsonable(element_)))
    out['attrs'] = out.get('attrs') or {}
    out['attrs'][str(slot)] = value
    return cast(Element, out)


def state(value: Any) -> State:
    """Create a mutable state cell holding ``value``."""
    return {'tag': 'state', 'value': value, '_on_change': None}


def state_get(state: State) -> Any:
    """Return the value currently held by ``state``."""
    return state['value']


def state_set(state: State, value: Any) -> State:
    """Set the value held by ``state`` and return the same cell. Triggers any registered change callback."""
    state['value'] = value
    callback = state.get('_on_change')
    if callable(callback):
        callback()
    return state


def state_on_change(state: State, callback: Callable[[], Any] | None) -> None:
    """Register a callback to be invoked when ``state_set`` changes the value."""
    state['_on_change'] = callback


def render(element_: Any) -> str:
    """Render an element tree (or ``None``) to an HTML string."""
    return _element_to_html(element_)


to_html = render


def get_value(id: str) -> str:
    """Read the current value of the DOM element with ``id`` ('' when absent)."""
    return ''

def get_form_data(id: str) -> dict[str, Any]:
    """Read named form field values of the DOM element with ``id`` as a map."""
    return {}


def _jsonable(value: Any) -> Any:
    """Make ``value`` JSON-safe by dropping callable dict entries."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not callable(v)}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _escape_html(value: Any) -> str:
    """Escape ``&``, ``<``, ``>`` and ``"`` in the string form of ``value``."""
    out = str(value)
    for char, escaped in _HTML_ESCAPES.items():
        out = out.replace(char, escaped)
    return out


def _attrs_to_html(attrs: Any) -> str:
    """Serialize whitelisted attributes to an HTML attribute string."""
    out = ''
    for key, value in (attrs or {}).items():
        if key in _WHITELISTED_ATTRS:
            out += ' ' + key + '="' + _escape_html(value) + '"'
    return out


def _element_to_html(node: Any) -> str:
    """Render a single element tree node to an HTML fragment."""
    if node is None:
        return ''
    if node.get('tag') == 'text':
        return _escape_html(node.get('content'))
    kind = node.get('kind') or 'div'
    children = node.get('children') or []
    if kind in {'row', 'column'}:
        style = (
            'display:flex;flex-direction:row'
            if kind == 'row'
            else 'display:flex;flex-direction:column'
        )
        return (
            '<div style="'
            + style
            + '">'
            + ''.join(_element_to_html(c) for c in children)
            + '</div>'
        )
    if kind == 'button':
        return (
            '<button'
            + _attrs_to_html(node.get('attrs'))
            + '>'
            + ''.join(_element_to_html(c) for c in children)
            + '</button>'
        )
    if kind == 'input':
        return '<input' + _attrs_to_html(node.get('attrs')) + ' />'
    return (
        '<'
        + kind
        + _attrs_to_html(node.get('attrs'))
        + '>'
        + ''.join(_element_to_html(c) for c in children)
        + '</'
        + kind
        + '>'
    )
