# Benchmark Task 1.2: Filesystem Synchronizer & File Organizer

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `filesystem` capability vocabulary, effects enforcement.
- **Missing**: `Path`, `File`, `Dir`, `Watch`, `Temp`, atomic write APIs (unlocks with `OMNISYS.fs`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.fs` ships in v6.
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

Implement a directory synchronization and file organization utility that computes file-system changes, applies them safely, and enforces capability policy.

### Functional Requirements
1. **Path & Directory Model**:
   - Represent filesystem paths and directory trees in memory.
2. **Sync Planning**:
   - Compare two directory trees and compute a change plan: files to create, update, delete, or skip.
   - Order operations to avoid conflicts (directories before children, deletes after copies).
3. **Safe Write Operations**:
   - Stage changes before commit and perform writes atomically where possible.
   - Preserve file contents on any partial failure.
4. **Organization Rules**:
   - Apply naming/extension-based organization rules to sort files into categorized subdirectories.
5. **Capability Policy**:
   - Declare all filesystem capabilities used at function boundaries; pure planning functions must remain side-effect-free.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/file_organizer.omni`**: Primary program implementing the sync/organize utility.
3. **`tests/test_file_organizer.py`**: Automated test suite verifying change-plan computation and ordering.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/file_organizer.omni` exits with code 0.
- `omni run source/file_organizer.omni` executes and prints a valid change plan.
- Effect declarations pass the semantic checker (no undeclared capabilities).