# Benchmark Reasoning: PROJECT_16_ASYNC_JOB_PROCESSOR

## Investigation Log

### Initial Probe: OMNISYS.async Module Availability (2026-08-18)

**Question**: Does `import OMNISYS.async` work in OmniScript?

**Files inspected**: 
- `omni_compiler/omnisys_registry.py` — defines `async` module with functions: task, delay, all, race, any, timeout, channel, channel_send, channel_recv, is_promise (all declared `pure`)
- `omni_compiler/checker.py:460` — allows `sim.*` without import; other OMNISYS modules require explicit import
- `omnisys/async.js` — Promise-based implementation returning Task/Promise objects

**Probe executed**: `probe_async.omni` and `probe_async2.omni`

**Results**:
- `omni check` passes for both probes → async module IS recognized when imported
- `omni run` shows all async operations return `[object Promise]` / `object` type
- Channel send/recv return Promises, not direct values
- No automatic await in synchronous OmniScript runtime

**Conclusion**: The async module type-checks but **cannot be used for real concurrency** because:
1. All async functions return Promise/Task objects
2. OmniScript runtime is synchronous — no `await` keyword exists
3. Promises are opaque objects; cannot extract values synchronously
4. Channel communication deadlocks (send returns Promise, recv returns Promise, neither resolves synchronously)

### Syntax Discovery: Struct Construction (2026-08-18)

**Files inspected**: `omni_compiler/parser.py:616-627`

**Finding**: Struct construction uses `TypeName(field=value, ...)` syntax, NOT `{field=value, ...}`. The `{...}` syntax is only for type declarations (`type T = { f: Type }`).

**Error in existing `job_processor.omni`**: Line 58 uses `{id=id, input=input, ...}` which fails with "Unexpected token '{'".

### Architecture Decision

**Given**: True async/concurrency impossible in current OmniScript.

**Strategy**: Implement a **synchronous model** of the job processor that:
- Represents jobs, workers, queues, timeouts, cancellation as data structures
- Simulates scheduling, fan-in, timeout classification, cancellation as pure data transformations
- Uses `sim.*` for any runtime effects (timing, logging)
- Declares effects honestly (`pure` for pure functions, `uses process` for simulated work)
- Documents the async blockage in `BENCHMARK_REASONING.md` and `RESULTS.md`

## Implementation Plan

### Job Model (synchronous records)
```omniscript
type Job = { id: Text, input: any, priority: Number, duration_class: Text, timeout_ms: Number, status: Text, result: any, error: Text }
type JobResult = { job_id: Text, status: Text, output: any, error: Text, duration_ms: Number }
type AggregatedReport = { total_jobs: Number, completed: Number, failed: Number, timed_out: Number, cancelled: Number, total_duration_ms: Number, results: List }
```

### Synchronous Scheduler Functions
1. `dispatch_jobs(jobs: List, worker_count: Number) -> List` — simulates concurrent dispatch by sorting by priority and "executing" sequentially
2. `execute_with_timeout(job: Job, timeout_ms: Number) -> JobResult` — classifies timeout based on duration_class vs timeout_ms
3. `cancel_job(job_id: Text, jobs: List) -> List` — marks job as cancelled
4. `fan_in(results: List) -> AggregatedReport` — aggregates results
5. `classify_timeout(duration_class: Text, timeout_ms: Number) -> Text` — pure timeout classification

### Effect Declarations
- Pure functions: `pure` (job creation, sorting, classification, aggregation)
- Simulated execution: `uses process` (for `omnisys.platform.now`, `omnisys.platform.sleep_ms`)

### Entry Point
`when app starts:` drives the synchronous scheduler and prints aggregated report.

---

## What Would Be Needed for True Concurrency (Compiler Changes)

1. **Await/async syntax** in OmniScript parser and type checker
2. **Promise unwrapping** in the JS emitter — convert `omnisys.async.task` calls to `await` expressions
3. **Runtime support** for Promise resolution in the entry point (make `when app starts:` async)
4. **Channel select/race** primitives with synchronous blocking semantics
5. **Effect system extension** to track async boundaries (`uses async` capability)

---

## Revised Implementation Strategy (Synchronous)

Replace all `omnisys.async.*` calls with pure data transformations:

| Async Concept | Synchronous Model |
|--------------|-------------------|
| `channel` (queue) | `List` with push/pop |
| `task(fn)` | Direct function call `fn()` |
| `timeout(task, ms)` | Compare `duration_class` to `timeout_ms`, return timeout status |
| `all([tasks])` | Map over list, collect all results |
| `race([tasks])` | Return first result (simulated by shortest duration) |
| `channel_send/recv` | List append/shift |
| Cancellation | Filter/update job status in list |

This models the **concurrency concepts** as data flow without actual parallelism.