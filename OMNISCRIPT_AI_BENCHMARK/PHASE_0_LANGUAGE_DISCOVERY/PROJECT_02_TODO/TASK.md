# Benchmark Task 0.2: Task Management & Todo Engine

## Status Metadata
- **STATUS**: `READY`
- **Required capabilities**: Custom type system, List collections, iteration constructs, state mutation, functions.
- **Verified by**: `omni check`, `omni run`, `omni inspect`.

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

Implement a data structure, state manager, and task list engine for managing todo items and task collections.

### Functional Requirements
1. **Custom Data Types**:
   - Define a structured Task/Todo representation containing title text, completion status, priority score, and category.
2. **Collection Operations**:
   - Create, store, and manage a collection of task records.
   - Implement functions to filter task lists by completion status (completed vs active).
   - Implement functions to search tasks by category or title substring.
   - Implement aggregation functions calculating completion percentage and remaining high-priority tasks.
3. **Iteration & State Updates**:
   - Process collections using iteration blocks with conditional break and continue controls.
   - Update individual task completion states cleanly across list collections.
4. **Formatting & Output**:
   - Build a summary formatter that converts a list of tasks into a single formatted report string using text interpolation or joining builtins.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/todo_engine.omni`**: Primary program implementing the task management engine.
3. **`tests/test_todo_engine.py`**: Automated test suite verifying task filtering, iteration, and state updates.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/todo_engine.omni` exits with code 0.
- `omni run source/todo_engine.omni` executes and outputs formatted task reports.
- `omni inspect symbol source/todo_engine.omni` correctly inspects task data structures and functions.
