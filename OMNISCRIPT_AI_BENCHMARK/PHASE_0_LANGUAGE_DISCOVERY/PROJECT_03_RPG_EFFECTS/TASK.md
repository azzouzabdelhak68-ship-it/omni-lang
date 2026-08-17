# Benchmark Task 0.3: RPG Action & Effect Engine

## Status Metadata
- **STATUS**: `READY`
- **Required capabilities**: Checked effects system, capability declarations, static semantic checker, diagnostics generator.
- **Verified by**: `omni check`, `omni explain`, `omni suggest`.

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

Implement an RPG character action and ability manager requiring explicit side-effect and capability management, and evaluate compiler diagnostic feedback on an immutable invalid effect file.

### Functional Requirements
1. **Character Ability System**:
   - Model character stats, health points, mana points, and status effects.
   - Implement pure mathematical calculation functions for damage calculation, hit probabilities, and stat modifiers (declaring pure execution).
   - Implement action functions for saving character state or performing external actions that explicitly declare their required capabilities and resource access.
2. **Capability Inheritance**:
   - Ensure higher-level action functions calling lower-level capability-bound functions correctly inherit and declare necessary capabilities.
3. **Diagnostic Analysis of `invalid_effect.omni`**:
   - Inspect the immutable test fixture `invalid_effect.omni` located in the project root directory.
   - Run compiler check, diagnostic explanation, and fix suggestion commands against `invalid_effect.omni`.
   - Record the exact diagnostic output schema and suggested fixes in your benchmark findings.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/rpg_engine.omni`**: Primary program implementing the RPG ability system with sound effect declarations.
3. **`tests/test_rpg_engine.py`**: Automated test suite verifying ability calculations and effect enforcement.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/rpg_engine.omni` exits with code 0.
- `omni check invalid_effect.omni` fails with an effect-mismatch diagnostic code.
- `omni explain invalid_effect.omni` and `omni suggest invalid_effect.omni` return structured JSON diagnostic output.
