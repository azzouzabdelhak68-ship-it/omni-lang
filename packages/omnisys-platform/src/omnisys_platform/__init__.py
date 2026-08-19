"""OMNISYS.platform — native platform abstractions (Python process lane).

Python reference implementation of the OMNISYS ``platform`` module (v6):
reports OS, architecture, environment and monotonic time, and lists what the
current lane can do. Mirrors the JS reference lane ``omnisys/platform.js``
and satisfies the registry contract (``OMNISYS_MODULES["platform"]``):
``info``/``os``/``arch``/``env``/``sleep_ms`` declare the ``process``
effect; ``now`` and ``capabilities`` are pure. Python always provides the
stdlib ``os``/``platform``/``time`` modules, so the process lane is always
available (``_HAS_PROCESS`` is the constant ``True`` and ``_RUNTIME`` is
``'python'``). The browser lane's device capabilities (``graphics``,
``camera``, ``microphone``) are reported by ``capabilities()`` but their
device access is a platform escape and is not ported.
"""

import os as _os
import platform as _platform
import sys
import time

from omnisys_core import panic

__all__ = [
    'info',
    'os',
    'arch',
    'env',
    'now',
    'sleep_ms',
    'capabilities',
]

_HAS_PROCESS: bool = True
_RUNTIME: str = 'python'


def info() -> dict[str, str]:
    """Return a map of this lane: os/arch/python/runtime strings."""
    return {
        'os': os(),
        'arch': arch(),
        'python': sys.version.split()[0],
        'runtime': _RUNTIME,
    }


def os() -> str:
    """Return the OS name as ``sys.platform`` ('win32', 'linux', 'darwin')."""
    return sys.platform


def arch() -> str:
    """Return the machine architecture (``platform.machine()``, e.g. 'AMD64')."""
    return _platform.machine()


def env(key: str, default: str = "") -> str:
    """Return the environment variable ``key``; return default (empty string) when unavailable."""
    value = _os.environ.get(key)
    if value is None:
        return default
    return value


def now() -> float:
    """Return the current time in milliseconds (float, mirrors ``Date.now()``)."""
    return time.time() * 1000


def sleep_ms(ms: float) -> float:
    """Busy-wait ``ms`` milliseconds (deterministic tiny sleeps) and return ``ms``."""
    end = now() + max(0, int(ms))
    while now() < end:
        pass
    return ms


def capabilities() -> list[str]:
    """Return the Python lane's capability list (always contains 'none')."""
    return ['none', 'process', 'filesystem', 'camera', 'microphone', 'graphics']
