"""OMNISYS.gpu — portable data-parallel compute (GPU capability).

The portable core expresses data-parallel kernels as ``kernel(i, input)``
calls over explicit buffers; the default lane is a deterministic CPU fallback
so programs run and test everywhere. Registry (``OMNISYS_MODULES["gpu"]``):
every function except :func:`buffer` declares the ``GPU`` capability; that
capability is metadata here — every function is a plain synchronous Python
function with no hardware access.
"""

import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

from omnisys_core import panic

if TYPE_CHECKING:  # pragma: no cover
    # Registry dependency (core, graphics); graphics is unused by this lane.
    import omnisys_graphics  # noqa: F401  # pragma: no cover

__all__ = [
    'buffer',
    'compute',
    'parallel',
    'add',
    'scale',
    'dot',
    'matmul',
    'normalize',
    'device_info',
]

Buffer: TypeAlias = dict[str, Any]


def buffer(data: list[Any]) -> Buffer:
    """Copy ``data`` (or ``[]`` when empty) into a ``gpu.buffer`` value."""
    return {'tag': 'gpu.buffer', 'data': list(data or [])}


def compute(kernel: Callable[[int, object], Any], input: list[Any], size: float) -> list[Any]:
    """Run ``kernel(i, input)`` for each ``i`` in ``range(max(0, int(size)))``."""
    n = max(0, int(size))
    return [kernel(i, input) for i in range(n)]


def parallel(kernel: Callable[[int, Any], Any], list_: list[Any]) -> list[Any]:
    """Run ``kernel(i, item)`` over the enumerated items of ``list_``."""
    return [kernel(i, item) for i, item in enumerate(list(list_ or []))]


def add(a: list[float], b: list[float]) -> list[float]:
    """Return the element-wise sum of ``a`` and ``b``; panic on length mismatch."""
    if len(a) != len(b):
        panic('gpu.add: length mismatch')
    return [x + y for x, y in zip(a, b, strict=True)]


def scale(a: list[float], factor: float) -> list[float]:
    """Return ``a`` scaled by ``factor``."""
    return [v * factor for v in a]


def dot(a: list[float], b: list[float]) -> float:
    """Return the dot product of ``a`` and ``b``; panic on length mismatch."""
    if len(a) != len(b):
        panic('gpu.dot: length mismatch')
    total = 0.0
    for i in range(len(a)):
        total += a[i] * b[i]
    return total


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Multiply ``a`` (m x k) by ``b`` (k x n); panic on incompatible shapes."""
    if len(a[0]) != len(b):
        panic('gpu.matmul: incompatible matrices')
    out: list[list[float]] = []
    for i in range(len(a)):
        row: list[float] = []
        for j in range(len(b[0])):
            total = 0.0
            for p in range(len(b)):
                total += a[i][p] * b[p][j]
            row.append(total)
        out.append(row)
    return out


def normalize(a: list[float]) -> list[float]:
    """Return ``a`` scaled to unit length; return a copy when ``a`` is the zero vector."""
    total = 0.0
    for v in a:
        total += v * v
    length = math.sqrt(total)
    if length == 0:
        return a[:]
    return [v / length for v in a]


def device_info() -> dict[str, Any]:
    """Describe the default portable-CPU compute lane."""
    return {'tag': 'gpu.device', 'name': 'portable-cpu', 'lanes': ['js-fallback'], 'cores': 1}
