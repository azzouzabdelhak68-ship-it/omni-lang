# Benchmark Task 4.4: Native System Utility with Portable Fallbacks

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `process` capability vocabulary, effects enforcement, escape-hatch architecture (documented).
- **Missing**: `OMNISYS.platform` — native OS APIs, portable abstraction layer, backend-specific escape hatches.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.platform` ships in v6.
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

Implement a native system utility that uses platform-specific OS functionality while providing a portable abstraction layer with fallbacks.

### Functional Requirements
1. **Portable Abstraction**:
   - Define a portable capability interface for the utility's core operation.
   - Implement the same operation across multiple platform backends.
2. **Native Escape Hatch**:
   - Where the portable API is insufficient, access platform-native functionality explicitly.
   - Preserve type and error boundaries when crossing into native code.
3. **Fallback Behavior**:
   - Detect platform support at runtime and degrade gracefully with a clear status when a feature is unavailable.
4. **Capability Declaration**:
   - Declare any process/platform capabilities used at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/system_utility.omni`**: Primary program implementing the utility.
3. **`tests/test_system_utility.py`**: Automated test suite verifying portable fallback and native-boundary behavior.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/system_utility.omni` exits with code 0.
- All tests in `tests/` pass.