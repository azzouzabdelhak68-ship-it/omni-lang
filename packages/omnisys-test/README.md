# OMNISYS.test

Python reference implementation of the `OMNISYS.test` module (v6 Phase 1):
assertions, deterministic property testing, and micro-benchmarking for the
OmniScript test surface.

## API

- `assert_true(cond, msg=None)` — panic unless `cond` is truthy.
- `assert_eq(actual, expected)` — canonical-JSON equality with a diagnostic panic.
- `assert_throws(fn)` — `True` when `fn()` raises any exception, else `False`.
- `property(prop, samples)` — deterministic LCG-driven property run (seed 12345, same sequence as JS).
- `bench(fn, iterations)` — elapsed wall-clock time in milliseconds.
- `fail(msg)` — always panics with the `test assertion failed: ` prefix.

## Dependencies

- `omnisys_core` — `panic` for assertion failures (registry `core.panic`).
- `omnisys_collections` — declared as a registry dependency (`js_deps`), not used at runtime.

All functions are pure; stdlib only (`json`, `time`). Failures raise
`omnisys_core.PanicError` via `panic`, mirroring the JS runtime.

See [`RESEARCH.md`](RESEARCH.md) for the design rationale, studied ecosystems,
and deviations from the JS reference.