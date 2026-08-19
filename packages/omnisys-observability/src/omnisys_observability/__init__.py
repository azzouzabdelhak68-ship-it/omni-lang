"""OMNISYS.observability — logging, metrics, tracing, profiling.

Python reference implementation of the OMNISYS ``observability`` module (v6),
mirroring the JS reference lane ``omnisys/observability.js`` and satisfying
the registry contract (``OMNISYS_MODULES["observability"]``). An in-process
collector with a JSON snapshot. Portable; no external I/O; all eleven
functions are pure (module-level state is the only mutable surface).
"""

import time
from collections.abc import Callable
from typing import Any, TypeAlias

__all__ = [
    'log',
    'info',
    'warn',
    'error',
    'metric',
    'metric_value',
    'trace_begin',
    'trace_end',
    'snapshot',
    'clear',
    'profile',
]

LogEntry: TypeAlias = dict[str, Any]
MetricMap: TypeAlias = dict[str, float]
TraceEntry: TypeAlias = dict[str, Any]
Snapshot: TypeAlias = dict[str, Any]

_state: dict[str, Any] = {'logs': [], 'metrics': {}, 'traces': [], 'nextTrace': 1}


def clear() -> None:
    """Reset the collector state: logs, metrics, traces and trace counter."""
    _state['logs'] = []
    _state['metrics'] = {}
    _state['traces'] = []
    _state['nextTrace'] = 1


def log(level: Any, message: Any, fields: Any) -> None:
    """Append a ``{level, message, fields, at}`` entry to the log."""
    entry = {
        'level': str(level),
        'message': str(message),
        'fields': fields or {},
        'at': time.time() * 1000,
    }
    _state['logs'].append(entry)


def info(message: Any, fields: Any = None) -> None:
    """Log an ``info``-level entry."""
    log('info', message, fields)


def warn(message: Any, fields: Any = None) -> None:
    """Log a ``warn``-level entry."""
    log('warn', message, fields)


def error(message: Any, fields: Any = None) -> None:
    """Log an ``error``-level entry."""
    log('error', message, fields)


def metric(name: Any, value: Any) -> None:
    """Record ``value`` under ``name`` as a float."""
    _state['metrics'][str(name)] = float(value)


def metric_value(name: Any) -> float:
    """Return the recorded value for ``name``, or ``0`` when unknown."""
    return float(_state['metrics'].get(str(name), 0))


def trace_begin(name: Any) -> int:
    """Start a trace span named ``name``; returns its id."""
    trace_id = int(_state['nextTrace'])
    _state['nextTrace'] = trace_id + 1
    _state['traces'].append(
        {'id': trace_id, 'name': str(name), 'start': time.time() * 1000, 'end': None, 'fields': {}}
    )
    return trace_id


def trace_end(trace_id: Any, fields: Any = None) -> None:
    """Close the trace span with id ``trace_id`` (no-op when unknown)."""
    for trace in _state['traces']:
        if trace['id'] == trace_id:
            trace['end'] = time.time() * 1000
            trace['duration'] = trace['end'] - trace['start']
            trace['fields'] = fields or {}
            return


def snapshot() -> Snapshot:
    """Return a JSON-friendly copy of the current collector state."""
    return {
        'logs': list(_state['logs']),
        'metrics': dict(_state['metrics']),
        'traces': [dict(trace) for trace in _state['traces']],
    }


def profile(fn: Callable[[], Any], iterations: Any) -> float:
    """Run ``fn`` ``max(1, int(iterations))`` times; return elapsed ms."""
    n = max(1, int(iterations))
    start = time.time() * 1000
    for _ in range(n):
        fn()
    return time.time() * 1000 - start
