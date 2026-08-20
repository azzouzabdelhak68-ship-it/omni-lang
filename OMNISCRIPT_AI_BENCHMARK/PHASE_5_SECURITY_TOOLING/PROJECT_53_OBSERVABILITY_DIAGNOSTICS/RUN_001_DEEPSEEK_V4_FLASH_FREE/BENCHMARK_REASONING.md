# BENCHMARK REASONING LEDGER — Phase 5 Project 5.3: Application Diagnostics & Observability

## 2026-08-19

## Initial Investigation

### Questions Investigated
- Is `OMNISYS.observability` really implemented (TASK.md says STATUS `BLOCKED` / "Missing")?
- What is the exact registered signature of every observability function?
- Are the functions `pure` (usable directly from `pure` functions) or do they require capability declarations?
- How are maps constructed and mutated in OmniScript, given `m["k"]=v` is a syntax error?
- Can `profile(fn, Number)` accept an existing function name (no inline lambdas)?
- Can the emitted JS actually run under Node so runtime telemetry is testable?
- What is the sibling project 5.5 run's file/test structure to mirror?

### Hypotheses & Assumptions
- TASK.md is stale and the module is actually present in `omnisys_registry.py` + `omnisys/observability.js`.
- All observability functions are pure (registry `_pure`), so pure functions may call them directly.
- `profile` takes a function name reference, not a lambda.
- Map index READ `m["k"]` works; map WRITE must go through `omnisys.collections.map_set`.
- The JS emitter inlines the OMNISYS runtime, and the entry point body runs synchronously (no awaits), so a Node + DOM-stub harness can assert on the final in-process snapshot.

### Files Inspected
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_5_SECURITY_TOOLING\PROJECT_53_OBSERVABILITY_DIAGNOSTICS\TASK.md` — mission brief (marked BLOCKED/stale).
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_5_SECURITY_TOOLING\PROJECT_55_NATIVE_INTEROP_ESCAPE_HATCH\RUN_001_CLAUDE_3_5\{TASK?, BENCHMARK_REASONING.md, RESULTS.md, source\native_interop_demo.omni, tests\test_native_interop.py}` — structure to mirror.
- `E:\simualtion\omni_compiler\omnisys_registry.py` — `observability` module registered with `log/info/warn/error/metric/metric_value/trace_begin/trace_end/snapshot/clear/profile`, all `_pure`.
- `E:\simualtion\omnisys\observability.js` — in-process collector: `logs[]`, `metrics{}`, `traces[]`, snapshot returns copies.
- `E:\simualtion\omnisys\core.js`, `E:\simualtion\omnisys\collections.js` — runtime for `length/is_empty/split/to_number`, `list_push`, `map_get/map_set/map_keys/map_size`.
- `E:\simualtion\omni_compiler\cli.py` — `check` (compile, exit 0 on OK), `run` (Node), `build` (js target default), `verify` (SMT contract batch).
- `E:\simualtion\omni_compiler\checker.py` — `BUILTIN_FUNCTIONS` (join/range/length/contains/starts_with/ends_with/substring/regex_match), E-EFFECT-004 module-data write rules.
- `E:\simualtion\omni_compiler\emitter.py` — OMNISYS runtime inlined dependency-ordered; `show` → `console.log`; functions as `function name(...)`; entry wrapped in `batchUpdate(async fn)`; `join` special-cased to `.join(sep)`.
- `E:\simualtion\tests\test_emitter.py` — `_run_emitted` DOM-stub harness pattern for Node runtime tests.

## Probe 1 — observability call shapes, map handling, profile

`probes/probe_01.omni`: metric round trip, `{"alpha": 5}` map literal + `m["alpha"]` index read, `map_set`/`map_get`/`map_size`, `info(Text, Map)`, `trace_begin/trace_end`, `snapshot()`, `clear()`, `profile(busy_work, 100)`.

### Error: E-EFFECT-004 on `timed_span`
```
{
  "code": "E-EFFECT-004",
  "message": "Module data 'tid' accessed via writes without declaration.",
  "details": "timed_span writes 'tid' but does not declare it."
}
```
Interpretation: `when app starts` also assigns `tid = timed_span(...)`, so `tid` is module-scope data; reusing the name as a function-local (non-loop) variable makes the function appear to WRITE module data. Renamed the local to `span_id` → check passed.
**Discovered rule**: a name assigned anywhere in the entry point becomes module data; function bodies may only shadow it via parameters or loop variables (`_loop_vars_ast`), not plain assignments (see checker.py `_walk_data_access`).

### Probe 1 check + run (raw output)
```
omni check: OK  probe_01.omni   (exit 0)
omni run probe_01.omni:
map read: 5
map_get gamma: 7
map_size: 3
metric roundtrip: 41
snap logs len: 1
snap metrics count: 41
trace id: 1
trace_count: 0        <- MY probe ordering bug: snapshot taken BEFORE timed_span
profile ms: 0
after clear logs len: 0
```
Notes: `trace_count: 0` is expected — the snapshot was captured before the span was recorded; this confirmed snapshot reflects live in-process state. `profile(busy_work, 100)` accepted an existing function name and returned a duration.

## Probe 2 — full API surface + structs + interpolation

`probes/probe_02.omni`: 3-arg `log(level, msg, map)`, `warn`, `error`, struct `TaskEvent` construction + field access inside a pure function, trace begin/end, `join`, `split()[1]`, `{var}` interpolation, snapshot shape (logs/metrics/traces), missing metric → 0.

```
omni check: OK  probe_02.omni   (exit 0)
omni run probe_02.omni:
recorded: t-42
logs: 4
traces: 2
tasks_total: 10
missing_metric_defaults_to_0: 0
joined: a,b,c
len: 5
split2: y
interp: Hello, bob
snapshot logs: 4
snapshot metrics keys: 3
snapshot traces: 2
```

## Probe 3 — `to_text` (brief claimed it exists)

```
omni check probe_03.omni:
E-NAME-001: Undefined variable or function 'omnisys.core.to_text'
```
**Discovered**: `OMNISYS.core.to_text` does NOT exist (brief stale; `core.js` has `to_number` but no `to_text`). Text coercion is implicit via `+` concatenation and `show`.

## Probe 4 — telemetry interpretation patterns (diagnosis building blocks)

Iterate snapshot log records (`entry["level"]`, `entry["message"]`), nested map index chains (`tr["fields"]["ok"] is false`), `split` + `to_number` to extract a numeric priority from an error message.

```
omni check: OK  probe_04.omni   (exit 0)
omni run probe_04.omni:
error logs: 2
first msg: REJECTED priority 4
failed traces: 1
extracted priority: 3
```

## Decisions

1. **App design**: an in-memory settlement-dispatch workload (`DispatchTask` list, priorities 1..5, max_allowed=3) with a planted off-by-one gate bug (`greater or equal` instead of `greater than`) so that telemetry genuinely isolates the root cause: a rejection log at exactly `priority == max_allowed`.
2. **Diagnosis must be data-driven**: `diagnose(max_allowed)` reads `snapshot()`; scans error logs, extracts each rejected priority via `split(" ")` + `to_number`, and confirms the boundary case by testing `extracted == max_allowed` — not hardcoded output.
3. **Remediation in-program**: run the buggy gate (phase 1) and the fixed gate (phase 3, after `clear()`), compare rejection counts, and print a PASSED/FAILED verification line.
4. **Telemetry coverage**: counters `rejected_total`/`accepted_total` via a `bump_counter` helper, gauge `queue_depth` via `set_gauge`, structured `info`/`error` logs with field maps, `trace_begin/trace_end` spans per dispatch, and `profile(bench_loop, 500)` timing.
5. **Runtime verification strategy**: mirror `tests/test_emitter.py::_run_emitted` (Node + DOM stub), but add an epilogue that dumps `omnisys.observability.snapshot()` as JSON. Because the entry point runs synchronously (no awaits, no network effects), the snapshot is fully populated when `runInThisContext` returns.

### Alternatives considered & rejected
- **Hardcoded diagnosis** (print the known failing priority): rejected — would not demonstrate telemetry interpretation.
- **Inline lambdas for `profile`**: rejected — not supported; pass an existing zero-arg `bench_loop` function instead.
- **Using `show snapshot_map`**: rejected — `show` stringifies maps to `[object Object]`; runtime assertions use the snapshot epilogue instead.
- **A 4-arg structured result pattern / custom Result type**: rejected — sibling 5.5 showed field access on function returns of custom types is blocked (E-TYPE-002); a flat `DiagnosticReport` struct held in a local variable works and is read field-by-field in the entry point.

## Compiler friction encountered & workarounds

| Friction | Diagnostic | Workaround |
|---|---|---|
| Local var name collides with entry-point (module-scope) name | E-EFFECT-004 | Rename function locals to names never assigned in `when app starts` |
| Multi-line struct type declaration | E-SYNTAX-001 (`Expected IDENTIFIER, got RBRACE`) | Declare `type X = { a: A, b: B }` on one line |
| Multi-line function call / struct construct | E-SYNTAX-001 (`Unexpected token RPAREN`) | Every call/construction on one line |
| `omnisys.core.to_text` missing | E-NAME-001 | Rely on implicit `+`/`show` coercion; `to_number` exists for parsing |
| `m["k"] = v` map write | syntax error (known) | `omnisys.collections.map_set(m, k, v)` |

## Language rules confirmed by probes
- OMNISYS calls are emitted as `omnisys.<module>.<fn>(...)`; runtime is inlined dependency-ordered by the JS emitter.
- Map literals `{k: v}` work; reads via `m["k"]` or `map_get`; nested chains like `tr["fields"]["ok"]` work (maps are plain JS objects).
- `is`/`is not` compare values; `for x in list:` iterates snapshot arrays; loop variables may shadow module scope without `writes`.
- `profile(fn, Number)` accepts a declared function name (zero-arg) and returns elapsed ms.
- `verify` reports `no-contracts` for functions without require/ensure; batch schema `omni.verify.batch`, exit 0 when no failures.
- `build` default target `js` writes `<stem>.html`; exit 0.
- `run` executes via `scripts/run-omnisys.js` + Node, streaming `console.log` output; `show` → `console.log`.

## Final verification (raw outputs)
```
python -m omni_compiler.cli check source/diagnostics_app.omni  -> "omni check: OK  diagnostics_app.omni"  (exit 0)
python -m omni_compiler.cli build source/diagnostics_app.omni  -> "omni build: wrote source\diagnostics_app.html (target=js)"  (exit 0)
python -m omni_compiler.cli verify source/diagnostics_app.omni -> omni.verify.batch, 12 functions, all "no-contracts"  (exit 0)
python -m pytest tests/ -q  -> 19 passed in 2.38s  (exit 0)
```

### `omni run source/diagnostics_app.omni` (final app)
```
queued tasks: 5
gauge queue_depth: 5
phase1 buggy rejected: 3
phase1 error logs: 3
phase1 failed traces: 3

=== DIAGNOSIS ===
symptoms: failed=3 ok=2 error_logs=3 failed_traces=3
evidence: error logs contain a rejection at priority 3 == max_allowed: true
root_cause: boundary case confirmed: priority == max_allowed wrongly rejected by `greater or equal`
remediation: replace `greater or equal` with `greater than` in the dispatch gate
verification: fixed gate must reject only priorities above max_allowed

=== REMEDIATION CHECK ===
phase3 fixed rejected: 2
phase3 error logs: 2
phase3 failed traces: 2
verification: PASSED — rejections dropped from 3 to 2

profile bench_loop x500: 72 ms
=== Diagnostics App Complete ===
```

### Verification criteria (completed)
- `omni check` exit 0 — PASSED
- `omni build` success — PASSED
- `omni verify` all `verified`/`no-contracts` — PASSED (12/12 no-contracts)
- pytest — 19/19 PASSED (incl. Node runtime telemetry assertions: metric round trip `accepted_total=3/rejected_total=2`, 5 paired traces with 2 failed, info+error log levels, remediation verification)
- Diagnosis workflow recorded — PASSED (probes + final run above)

## Unresolved questions
- `snapshot()` returns JS `null` vs Python `None` interop when values come back from index reads — not needed for this task, unverified.
- `profile` timing resolution: returns 0 ms for tiny workloads under Node; no sub-ms fidelity guarantees documented.
- Whether `trace_end` on an unknown id silently no-ops (observability.js `find` guard) — behavior observed, not stress-tested.