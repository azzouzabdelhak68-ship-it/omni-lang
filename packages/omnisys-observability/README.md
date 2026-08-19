# OMNISYS.observability

Python reference implementation of the OMNISYS `observability` module:
logging, metrics, tracing, and profiling as an in-process collector with a
JSON snapshot. Portable; no external I/O.

- **Registry**: `OMNISYS_MODULES["observability"]` — 11 functions, all pure.
  `js_deps` = `("core", "collections")`.
- **Import**: `from omnisys_observability import log, info, warn, error,
  metric, metric_value, trace_begin, trace_end, snapshot, clear, profile` —
  add `packages/omnisys-observability/src` to `PYTHONPATH`, or rely on the
  monorepo `packages/conftest.py` bootstrap.
- **State**: one module-level collector: logs (list), metrics (name → float),
  traces (list of open/closed spans), nextTrace (counter). `clear()` resets
  all of it.
- **Semantics**: mirrors `omnisys/observability.js` — `log` appends
  `{level, message, fields, at}` (ms float timestamp); `info`/`warn`/`error`
  set the level; `metric` coerces name to text and value to float;
  `metric_value` returns `0` for unknown names; `trace_begin` returns an
  incrementing id and pushes an open span; `trace_end` closes the span and
  records `duration` (no-op for unknown ids); `snapshot` returns
  `{logs, metrics, traces}` with top-level copies; `profile` runs `fn`
  `max(1, int(iterations))` times and returns elapsed ms.
- **Note**: shipping logs to an external sink (log transport, OTLP) is a
  documented escape; this is the in-process collector surface.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.