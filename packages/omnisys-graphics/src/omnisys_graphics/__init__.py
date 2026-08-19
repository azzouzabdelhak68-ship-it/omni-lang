"""OMNISYS.graphics — a portable 2D canvas model.

Python reference implementation of the OMNISYS ``graphics`` module (v6): a
canvas is a plain dict that records a deterministic list of draw operations,
and ``render``/``to_json`` expose that list as serializable output. Mirrors
the JS reference lane ``omnisys/graphics.js`` and satisfies the registry
contract (``OMNISYS_MODULES["graphics"]``): all eleven functions are pure and
depend only on the Python standard library.
"""

from typing import Any, TypeAlias, cast

__all__ = [
    'canvas',
    'clear',
    'line',
    'rect',
    'circle',
    'polygon',
    'text',
    'fill',
    'stroke',
    'render',
    'to_json',
]

Canvas: TypeAlias = dict[str, Any]
Number: TypeAlias = int | float


def canvas(width: Number, height: Number) -> Canvas:
    """Return a new empty canvas value with ``width`` and ``height``."""
    return {
        'tag': 'canvas',
        'width': width,
        'height': height,
        'ops': [],
        'fillColor': None,
        'strokeColor': None,
    }


def clear(canvas: Canvas, color: str | None) -> Canvas:
    """Append a ``clear`` operation to ``canvas`` and return the same value."""
    cast(list[dict[str, Any]], canvas['ops']).append({'op': 'clear', 'color': color})
    return canvas


def fill(canvas: Canvas, color: str | None) -> Canvas:
    """Set the default fill color of ``canvas`` and return the same value."""
    canvas['fillColor'] = color
    return canvas


def stroke(canvas: Canvas, color: str | None) -> Canvas:
    """Set the default stroke color of ``canvas`` and return the same value."""
    canvas['strokeColor'] = color
    return canvas


def line(  # noqa: PLR0913, PLR0917 - registry contract mandates six parameters
    canvas: Canvas,
    x1: Number,
    y1: Number,
    x2: Number,
    y2: Number,
    color: str | None,
) -> Canvas:
    """Append a ``line`` operation to ``canvas`` and return the same value."""
    stroke_color = color or canvas['strokeColor']
    cast(list[dict[str, Any]], canvas['ops']).append(
        {
            'op': 'line',
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'color': stroke_color,
        }
    )
    return canvas


def rect(  # noqa: PLR0913, PLR0917 - registry contract mandates six parameters
    canvas: Canvas,
    x: Number,
    y: Number,
    w: Number,
    h: Number,
    color: str | None,
) -> Canvas:
    """Append a ``rect`` operation to ``canvas`` and return the same value."""
    fill_color = color or canvas['fillColor']
    cast(list[dict[str, Any]], canvas['ops']).append(
        {'op': 'rect', 'x': x, 'y': y, 'w': w, 'h': h, 'color': fill_color}
    )
    return canvas


def circle(canvas: Canvas, cx: Number, cy: Number, r: Number, color: str | None) -> Canvas:
    """Append a ``circle`` operation to ``canvas`` and return the same value."""
    fill_color = color or canvas['fillColor']
    cast(list[dict[str, Any]], canvas['ops']).append(
        {'op': 'circle', 'cx': cx, 'cy': cy, 'r': r, 'color': fill_color}
    )
    return canvas


def polygon(canvas: Canvas, points: list[list[Number]], color: str | None) -> Canvas:
    """Append a ``polygon`` operation to ``canvas`` and return the same value."""
    fill_color = color or canvas['fillColor']
    cast(list[dict[str, Any]], canvas['ops']).append(
        {'op': 'polygon', 'points': points, 'color': fill_color}
    )
    return canvas


def text(canvas: Canvas, content: Any, x: Number, y: Number, color: str | None) -> Canvas:
    """Append a ``text`` operation with stringified ``content`` to ``canvas``."""
    fill_color = color or canvas['fillColor']
    cast(list[dict[str, Any]], canvas['ops']).append(
        {'op': 'text', 'content': str(content), 'x': x, 'y': y, 'color': fill_color}
    )
    return canvas


def render(canvas: Canvas) -> list[Any]:
    """Return a copy of the operation list of ``canvas``."""
    return cast(list[Any], canvas['ops'])[:]


def to_json(canvas: Canvas) -> Canvas:
    """Return a JSON-friendly view of ``canvas`` with a copied op list."""
    return {
        'tag': 'canvas',
        'width': canvas['width'],
        'height': canvas['height'],
        'ops': cast(list[Any], canvas['ops'])[:],
    }
