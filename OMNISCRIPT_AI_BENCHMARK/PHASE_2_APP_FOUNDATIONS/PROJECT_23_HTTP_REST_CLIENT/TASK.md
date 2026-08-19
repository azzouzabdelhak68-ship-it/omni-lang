# Benchmark Task 2.3: External REST API Client

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, custom types, `List`, `network` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.http` — HTTP client, serialization, timeouts, typed responses.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.http` ships in v6.
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

Implement an external REST API integration client that formats requests, deserializes typed responses, handles errors and timeouts, and respects capability declarations.

### Functional Requirements
1. **Request Formatting**:
   - Build GET and POST requests against a configured external endpoint.
   - Construct query strings, headers, and JSON request bodies.
2. **Typed Responses**:
   - Define typed result structures for the expected API response payloads.
   - Deserialize raw responses into these typed structures.
3. **Error & Timeout Handling**:
   - Distinguish connection failures, HTTP error statuses, malformed payloads, and timeouts.
   - Enforce request timeouts.
4. **Capability Declaration**:
   - Declare network usage and any serialization side-effects at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/api_client.omni`**: Primary program implementing the client.
3. **`tests/test_api_client.py`**: Automated test suite verifying request construction, response parsing, and error classification (using stubbed responses).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/api_client.omni` exits with code 0.
- The capability model correctly enforces declared network usage.
- All tests in `tests/` pass.