# Benchmark Task 3.2: Interactive 3D Solar System Visualization

## Status Metadata
- **STATUS**: `PARTIAL`
- **Implemented**: `scene:` block with `box`, `sphere`, `cylinder`, `plane`, `light`, `camera` primitives; attributes (`size`, `color`, `pos`, `rotation`, `scale`); Three.js JS emission.
- **Missing**: `OMNISYS.scene` — full scene graph, per-mesh transforms, hierarchical animation, native backends (Vulkan/Metal/DX/WebGPU).
- **Benchmark purpose**: Discovery/limitation testing only — assesses scene-capability depth against the current `scene:` block.
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

Implement an interactive 3D solar system visualization with a scene graph, camera, lighting, mesh bodies, orbital motion, and interaction.

### Functional Requirements
1. **Scene Composition**:
   - Compose a 3D scene with a central star and several orbiting planetary bodies.
   - Include a light source and a camera framing the scene.
2. **Hierarchical Motion**:
   - Implement orbital motion: planets revolve around the central star.
   - Support hierarchical transforms (a moon orbiting a planet).
3. **Lighting & Materials**:
   - Assign distinct colors to bodies; ensure lighting produces a sensible 3D appearance.
4. **Interaction**:
   - Allow the user to rotate the camera view or select a body to highlight it.
5. **Animation**:
   - Drive continuous orbital motion over time.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/solar_system.omni`**: Primary program implementing the visualization.
3. **`tests/test_solar_system.py`**: Automated test suite verifying scene composition and motion math.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/solar_system.omni` exits with code 0.
- `omni build source/solar_system.omni --target js` produces a runnable 3D artifact.
- All tests in `tests/` pass.