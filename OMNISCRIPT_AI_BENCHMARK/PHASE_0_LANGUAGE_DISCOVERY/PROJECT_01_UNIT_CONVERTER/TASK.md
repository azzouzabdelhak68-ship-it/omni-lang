# Benchmark Task 0.1: Multi-Unit Conversion Engine

## Status Metadata
- **STATUS**: `READY`
- **Required capabilities**: Core compiler (type checker, parser, contract verification, JS emitter).
- **Verified by**: `omni check`, `omni verify`, `omni run`, `omni generate`.

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

Implement a multi-unit conversion engine capable of converting values across temperature, length, and weight units with rigorous boundary validation and precision constraints.

### Functional Requirements
1. **Core Conversion Operations**:
   - Convert temperature between Celsius, Fahrenheit, and Kelvin.
   - Convert length between Meters, Feet, Inches, and Kilometers.
   - Convert weight between Kilograms, Pounds, and Ounces.
2. **Safety & Boundary Contracts**:
   - Enforce non-negative input constraints where physically required (e.g., Kelvin cannot be negative, length and weight measurements cannot be below zero).
   - Require explicit preconditions for mathematical operations subject to division or invalid boundaries.
   - Assert postconditions guaranteeing converted values adhere to expected ranges and formulas.
3. **Data Representation**:
   - Define structured representation for conversion results combining the numerical value, source unit, target unit, and status code or message.
4. **Effect Declarations**:
   - Pure conversion functions must declare zero side-effects.
   - Main entry point must display conversion outputs cleanly.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/unit_converter.omni`**: Primary program implementing the conversion engine.
3. **`tests/test_unit_converter.py`**: Automated test suite verifying conversion formulas and contract bounds.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/unit_converter.omni` exits with code 0.
- `omni verify source/unit_converter.omni` statically proves all declared contracts.
- `omni run source/unit_converter.omni` executes without runtime errors.
- `omni generate source/unit_converter.omni convert_temperature` generates a valid test template.
