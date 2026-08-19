# BENCHMARK REASONING LEDGER - Phase 4 Project 4.3: Media/Camera Capture

## Initial Investigation (2026-08-18)

### Questions Investigated
- What OMNISYS modules are available for camera, microphone, and video?
- What is the OmniScript syntax for capability declarations (`uses`, `pure`, `reads`, `writes`)?
- How does the compiler check enforce effect systems for device access?
- What previous patterns exist in Phase 4 projects (4.1 Voice Recorder, 4.2 Video Player)?
- How are camera and microphone capabilities declared and checked?

### Hypotheses & Assumptions
- `OMNISYS.camera` module may not exist in v6 like `OMNISYS.microphone` - capability must be declared but runtime support may be absent
- `OMNISYS.microphone` module does not currently registered - capability must be declared but runtime support absent (confirmed from Project 41)
- Compiler checks: E-EFFECT-003 (capability declaration), E-EFFECT-004 (module data reads/writes), E-EFFECT-001 (pure function effect violation)
- Camera and microphone must be declared at every function touching device streams per task requirements
- Device permission must model as explicit, grantable/deniable state

### Files Inspected
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_4_MEDIA_PLATFORM\PROJECT_43_MEDIA_CAPTURE\TASK.md` - Task metadata and requirements
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_4_MEDIA_PLATFORM\PROJECT_41_AUDIO_VOICE_RECORDER\RUN_001_CLAUDE_3_5\BENCHMARK_REASONING.md` - Reference implementation study
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_4_MEDIA_PLATFORM\PROJECT_41_AUDIO_VOICE_RECORDER\RUN_001_CLAUDE_3_5\source\voice_recorder.omni` - Reference OmniScript implementation
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_4_MEDIA_PLATFORM\PROJECT_41_AUDIO_VOICE_RECORDER\RUN_001_CLAUDE_3_5\tests\test_voice_recorder.py` - Reference test suite
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_4_MEDIA_PLATFORM\PROJECT_41_AUDIO_VOICE_RECORDER\RUN_001_CLAUDE_3_5\RESULTS.md` - Reference results format

### Compiler Behaviors Discovered
- `omni check` performs type-checking and effect-checking, exits 0 on success
- `omni run` compiles and executes under Node.js, requires `--target js` for native targets
- `omnisys_effects()` in registry returns declared capability effects for OMNISYS calls
- Pure functions must not use effectful capabilities; violation -> E-EFFECT-001
- Functions accessing module resources must declare `reads`/`writes`; violation -> E-EFFECT-004
- Undeclared capability usage -> E-EFFECT-003
- `import OMNISYS.<module>` must resolve to a registered module; otherwise E-IMPORT-003
- `uses microphone` declaration is accepted by checker even though no OMNISYS.microphone module exists (syntactic per task requirements)

### Architectural & Code Decisions

#### Camera Processing Path
- Use `OMNISYS.camera` pure functions for frame processing (if available)
- No actual camera capture (unavailable in v6); declare `uses camera` per requirements
- Use synthetic test frames/buffers for processing and validation
- Declare `uses camera` at function boundaries that touch camera streams

#### Microphone Processing Path
- Use `OMNISYS.microphone` pure functions for audio sample processing (if available)
- No actual microphone capture (unavailable in v6); declare `uses microphone` per requirements
- Use synthetic test audio data for waveform validation and transforms
- Declare `uses microphone` at function boundaries that touch microphone streams

#### Permission Lifecycle Modeling
- Model device permission as explicit state: `granted`, `denied`, `prompted`
- Handle denial gracefully with distinct status return values
- Permission state flows through functions that acquire/release streams
- Denial path returns early with specific status indicator

#### Capability Declarations
- `uses camera` declared at camera touch function boundaries
- `uses microphone` declared at microphone touch function boundaries
- Pure helper functions (frame processing, sample analysis) remain `pure` without capability declarations
- `uses filesystem` declared at any function that reads/writes capture files

### Alternative Approaches Considered & Rejected

1. **Real camera/microphone capture**: Rejected - `OMNISYS.camera`/`OMNISYS.microphone` modules do not exist in v6, would cause E-IMPORT-003 at runtime; `uses` declarations are syntactic per task requirements
2. **Full duplex camera + audio I/O**: Rejected - beyond scope; v6 only provides synthesis/processing functions
3. **Omit capability declarations**: Rejected - task explicitly requires camera and microphone capability declarations; would fail E-EFFECT-003
4. **Using `OMNISYS.net` for device transport**: Rejected - net is for network transport, not device I/O

### Unresolved Questions
- Whether `OMNISYS.camera` module exists in v6 or if `uses camera` declaration is purely syntactic like `uses microphone`
- Exact behavior of camera frame acquisition without `OMNISYS.camera` module
- Whether the compiler will accept `uses camera` declaration with no corresponding module (same pattern as `uses microphone`)
- How permission denial status is represented and returned in synthetic implementations
- Whether `for-i n` loops or `for-in` loops are supported for frame/sample iteration

### Verification Results

- Task directory contains only `TASK.md` - no implementation yet
- RUN directory created at `RUN_001_CLAUDE_3_5/` with empty `source/` and `tests/` subdirectories
- All deliverables yet to be created: `source/media_capture.omni`, `tests/test_media_capture.py`, `RESULTS.md`
- Next step: Create `source/media_capture.omni` with capability declarations and synthetic capture logic, then create test suite