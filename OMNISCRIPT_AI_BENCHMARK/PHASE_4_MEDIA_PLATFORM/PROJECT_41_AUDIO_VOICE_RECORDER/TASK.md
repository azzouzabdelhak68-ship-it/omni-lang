# Benchmark Task 4.1: Voice Recorder & Waveform Player

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `camera`/`microphone`/`filesystem` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.audio` — audio I/O, capture, synthesis, processing; device permissions.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.audio` ships in v6.
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

Implement a voice recording and playback application that captures microphone audio, processes the waveform, persists recordings, and plays them back.

### Functional Requirements
1. **Audio Capture**:
   - Start and stop microphone input capture.
   - Represent captured audio as sampled waveform data.
2. **Signal Processing**:
   - Compute a waveform visualization (amplitude envelope over time).
   - Apply a basic transform (normalization or simple gain).
3. **Playback**:
   - Play back recorded audio.
4. **Persistence**:
   - Save and load recordings to/from storage.
5. **Permissions & Effects**:
   - Declare microphone and storage capabilities at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/voice_recorder.omni`**: Primary program implementing the recorder.
3. **`tests/test_voice_recorder.py`**: Automated test suite verifying waveform math and persistence logic (with synthetic samples).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/voice_recorder.omni` exits with code 0.
- Capability declarations correctly express microphone and storage access.
- All tests in `tests/` pass.