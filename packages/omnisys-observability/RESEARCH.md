# OMNISYS.observability — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/observability.js` and the compiler registry
`OMNISYS_MODULES["observability"]`.

## 1. Ecosystems studied

- **OpenTelemetry** — the de-facto observability standard: logs, metrics,
  spans, and exporters. Kept conceptually: an in-process collector with a
  uniform snapshot.
- **Python `logging`** — the stdlib structured-logging story; more rigid
  (handlers/formatters/levels as classes).
- **Prometheus** — metrics as a name → number collector; mirrored directly by
  `metric`/`metric_value`.
- **Tracing SDKs (OpenTelemetry, Datadog)** — span begin/end with duration
  and fields; mirrored by `trace_begin`/`trace_end`.

## 2. What was adopted

- One module-level state object with `logs`, `metrics`, `traces`,
  `nextTrace` — matching the JS lane exactly.
- `log` entries `{level, message, fields, at}`; `at` as epoch ms float
  (`time.time() * 1000`; JS `Date.now()`).
- Metrics coerced `String(name)` / `Number(value)`; unknown `metric_value`
  returns `0` (JS `undefined || 0`).
- Trace spans with incrementing integer ids, closed by id with `duration`.
- `snapshot` returning top-level copies so callers cannot corrupt the
  collector (JS `slice()` + `Object.assign`).
- `profile(fn, iterations)` with `Math.max(1, iterations | 0)` clamping.

## 3. Strengths / weaknesses of the studied ecosystems

- OpenTelemetry: complete, standardized; heavy SDK surface, exporter
  coupling.
- Python logging: battle-tested; sink-oriented, not snapshot-oriented.
- Prometheus: trivial metric model; no spans/logs.
- Tracing SDKs: rich spans; vendor-bound.

## 4. Performance

- Append-only lists/dicts; `trace_end` is O(traces) linear find (JS
  `Array.find`). `snapshot` copies logs/metrics/traces top-level — O(n).
  `profile` runs the callback n times with a wall-clock ms delta.

## 5. Type-system interaction / portability

- Registry types: `fn(Text, Text, Map) -> None`, `fn(Text, Number) -> None`,
  `fn(Text) -> Number`, `fn() -> Map`, `fn(fn, Number) -> Number`. Python
  types use `LogEntry`/`TraceEntry`/`Snapshot` aliases over `dict[str, Any]`.
- `profile`'s callback is typed `Callable[[], Any]`.

## 6. Lifecycle / error / concurrency model

- Single mutable `_state`; functions are otherwise pure (registry declares
  zero effects). No panics and no exceptions. Not thread-safe (matching the
  single-threaded JS model); the snapshot idiom makes it safe to read state
  for export.

## 7. AI usability

- One `snapshot()` call returns the full observability picture as JSON — an
  agent can emit logs/metrics/spans and then inspect a consistent snapshot
  directly, no runtime or daemon required.

## 8. Interop requirements

- Future escapes: OTLP/OpenTelemetry exporters, Prometheus endpoints, file
  log sinks — all consume the same `snapshot` model.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/observability.js`) | Python (this package) | Reason |
|---|--------------------------------|-----------------------|--------|
| 1 | `Date.now()` (ms integer) | `time.time() * 1000` (ms float) | Same ms scale, Python-native clock |
| 2 | `iterations \| 0` bitwise truncate | `int(iterations)` | Same for integral inputs |
| 3 | `trace.find(...)` returns undefined → silent no-op | loop + early `return` | Same observable behavior |
| 4 | `profile` returns `Date.now()` diff (integer) | float ms diff | Same scale; sub-ms precision is a bonus |

## 10. Verification

- `python -m pytest packages/omnisys-observability/tests -q -W error` — all
  tests pass, zero warnings.
- Coverage: `packages/omnisys-observability/src` **100% branch**.
- `mypy --strict packages/omnisys-observability/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-observability` —
  clean.