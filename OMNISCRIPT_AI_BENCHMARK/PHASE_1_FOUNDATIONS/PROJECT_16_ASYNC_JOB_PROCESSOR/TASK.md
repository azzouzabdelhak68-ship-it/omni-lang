# Benchmark Task 1.6: Concurrent Job Processing Engine

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, functions, loops, effects enforcement.
- **Missing**: `Task`, `Future`, `Stream`, `Channel`, `Select`, `Timeout`, cancellation (unlocks with `OMNISYS.async`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.async` ships in v6.
- **Verified by**: `omni check`, `omni run`.

---

## Investigation Requirement & Reasoning Instructions

Before implementing the project, investigate the OmniScript compiler and establish the language rules necessary for this task.

Do not assume that OmniScript follows conventions from another programming language.

When uncertain, investigate the repository, construct a minimal probe, inspect compiler behavior, or write a focused test.

Create `RUN_xxx_<MODEL_NAME>/BENCHMARK_REASONING.md` inside a dedicated run directory (e.g., `RUN_001_CLAUDE_3_5/BENCHMARK_REASONING.md`) at the beginning of the task.

Continuously record your explicit, observable investigation throughout implementation:
- Questions currently being investigated
- Initial hypotheses and assumptions
- Files, documentation, and compiler source inspected
- Probes and experimental source files created
- Compiler commands executed and raw outputs
- Errors encountered and your interpretation
- Architectural and code decisions made
- Alternative approaches considered and rejected
- Failed approaches and corrections
- Discovered language rules and compiler behaviors
- Unresolved questions and verification results

**Do not retrospectively rewrite or polish the reasoning history after completion.** The purpose of this file is to preserve the actual observable decision trajectory of the implementation process.

---

## Behavioral Mission Brief

Implement a concurrent job processing engine that schedules tasks, coordinates results, enforces timeouts, and supports cancellation.

### Functional Requirements
1. **Job Model**:
   - Represent jobs with inputs, priority, expected duration class, and result slots.
2. **Scheduling & Concurrency**:
   - Dispatch independent jobs concurrently while serializing dependent jobs.
   - Coordinate fan-in: collect results from many concurrent jobs into one aggregated result.
3. **Timeouts & Cancellation**:
   - Enforce per-job time limits; classify timed-out jobs distinctly.
   - Support cooperative cancellation of a job in progress.
4. **Streaming & Selection**:
   - Process jobs as a continuous stream of events.
   - Select among multiple concurrent sources of completion (first-completed, any, all).
5. **Effect Declarations**:
   - Declare any external side-effects (e.g. logging, network) explicitly at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/job_processor.omni`**: Primary program implementing the concurrent engine.
3. **`tests/test_job_processor.py`**: Automated test suite verifying scheduling, timeout, cancellation, and result aggregation.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/job_processor.omni` exits with code 0.
- `omni run source/job_processor.omni` executes and prints an aggregated job report.
- All tests in `tests/` pass.