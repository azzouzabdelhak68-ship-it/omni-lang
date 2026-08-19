"""Test bootstrap: expose the reference ``panic``/``PanicError`` on ``omnisys_core``.

``omnisys_test`` imports ``panic`` from ``omnisys_core`` per the registry
contract, but the OMNISYS.core package is still a placeholder in this
monorepo. This seam installs the reference behaviour on the imported module
only when the sibling package does not provide it yet, so the tests run
against the documented contract regardless of which lane is implemented.
"""

from __future__ import annotations

import omnisys_core


class PanicError(RuntimeError):
    """Raised by the reference ``panic`` to abort a test run."""


def _panic(msg: str) -> None:
    raise PanicError(msg)


if not hasattr(omnisys_core, 'panic'):
    omnisys_core.panic = _panic

if not hasattr(omnisys_core, 'PanicError'):
    omnisys_core.PanicError = PanicError
