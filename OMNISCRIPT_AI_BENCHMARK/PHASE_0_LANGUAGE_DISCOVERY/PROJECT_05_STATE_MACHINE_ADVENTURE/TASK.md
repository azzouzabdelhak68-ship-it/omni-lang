# Benchmark Task 0.5: State-Machine Adventure Engine

## Status Metadata
- **STATUS**: `READY`
- **Required capabilities**: Complex control flow, custom state structures, WASM/C/JS target emitters, cross-backend build pipeline.
- **Verified by**: `omni check`, `omni build --target js`, `omni build --target c`, `omni build --target wasm-browser`.

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

Implement an interactive state-machine adventure engine featuring room navigation, item inventory state, behavioral transitions, and multi-backend build conformance validation.

### Functional Requirements
1. **World & State Modeling**:
   - Represent game rooms, available transitions, player inventory, and game state metrics using custom data structures.
2. **State Transition Logic**:
   - Implement navigation functions validating movement requests between connected rooms.
   - Implement item interaction functions managing player inventory (picking up items, using inventory keys to unlock room doors).
   - Enforce assertion contracts on state transition boundaries (e.g. player cannot enter locked room without item in inventory).
3. **Multi-Backend Build Conformance**:
   - Build the complete program for JavaScript, C, and WebAssembly (`wasm-browser`) targets.
   - Record target output sizes and backend build output details in a conformance summary matrix.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/adventure.omni`**: Primary program implementing the state-machine adventure engine.
3. **`tests/test_adventure.py`**: Automated test suite verifying state transitions and inventory logic.
4. **`CONFORMANCE_RESULTS.md`**: Backend conformance matrix recording build status, target output sizes, and emitter behavior across JS, C, and WASM targets.
5. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/adventure.omni` exits with code 0.
- `omni build source/adventure.omni --target js` produces valid JavaScript output.
- `omni build source/adventure.omni --target c` produces valid C output.
- `omni build source/adventure.omni --target wasm-browser` produces valid WASM wrapper output.
