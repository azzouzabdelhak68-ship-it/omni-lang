# Benchmark Task 6.1: Local AI Inference Assistant

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `GPU` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.ai` — tensors, autograd, inference, tool use, structured outputs, model interaction.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.ai` ships in v6.
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

Implement a local AI inference assistant that runs a small model, performs tensor operations, and produces structured, machine-readable outputs.

### Functional Requirements
1. **Tensor Model**:
   - Represent model weights and activations as typed numeric tensors.
2. **Inference**:
   - Run forward inference over input data through a small model (e.g. a linear/affine classifier).
3. **Tool Use / Structured Output**:
   - Map model outputs to structured result records with confidence.
   - Support a tool-like dispatch: the assistant selects an action from a fixed set based on structured output.
4. **Capability Declaration**:
   - Declare any compute capabilities (e.g. GPU) used by the inference path.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/ai_assistant.omni`**: Primary program implementing the assistant.
3. **`tests/test_ai_assistant.py`**: Automated test suite verifying tensor math and structured-output mapping against a reference implementation.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/ai_assistant.omni` exits with code 0.
- Inference results match the reference within tolerance.
- Structured outputs are well-typed and deterministic for fixed inputs.
- All tests in `tests/` pass.