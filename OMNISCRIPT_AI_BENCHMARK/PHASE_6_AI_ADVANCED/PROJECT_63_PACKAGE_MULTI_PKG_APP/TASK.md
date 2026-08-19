# Benchmark Task 6.3: Multi-Package Application & Dependency System

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language (single-file), `import` reserved for future versions, `import OMNISYS` model (documented in v6 §17.2).
- **Missing**: `OMNISYS.pkg` — package manager, registry, resolver, multi-file imports, lazy loading, versioning, dead-code elimination.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.pkg` ships in v6. Validates the `import OMNISYS` model and unused-subsystem elimination.
- **Verified by**: `omni check`, `omni build --target js`.

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

Implement a multi-module application split across packages, with explicit dependency relationships, and validate that unused subsystems can be excluded from the build.

### Functional Requirements
1. **Package Layout**:
   - Define at least three packages with clear responsibilities and dependency edges (e.g. `core`, `parser`, `app`).
2. **Imports & Boundaries**:
   - Import functionality across package boundaries.
   - Enforce that packages only access exported surfaces of their declared dependencies.
3. **Dependency Resolution**:
   - Resolve the dependency graph transitively and deterministically.
4. **Versioning**:
   - Model package versions and require compatible version selection.
5. **Unused-Subsystem Elimination**:
   - Demonstrate that importing the umbrella namespace does NOT force unused subsystems into the build artifact.
   - Show the built artifact omits an unused package/subsystem.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/` + `packages/`**: The multi-package application.
3. **`tests/`**: Tests covering cross-package behavior and dependency resolution.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to the `import OMNISYS` model and unused-subsystem elimination**.

### Verification Criteria
- `omni check` passes on the umbrella app.
- The build artifact demonstrably excludes an unused subsystem.
- All tests in `tests/` pass.