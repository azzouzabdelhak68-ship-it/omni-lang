# RESULTS — Phase 5 Project 5.3: Application Diagnostics & Observability

## MODEL_RESULT

### Task Completion Status: ✅ COMPLETE

**Summary**: Built an instrumented in-memory settlement-dispatch workload (`source/diagnostics_app.omni`) that
1. Emits structured logs (`info`/`error` with field maps), metric counters (`rejected_total`, `accepted_total`) and a gauge (`queue_depth`), trace spans per dispatch, and `profile()` timing telemetry.
2. Reproduces a planted malfunction (off-by-one boundary comparison in the dispatch gate: `greater or equal` instead of `greater than`).
3. **Diagnoses from telemetry alone**: `diagnose()` reads `snapshot()`, scans error log records, extracts the rejected priority from each message via `split`/`to_number`, and confirms the boundary case (`priority == max_allowed`).
4. Applies the fix in-program (fixed gate), clears telemetry, re-runs, and reports verification (rejections drop 3 → 2, PASSED).
5. The emission path is **runtime-verified under Node**: a DOM-stub harness executes the emitted JS and asserts on the in-process snapshot (metric record→query round trip, trace begin/end pairing, log levels, remediation).

### Execution Efficiency
- `omni check`: exit 0 (all static analysis passes)
- `omni build` (target js): wrote `source/diagnostics_app.html`
- `omni verify`: batch schema, 12 functions, all `no-contracts`, exit 0
- `pytest`: **19 passed in 2.38s** (including 8 runtime tests under Node)
- `omni run`: full reproduce → diagnose → remediate → verify cycle executes end-to-end

### Invalid Assumptions Encountered
1. **`OMNISYS.core.to_text` exists** (brief said so): false — `E-NAME-001`; `core.js` has `to_number` but no `to_text`. Text coercion is implicit via `+`/`show`.
2. **TASK.md `BLOCKED` status is current**: false — `OMNISYS.observability` is registered and implemented (all 11 functions pure); the block is stale.
3. **Multi-line declarations/calls are fine**: false — struct type declarations, function calls, and struct constructions must each be single-line (`E-SYNTAX-001`).
4. **Function-local names may shadow module data**: false — a local plain-assignment that collides with an entry-point-assigned name triggers `E-EFFECT-004` (must rename the local).
5. **`show map` is a usable runtime assertion**: false — `show` stringifies maps to `[object Object]`; runtime assertions instead dump `snapshot()` via a harness epilogue.

---

## ECOSYSTEM_RESULT

### API Findings
| Aspect | Finding |
|--------|---------|
| **Module status** | `OMNISYS.observability` fully registered + implemented (`omnisys/observability.js`); TASK.md `BLOCKED` is stale |
| **Logging** | `log(Text, Text, Map)`, `info/warn/error(Text, Map)` — structured records `{level, message, fields, at}` in `logs[]` |
| **Metrics** | `metric(Text, Number)` (counter/gauge record), `metric_value(Text) -> Number` (0 for unknown) |
| **Tracing** | `trace_begin(Text) -> Number` (id), `trace_end(Number, Map)` fills `end`, `duration`, `fields` on the record |
| **Snapshot** | `snapshot() -> Map` with `{logs, metrics, traces}` (copies, not live refs) |
| **Profiling** | `profile(fn, Number) -> Number` accepts a zero-arg function **name** (no inline lambdas) |
| **Lifecycle** | `clear()` resets all collectors |

### Language Findings
| Aspect | Finding |
|--------|---------|
| **Pure-callable** | All 11 observability functions are `pure` — callable directly from `pure` functions with no capability declaration |
| **Map writes** | `m["k"] = v` is a syntax error; use `omnisys.collections.map_set(m, k, v)` |
| **Map/index reads** | `m["k"]` and nested chains `tr["fields"]["ok"]` work (plain JS objects) |
| **Module-scope collision** | A name assigned in `when app starts` is module data; plain-assigning it in a function body triggers `E-EFFECT-004` (loop variables and params are exempt) |
| **Single-line constructs** | Struct type decls, calls, and struct constructions are single-line only |
| **Coercion** | Implicit `Number`→`Text` in `+`/`show`; explicit `omnisys.core.to_number(Text)` exists; `to_text` does NOT |
| **Builtins** | `join`, `split`, `length`, `to_number`, `range` available; `verify` treats no-contract functions as `no-contracts` |

### Compiler Findings
| Aspect | Finding |
|--------|---------|
| **Effect system** | Observability is entirely capability-free (`_pure`), unlike `platform`/`fs`/`net` — simplest possible instrumentation story |
| **E-EFFECT-004 precision** | Only fires for entry-point-assigned names; diagnostics correctly identify the colliding resource and offer `writes` auto-fix |
| **E-SYNTAX-001** | Parser rejects multi-line type/struct/call layouts with trailing commas |
| **`build`/`verify`/`run`** | All reliable; `build` default target `js` emits self-contained HTML with inlined runtime |
| **Emitter** | `show` → `console.log`; entry wrapped in `batchUpdate(async fn)` but body runs synchronously when no `await` — snapshot is populated before script end |

### Diagnostic Findings
| Aspect | Finding |
|--------|---------|
| **Ecosystem diagnosability** | HIGH for this task — the compiler's own observability module is what the app instruments, and `snapshot()`/`metric_value()`/logs make the failure tractable end-to-end |
| **`omni run`** | Streams runtime output; verified the full diagnose cycle in one run |
| **`omni verify`** | Returns structured `omni.verify.batch` JSON — machine-parseable, exit 0 on no failures |
| **`omni check` diagnostics** | JSON schema with code/category/severity/span/fixes; auto-fix for `E-EFFECT-004` |
| **Gap** | No `omni trace`-style runtime step output for OMNISYS state; diagnosis relies on in-app telemetry interpretation |

### Capability/Effect Findings
- No capability is consumed by the entire observability surface — logging/metrics/tracing are effect-free by design, so instrumentation cannot be rejected by the effect checker.
- `profile(fn, Number)`'s `fn` parameter type is a bare `fn` (untyped); the checker accepts a declared function name.
- No `uses`/`reads`/`writes` declarations required anywhere in the instrumented app — a notable contrast to `OMNISYS.platform` (all `process`).

### Backend Findings
| Backend | Status |
|---------|--------|
| **JS lane (Node)** | Fully verified — in-process collector + snapshot survive emission; DOM-stub harness executes the whole diagnose cycle |
| **Native (C/WASM)** | `build --target c/rust/wasm-*` rejects programs that *call* `omnisys.*` (`E-BACKEND-001`); import-only programs may build. Observability is JS-lane-only |

### Documentation Findings
- `omnisys/observability.js` is self-documenting ("logging, metrics, tracing, profiling. In-process collector with a JSON snapshot").
- `omnisys_registry.py` is the authoritative signature source (`fn(Text, Text, Map) -> None`, etc.).
- TASK.md status metadata (`BLOCKED`, "Missing: OMNISYS.observability") is **stale and misleading** — should be corrected to reflect v6 shipping.
- No user-facing doc for the module; signatures discoverable only via registry source.

### Positive Discoveries
1. **Effect-free observability**: the entire telemetry API is pure — zero effect-declaration friction for instrumentation.
2. **Diagnosis is genuinely data-driven**: `split` + `to_number` on log messages yields the numeric root-cause signal; `snapshot()` makes correlation code-expressible.
3. **Runtime verifiability**: the emitted JS runs under Node with a DOM stub, and the in-process snapshot is reachable — metric round trip and trace pairing are testable end-to-end.
4. **Clean remediation loop**: `clear()` enables a within-program "reproduce → diagnose → fix → re-verify" cycle that ends with a machine-checkable PASSED/FAILED line.
5. **`map_set`/`map_get` fill the map-write gap** cleanly; nested map reads compose well for telemetry records.
6. **Compiler diagnostics carry auto-fixes** (e.g., `E-EFFECT-004` suggests the exact `writes` clause), which made the module-scope-collision rule quick to work around.

### Proposed Changes
| Priority | Change | Rationale |
|----------|--------|-----------|
| **HIGH** | Correct TASK.md 5.3 status metadata | `BLOCKED`/"Missing observability" is stale post-v6; misleads future benchmark runs |
| **HIGH** | Add `to_text`/`to_string` to `OMNISYS.core` | Brief assumed it exists; only `to_number` is implemented |
| **MEDIUM** | Allow multi-line calls/type decls/struct constructs | Single-line-only is a recurring ergonomic failure across projects (also seen in 5.5) |
| **MEDIUM** | Expose sub-ms `profile` fidelity or a duration-based metric API | `profile` returns 0 ms for tiny workloads |
| **LOW** | `snapshot()` deep-copy nested `fields` | Currently shallow-copies records; mutation of a returned field map would alias the collector |
| **LOW** | Document observability signatures in module README | Discoverability currently requires reading `omnisys_registry.py` |

---

## Verification Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| `omni check` passes | ✅ | Exit 0 |
| `omni build` succeeds | ✅ | target=js, wrote `source/diagnostics_app.html` |
| `omni verify` passes | ✅ | 12 functions, all `verified`/`no-contracts`, exit 0 |
| `pytest tests/` | ✅ | 19 passed in 2.38s |
| Structured logs/metrics/traces invoked | ✅ | Registry signatures + source instrumentation tests |
| Metric record→query round trip (runtime) | ✅ | `accepted_total=3`, `rejected_total=2`, `queue_depth=5` in snapshot |
| Trace begin/end pairing (runtime) | ✅ | 5 spans, all `end` set, 2 failed |
| Diagnosis root cause identified | ✅ | Boundary case confirmed from telemetry alone |
| Fix applied + verified | ✅ | Rejections 3 → 2, `verification: PASSED` |

---

## Files Produced

```
RUN_001_DEEPSEEK_V4_FLASH_FREE/
├── BENCHMARK_REASONING.md      # Observable investigation ledger
├── RESULTS.md                  # This dual-dimension summary
├── probes/                     # Minimal probes used to establish language facts
│   ├── probe_01.omni           #   observability shapes, maps, profile
│   ├── probe_02.omni           #   full API surface, structs, interpolation
│   ├── probe_03.omni           #   to_text absence (E-NAME-001)
│   └── probe_04.omni           #   telemetry interpretation patterns
├── source/
│   └── diagnostics_app.omni    # Instrumented, self-diagnosing workload (~240 lines)
└── tests/
    └── test_diagnostics_app.py # 19-test suite (compiler, API, runtime under Node)
```