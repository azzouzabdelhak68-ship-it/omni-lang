# Benchmark Task 5.3: Application Diagnostics & Observability

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, diagnostics (`omni explain`, `omni suggest`), `omni trace` step debugger.
- **Missing**: `OMNISYS.observability` — logging, metrics, tracing, profiling infrastructure.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.observability` ships in v6. Tests the AI's ability to debug the ecosystem, not just generate code.
- **Verified by**: `omni check`, `omni trace`, `omni explain`.

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

You are given a production-like application that is malfunctioning. Diagnose the failure, isolate the root cause, and produce a remediation report using instrumentation and inspection tools available in the ecosystem.

### Functional Requirements
1. **Instrumented Application**:
   - Construct (or reconstruct) a small production-like application with observable logging and metrics instrumentation around its critical path.
2. **Diagnosis**:
   - Reproduce the malfunction.
   - Identify the failing component, the triggering condition, and the propagation path.
3. **Telemetry Interpretation**:
   - Collect logs, timing/metrics, and error records during the failure.
   - Correlate telemetry to pinpoint the root cause.
4. **Remediation Report**:
   - Produce a structured report: symptoms, evidence collected, root cause, fix applied, verification result.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/`**: The instrumented application and any diagnostic harness.
3. **`DIAGNOSIS_REPORT.md`**: Structured remediation report (symptoms, evidence, root cause, fix, verification).
4. **`tests/`**: Tests covering the fix.
5. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to how diagnosable the ecosystem is**.

### Verification Criteria
- The root cause is identified with supporting evidence.
- The fix is applied and verified by tests.
- The diagnosis workflow (trace/explain) is recorded in the report.