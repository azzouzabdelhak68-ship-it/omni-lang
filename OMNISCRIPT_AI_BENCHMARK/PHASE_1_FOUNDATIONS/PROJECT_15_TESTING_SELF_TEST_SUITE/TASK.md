# Benchmark Task 1.5: Meta-Benchmark — Testing & Self-Test Suite

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `omni generate` (pytest template generation), generated hypothesis property tests.
- **Missing**: First-class assertions, property testing, mocking, benchmarking APIs in the language (unlocks with `OMNISYS.test`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.test` ships in v6.
- **Verified by**: `omni check`, `omni generate`, `pytest`.

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

**Meta-benchmark.** Select one completed prior project from Phase 0 (e.g. the Unit Converter or Todo Engine). Author a complete, high-quality test suite for it demonstrating the language's testing expectations.

### Functional Requirements
1. **Unit Tests**:
   - Cover every public function with explicit input/output assertions.
   - Include boundary cases (zero, negatives where valid, empty collections, single-element collections).
2. **Property-Based Tests**:
   - Express invariant relationships across generated inputs (e.g. conversion round-trip properties, aggregation correctness).
3. **Mocking / Isolation**:
   - Isolate functions with declared side-effects from pure logic during testing.
4. **Performance / Benchmark**:
   - Provide a repeatable timing harness for the core computational path.
5. **Tooling Integration**:
   - Use the compiler's test-generation assistance where available and record the outcome.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`tests/`**: The complete test suite (unit, property, mock, bench) for the chosen prior project.
3. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to how naturally the language supports its own testing**.

### Verification Criteria
- The referenced prior project passes `omni check`.
- The authored test suite runs green via `pytest`.
- Test generation tooling output (if any) is recorded and evaluated.