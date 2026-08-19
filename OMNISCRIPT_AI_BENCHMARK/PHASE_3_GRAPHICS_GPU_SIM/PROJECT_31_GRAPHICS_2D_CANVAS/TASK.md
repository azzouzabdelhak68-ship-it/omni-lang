# Benchmark Task 3.1: Interactive 2D Vector Drawing Canvas

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `UI:` block, `scene:` block (3D primitives).
- **Missing**: `OMNISYS.graphics` — 2D shapes, transforms, canvas rendering, 2D input events.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.graphics` ships in v6.
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

Implement an interactive 2D vector drawing application supporting geometric shapes, transforms, colors, user input, and simple animation.

### Functional Requirements
1. **Shape Model**:
   - Represent 2D primitives: rectangles, circles, lines, and polygons with fill and stroke colors.
2. **Canvas Rendering**:
   - Render the shape collection to a visual canvas.
3. **Transforms**:
   - Apply position, rotation, and scale transforms to shapes.
4. **User Input**:
   - Add, move, and delete shapes through pointer interaction.
   - Select a shape and change its color.
5. **Animation**:
   - Animate at least one property (position, rotation, or opacity) over time.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/canvas_app.omni`**: Primary program implementing the drawing canvas.
3. **`tests/test_canvas_app.py`**: Automated test suite verifying shape/transform logic and input handling.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/canvas_app.omni` exits with code 0.
- `omni build source/canvas_app.omni --target js` produces a runnable artifact.
- All tests in `tests/` pass.