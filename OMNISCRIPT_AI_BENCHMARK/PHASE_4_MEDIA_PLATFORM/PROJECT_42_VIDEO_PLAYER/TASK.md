# Benchmark Task 4.2: Video Player & Media Controller

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `filesystem` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.video` — decode, encode, seeking, metadata, streaming, frame display.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.video` ships in v6.
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

Implement a video player and media controller that decodes video streams, supports timeline seeking, extracts metadata, and displays frames.

### Functional Requirements
1. **Media Model**:
   - Represent a playable video with a source, duration, resolution, and codec metadata.
2. **Decode & Display**:
   - Decode the media stream and present frames.
3. **Timeline Control**:
   - Play, pause, seek to an arbitrary timestamp, and report current position.
4. **Metadata Extraction**:
   - Extract and present duration, dimensions, and bitrate.
5. **Streaming & Storage**:
   - Load media from a stream source and handle incomplete/partial sources gracefully.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/video_player.omni`**: Primary program implementing the player.
3. **`tests/test_video_player.py`**: Automated test suite verifying timeline math, metadata parsing, and seek bounds (with synthetic media data).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/video_player.omni` exits with code 0.
- All tests in `tests/` pass.