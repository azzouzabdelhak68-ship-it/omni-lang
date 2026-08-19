# Benchmark Task 3.4: Integrated ECS Simulation & 3D Scene Coexistence

## Status Metadata
- **STATUS**: `PARTIAL`
- **Implemented**: `sim.*` standard library (`sim.entity`, `sim.system`, `sim.for_each`), simulation model in MIR, JS emitter, C emitter with Flecs adapter, Rust emitter with Bevy adapter.
- **Missing**: `OMNISYS.sim` — full ECS/physics, determinism guarantees across backends, native scene integration.
- **Benchmark purpose**: Discovery/limitation testing only — assesses whether the simulation model coexists cleanly with scene/graphics.
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

Implement an integrated application that runs a data-oriented entity-component simulation and renders its results as a 3D scene, proving the simulation layer coexists cleanly with the scene layer.

### Functional Requirements
1. **Simulation Model**:
   - Define entities with position, velocity, and rendering-component data.
   - Register a motion system that runs each tick and updates positions from velocities.
   - Use component queries to iterate over entities with the required component set.
2. **Scene Integration**:
   - Represent each simulated entity as a visible 3D body in the scene.
   - Keep simulated positions and rendered positions consistent across ticks.
3. **Access Declarations**:
   - Declare read/write access to simulated components explicitly on systems.
4. **Multi-Backend Compilation**:
   - Compile the integrated program for JavaScript, C (Flecs), and Rust (Bevy) targets.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/integrated_sim.omni`**: Primary program implementing the integrated application.
3. **`tests/test_integrated_sim.py`**: Automated test suite verifying simulation update math and scene/sim consistency.
4. **`CONFORMANCE_RESULTS.md`**: Backend conformance matrix across JS, C, and Rust targets.
5. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/integrated_sim.omni` exits with code 0.
- `omni build --target js`, `--target c`, and `--target rust` all succeed.
- All tests in `tests/` pass.