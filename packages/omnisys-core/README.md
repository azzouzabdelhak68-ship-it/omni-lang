# OMNISYS.core

**OMNISYS.core** is the implicit root module of the OMNISYS platform —
`import OMNISYS` resolves to it. It provides the portable Option/Result
wrappers, math helpers, length helpers, and the panic abort used by every
other module.

## Python lane

```python
import omnisys_core
from omnisys_core import panic, PanicError

opt = omnisys_core.some(42)
res = omnisys_core.ok('value')
assert omnisys_core.is_some(opt)
assert omnisys_core.is_ok(res)
```

This package is the Python reference implementation of the JS runtime in
`omnisys/core.js`. Function names, semantics, and tagged-value shapes match
the registry contract in `omni_compiler/omnisys_registry.py`.

## Dependencies

None (foundational — every other package depends on this one).

## Docs

- [RESEARCH.md](RESEARCH.md) — research gate + design decisions
- [tests/](tests/) — unit, property, and registry-conformance tests