"""Shared pytest bootstrap for the OMNISYS monorepo packages.

Adds each package's ``src/`` directory to ``sys.path`` so a package's tests can
import its own ``omnisys_*`` module and any sibling packages (deps) without a
prior ``pip install``. Harmless when the packages are already installed
editable.
"""

import sys
from pathlib import Path

_PACKAGES_ROOT = Path(__file__).resolve().parent

for _src in sorted(_PACKAGES_ROOT.glob('*/src')):
    _path = str(_src)
    if _path not in sys.path:
        sys.path.insert(0, _path)
