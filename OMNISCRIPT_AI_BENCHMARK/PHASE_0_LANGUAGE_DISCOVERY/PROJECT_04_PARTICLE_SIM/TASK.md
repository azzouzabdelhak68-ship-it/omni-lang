# Benchmark Task 0.4: Particle Motion Simulation Engine

## Status Metadata
- **STATUS**: `READY`
- **Required capabilities**: Simulation standard library API (`sim.*`), MIR generator, multi-target build pipeline (JS, C, Rust).
- **Verified by**: `omni check`, `omni build --target js`, `omni build --target c`, `omni build --target rust`.

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

Implement a data-oriented particle motion simulation engine supporting entity creation, component data, query systems, and multi-backend compilation targets.

### Functional Requirements
1. **Simulation Model Setup**:
   - Define particle entities with spatial position and velocity attributes.
   - Initialize a simulation particle emitter spawning multiple particle entities.
2. **System Logic & Queries**:
   - Register a motion update system function executed every simulation frame.
   - Perform component query iteration updating position coordinates based on velocity vectors and time delta.
   - Enforce access declarations on systems modifying spatial components.
3. **Multi-Target Output Compilation**:
   - Compile the simulation program for JavaScript, C, and Rust backends.
   - Verify that generated output files correctly map simulation concepts to target runtime adapters.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/particle_sim.omni`**: Primary simulation program.
3. **`tests/test_particle_sim.py`**: Automated test suite verifying simulation system registration and execution.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/particle_sim.omni` exits with code 0.
- `omni build source/particle_sim.omni --target js -o generated/particle.js` succeeds.
- `omni build source/particle_sim.omni --target c -o generated/particle.c` succeeds.
- `omni build source/particle_sim.omni --target rust -o generated/particle.rs` succeeds.
