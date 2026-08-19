# Benchmark Task 5.5: Native Interoperability & Escape Hatch

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `process`/`GPU` capability vocabulary, escape-hatch architecture (documented in v6 §17.4).
- **Missing**: `OMNISYS.platform` native interop layer — FFI, backend-specific escapes (CUDA/Metal/Vulkan/DirectX/WebGPU).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once the native interop model ships in v6. The target backend determines the exercised escape hatch.
- **Verified by**: `omni check`, `omni build --target <selected-backend>`.

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

Build a small application that requires functionality unavailable through the standard OmniScript/OMNISYS API. Investigate and use the supported native interoperability mechanism to access that functionality while preserving type and error boundaries.

### Functional Requirements
1. **Gap Identification**:
   - Choose a small, concrete capability that the standard API does not provide.
2. **Escape Hatch Usage**:
   - Discover and use the ecosystem's supported native interop / foreign-function mechanism.
   - The target backend (native, WASM, browser) determines which escape hatch is exercised.
3. **Boundary Preservation**:
   - Convert values across the language/native boundary with correct typing.
   - Propagate native failures as structured errors, never silent crashes or type confusion.
4. **Portable Core**:
   - Keep the main program portable; confine native-specific logic to an escape layer.
5. **Capability Declaration**:
   - Declare the required capabilities (e.g. `process`, `GPU`) at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/`**: The application with a clean portable/native split.
3. **`tests/`**: Tests covering the interop boundary, including failure propagation.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to the escape-hatch model**.

### Verification Criteria
- `omni check` passes on the portable source.
- The native capability is exercised through the supported mechanism.
- Type and error boundaries hold under test (no silent type confusion).