# Benchmark Task 4.3: Camera & Microphone Capture Application

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `camera`/`microphone` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.camera`, `OMNISYS.microphone` — device access, stream capture, permission lifecycle.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once device modules ship in v6.
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

Implement a real-time camera and audio capture application that accesses device streams under explicit permission/capability enforcement.

### Functional Requirements
1. **Device Access**:
   - Discover and select camera and microphone devices.
   - Acquire and release device streams explicitly.
2. **Capture**:
   - Capture camera frames and audio samples.
   - Provide a preview state and stop/start control.
3. **Permission Lifecycle**:
   - Model device permission as an explicit, grantable/deniable state.
   - Handle denial gracefully with a distinct status.
4. **Capability Enforcement**:
   - Declare camera and microphone capabilities at every function touching device streams.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/media_capture.omni`**: Primary program implementing capture.
3. **`tests/test_media_capture.py`**: Automated test suite verifying device state machine and permission handling (with mocked devices).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/media_capture.omni` exits with code 0.
- Capability declarations correctly express camera and microphone access.
- All tests in `tests/` pass.