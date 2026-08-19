# Benchmark Task 1.4: Robust Multi-Step Data Processing Pipeline

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `require`/`ensure` contracts, runtime assertion panics, diagnostics.
- **Missing**: Typed error values, error context, stack traces, `ErrorId` (unlocks with `OMNISYS.error`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.error` ships in v6.
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

Build a robust multi-step data processing pipeline that classifies failures, enriches them with context, and recovers gracefully.

### Functional Requirements
1. **Multi-Step Pipeline**:
   - Implement a pipeline with distinct stages: input validation, transformation, aggregation, and output formatting.
   - Each stage can fail independently.
2. **Error Classification**:
   - Distinguish between expected errors (recoverable, input-driven), recoverable errors (transient), and fatal errors (abort the pipeline).
   - Represent failures as structured records with a stage, category, message, and input context.
3. **Context Enrichment**:
   - Attach the failing input and stage information to every error record.
   - Propagate context from inner stages to outer callers.
4. **Graceful Recovery**:
   - Skip inputs that produce expected errors and continue processing.
   - Abort cleanly with a classified final report when a fatal error occurs.
5. **Contract Enforcement**:
   - Declare preconditions on stage entry and postconditions on successful completion.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/pipeline.omni`**: Primary program implementing the robust pipeline.
3. **`tests/test_pipeline.py`**: Automated test suite verifying classification, recovery, and context propagation.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/pipeline.omni` exits with code 0.
- `omni run source/pipeline.omni` executes and outputs a processing report with classified failures.
- All tests in `tests/` pass.