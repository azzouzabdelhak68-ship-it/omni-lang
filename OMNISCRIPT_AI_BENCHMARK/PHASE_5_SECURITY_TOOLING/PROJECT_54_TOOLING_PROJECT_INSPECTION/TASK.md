# Benchmark Task 5.4: Compiler Tooling & Project Inspection

## Status Metadata
- **STATUS**: `PARTIAL`
- **Implemented**: `omni inspect symbol`, `omni explain error`, `omni find dependency`, `omni generate test`, `omni verify contract`, `omni trace execution`, `omni suggest fix`, `omni summarize module`; LSP server; machine-readable `omni.diagnostic` / `omni.symbol` schemas.
- **Missing**: `OMNISYS.tool` — full LSP/formatter/debugger/docgen/migration tool suite.
- **Benchmark purpose**: Discovery/limitation testing only — assesses the AI-native inspection surface with current tools.
- **Verified by**: `omni inspect`, `omni trace`, `omni generate`, `omni suggest`, LSP.

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

Given an unfamiliar OmniScript project, use the ecosystem's compiler inspection and diagnostic tooling to understand, explain, and improve it without being told the answer in advance.

### Functional Requirements
1. **Unfamiliar Project**:
   - An unfamiliar OmniScript codebase is provided (or reconstructed) with mixed-quality code including at least one latent bug and one effect-declaration issue.
2. **Inspection**:
   - Enumerate the symbols, their types, dependencies, and declared effects.
   - Produce a dependency map of the project.
3. **Diagnosis**:
   - Identify the latent bug and the effect-declaration issue through tooling.
   - Collect machine-readable diagnostics for each problem.
4. **Trace & Explain**:
   - Step through the critical function(s) and explain control flow.
   - Explain each error in plain language.
5. **Fix & Generate Tests**:
   - Apply fixes and draft tests for the corrected functions.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`INSPECTION_REPORT.md`**: Symbol inventory, dependency map, diagnostics, trace output, and explanations.
3. **`source/`**: The (corrected) project source.
4. **`tests/`**: Drafted and passing tests.
5. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to the AI-native tooling surface (discoverability, typed records, machine-readable output)**.

### Verification Criteria
- The effect-declaration issue is fixed and `omni check` passes.
- The latent bug is fixed and covered by a passing test.
- All inspection steps are documented in `INSPECTION_REPORT.md`.