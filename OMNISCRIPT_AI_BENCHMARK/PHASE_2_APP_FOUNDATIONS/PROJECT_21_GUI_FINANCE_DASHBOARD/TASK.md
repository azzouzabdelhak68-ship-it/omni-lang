# Benchmark Task 2.1: Interactive Finance Dashboard Application

## Status Metadata
- **STATUS**: `PARTIAL`
- **Implemented**: HTML `UI:` block with `{...}` live slots, `click="..."` actions, live-link batching, JS/HTML build.
- **Missing**: First-class navigation, form widgets, tables, charts, reactive state primitives (unlocks with `OMNISYS.ui`).
- **Benchmark purpose**: Discovery/limitation testing only — assesses how far the current UI model goes and what is missing.
- **Verified by**: `omni check`, `omni build --target js`, browser smoke test.

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

Implement a personal finance dashboard application: an interactive graphical application with navigation, data entry, tabular summaries, filtering, and responsive state updates.

### Functional Requirements
1. **Data Model**:
   - Represent financial transactions with date, category, amount, and description.
   - Maintain an account balance and per-category summaries.
2. **Navigation & Views**:
   - Provide distinct views: overview summary, transaction list, and category breakdown.
   - Support switching between views through user interaction.
3. **Forms & Validation**:
   - Provide a transaction entry form with input validation (positive amounts, non-empty category, valid date).
4. **Tables & Filtering**:
   - Render transactions as a table.
   - Filter transactions by category and by date range.
5. **Reactive State**:
   - When state changes (new transaction, filter applied), the visible summary and table MUST update automatically without reload.
6. **Empty & Error States**:
   - Show a distinct empty state when no transactions match.
   - Show a distinct error state when invalid data is submitted.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/finance_dashboard.omni`**: Primary program implementing the dashboard.
3. **`tests/test_finance_dashboard.py`**: Automated test suite verifying state transitions, filtering, and validation logic.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to the semantic UI model and live-binding behavior**.

### Verification Criteria
- `omni check source/finance_dashboard.omni` exits with code 0.
- `omni build source/finance_dashboard.omni --target js` produces a runnable HTML artifact.
- State updates propagate to visible output without reload (live-link behavior).
- All tests in `tests/` pass.