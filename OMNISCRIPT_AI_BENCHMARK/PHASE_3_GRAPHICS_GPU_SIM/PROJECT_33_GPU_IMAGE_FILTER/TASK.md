# Benchmark Task 3.3: GPU Image Processing Pipeline

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `GPU` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.gpu` — GPU data arrays, kernels, dispatch, memory management, backend abstraction (CUDA/Metal/Vulkan/DirectX/WebGPU).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.gpu` ships in v6.
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

Implement a high-performance image processing pipeline that applies matrix filters to image pixel data using hardware GPU compute, while keeping the pipeline backend-agnostic.

### Functional Requirements
1. **Data Buffers**:
   - Represent images as numeric buffers (width, height, pixel channels).
   - Transfer host pixel data into device memory.
2. **Compute Kernels**:
   - Implement matrix convolution filters (blur, sharpen, edge-detect) as data-parallel operations.
   - Dispatch kernels over the image buffer.
3. **Memory Management**:
   - Allocate, read back, and release device buffers explicitly.
4. **Backend Abstraction**:
   - Write the pipeline against a portable concept; backend selection (CUDA/Metal/Vulkan/WebGPU) must be swappable.
5. **Capability Declaration**:
   - Declare GPU usage explicitly at all functions touching the compute pipeline.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/gpu_filter.omni`**: Primary program implementing the pipeline.
3. **`tests/test_gpu_filter.py`**: Automated test suite verifying convolution math and buffer lifecycle against a CPU reference.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/gpu_filter.omni` exits with code 0.
- Filter outputs match a CPU reference implementation within tolerance.
- All tests in `tests/` pass.