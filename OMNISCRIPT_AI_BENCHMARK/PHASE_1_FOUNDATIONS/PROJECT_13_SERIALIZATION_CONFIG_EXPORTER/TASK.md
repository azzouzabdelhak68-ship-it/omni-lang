# Benchmark Task 1.3: Configuration Loader & Structured Export Tool

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, custom types, `List`, functions, error contracts (`require`/`ensure`).
- **Missing**: JSON/TOML/YAML parsing, schemas, validation, type conversion (unlocks with `OMNISYS.serde`).
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.serde` ships in v6.
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

Implement a configuration loading and export tool that parses structured configuration documents, validates them against a schema, and exports normalized structured values.

### Functional Requirements
1. **Configuration Schema**:
   - Define a typed schema for application configuration: name, version, feature flags, numeric thresholds, and nested option groups.
2. **Parsing & Validation**:
   - Load configuration documents from multiple structured text formats.
   - Validate documents against the schema: required fields present, correct value types, numeric ranges enforced, unknown keys rejected.
   - Classify validation failures distinctly (missing field, wrong type, out-of-range, unknown key).
3. **Type Conversion**:
   - Convert validated configuration values into canonical typed settings.
4. **Export**:
   - Serialize the canonical configuration back into a structured output format.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/config_tool.omni`**: Primary program implementing the loader/exporter.
3. **`tests/test_config_tool.py`**: Automated test suite verifying schema validation and error classification.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/config_tool.omni` exits with code 0.
- `omni run source/config_tool.omni` executes and outputs validated/exported configuration.
- All tests in `tests/` pass.