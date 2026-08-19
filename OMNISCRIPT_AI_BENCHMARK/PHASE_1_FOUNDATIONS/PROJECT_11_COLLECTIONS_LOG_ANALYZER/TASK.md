# Benchmark Task 1.1: Log Analysis & Data Processing Engine

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: `List` collections, iteration, core arithmetic, functions, text interpolation.
- **Missing**: `Map`, `Set`, `Deque`, structured collection APIs (unlocks with `OMNISYS.collections`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.collections` ships in v6.
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

Implement a log analysis and data-processing engine that ingests structured log records, filters by severity and source, aggregates statistics, and produces summary reports.

### Functional Requirements
1. **Log Record Model**:
   - Represent log entries with timestamp, severity level, source component, and message text.
2. **Collection Operations**:
   - Ingest collections of log records and filter by severity threshold.
   - Group and count records by source component.
   - Aggregate statistics: total entries, error rate, per-source counts, deduplicated message count.
3. **Sorting & Ordering**:
   - Order filtered records by severity, then by timestamp.
   - Provide top-N reporting of busiest components.
4. **Summary Output**:
   - Build a formatted multi-line summary report from the aggregation results.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/log_analyzer.omni`**: Primary program implementing the log analysis engine.
3. **`tests/test_log_analyzer.py`**: Automated test suite verifying filtering, aggregation, and reporting.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/log_analyzer.omni` exits with code 0.
- `omni run source/log_analyzer.omni` executes and outputs the summary report.
- All tests in `tests/` pass.