"""OMNISYS.core â€” implicit root module (import OMNISYS).

Portable core: option/result wrappers, math helpers, length helpers, panic.
Pure, dependency-free. Mirrors the JS runtime ``omnisys/core.js`` with the
same tagged-value shapes so the Python and JS lanes stay in conformance.
"""

import math
from typing import Any, NoReturn

VERSION = '6.0.0'


class PanicError(Exception):
    """Raised by :func:`panic`; mirrors ``omnisys.core.panic`` throwing."""

    def __init__(self, message: str) -> None:
        """Initialize with ``message``."""
        super().__init__(message)
        self.message = message


def panic(message: str) -> NoReturn:
    """Abort with ``PanicError(message)`` (programmer error, not a Result)."""
    raise PanicError(message)


def option(value: Any) -> dict[str, Any]:
    """Wrap ``value`` as a ``{"tag": "some", "value": ...}`` Option."""
    return {'tag': 'some', 'value': value}


some = option


def none() -> dict[str, Any]:
    """Produce the empty Option value ``{"tag": "none"}``."""
    return {'tag': 'none'}


def is_some(opt: dict[str, Any]) -> bool:
    """Return True when ``opt`` is a ``some`` Option value."""
    return bool(opt and opt.get('tag') == 'some')


def is_none(opt: dict[str, Any]) -> bool:
    """Return True when ``opt`` is a ``none`` Option value."""
    return bool(opt and opt.get('tag') == 'none')


def ok(value: Any) -> dict[str, Any]:
    """Wrap ``value`` as a ``{"tag": "ok", "value": ...}`` Result."""
    return {'tag': 'ok', 'value': value}


def err(error: Any) -> dict[str, Any]:
    """Wrap ``error`` as a ``{"tag": "err", "error": ...}`` Result."""
    return {'tag': 'err', 'error': error}


def is_ok(res: dict[str, Any]) -> bool:
    """Return True when ``res`` is an ``ok`` Result value."""
    return bool(res and res.get('tag') == 'ok')


def is_err(res: dict[str, Any]) -> bool:
    """Return True when ``res`` is an ``err`` Result value."""
    return bool(res and res.get('tag') == 'err')


def identity(x: Any) -> Any:
    """Return ``x`` unchanged."""
    return x


def type_of(x: Any) -> str:
    """Portable type vocabulary: none/list/string/number/boolean/object."""
    if x is None:
        return 'none'
    if isinstance(x, list):
        return 'list'
    if isinstance(x, bool):
        return 'boolean'
    if isinstance(x, (int, float)):
        return 'number'
    if isinstance(x, str):
        return 'string'
    return 'object'


def abs(x: float) -> float:
    """Absolute value (mirrors ``Math.abs``)."""
    return math.fabs(x)


def min(a: float, b: float) -> float:
    """Lesser of two numbers (mirrors ``Math.min``)."""
    return a if a <= b else b


def max(a: float, b: float) -> float:
    """Greater of two numbers (mirrors ``Math.max``)."""
    return a if a >= b else b


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp ``x`` into ``[lo, hi]`` (mirrors ``Math.min(Math.max(...))``)."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def round(x: float) -> int:
    """Round half away from zero (mirrors ``Math.round``, not banker's)."""
    return math.floor(x + 0.5)


def floor(x: float) -> int:
    """Floor (mirrors ``Math.floor``)."""
    return math.floor(x)


def ceil(x: float) -> int:
    """Ceiling (mirrors ``Math.ceil``)."""
    return math.ceil(x)


def sqrt(x: float) -> float:
    """Square root; NaN for negatives (mirrors ``Math.sqrt``)."""
    return math.sqrt(x) if x >= 0.0 else math.nan


def length(x: Any) -> int:
    """Length of str/list/dict; 0 for everything else (mirrors ``core.length``)."""
    if x is None:
        return 0
    if isinstance(x, (str, list, dict)):
        return len(x)
    return 0


def is_empty(x: Any) -> bool:
    """Return True when :func:`length` of ``x`` is 0."""
    return length(x) == 0


def split(s: Any, sep: Any) -> list[str]:
    """Split ``s`` on ``sep`` (mirrors ``core.split``)."""
    return str(s).split(str(sep))


def char_at(s: Any, i: Any) -> str:
    """Return the character of ``s`` at index ``i`` or ``''`` when out of range."""
    text = str(s)
    idx = int(i)
    if idx < 0 or idx >= len(text):
        return ''
    return text[idx]


def substring(s: Any, start: Any, end: Any = None) -> str:
    """Substring of ``s`` from ``start`` to ``end`` (default: end of string)."""
    text = str(s)
    a = int(start)
    b = len(text) if end is None else int(end)
    if a < 0:
        a = 0
    if b < 0:
        b = 0
    if a > b:
        a, b = b, a
    return text[a:b]


def to_number(s: Any) -> float:
    """Parse ``s`` as a number; return 0.0 when unparseable."""
    try:
        n = float(str(s).strip())
    except ValueError:
        return 0.0
    return 0.0 if math.isnan(n) else n


__all__ = [
    'VERSION',
    'PanicError',
    'panic',
    'option',
    'some',
    'none',
    'is_some',
    'is_none',
    'ok',
    'err',
    'is_ok',
    'is_err',
    'identity',
    'type_of',
    'abs',
    'min',
    'max',
    'clamp',
    'round',
    'floor',
    'ceil',
    'sqrt',
    'length',
    'is_empty',
    'split',
    'char_at',
    'substring',
    'to_number',
]
