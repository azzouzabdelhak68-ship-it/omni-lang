# Benchmark Task 5.2: Authenticated Web Service

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `network`/`database`/`secrets` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.auth` (registration, login, sessions, JWT/OAuth) plus `OMNISYS.db`, `OMNISYS.net`, `OMNISYS.crypto`.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once auth + supporting modules ship in v6. Tests capability composition.
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

Implement an authenticated web service combining network endpoints, cryptographic primitives, and persistent storage to deliver registration, login, session handling, and authorization.

### Functional Requirements
1. **Registration & Login**:
   - Register users with credentials; store credentials securely.
   - Authenticate users on login.
2. **Sessions & Tokens**:
   - Issue session tokens on successful login and validate them on protected endpoints.
   - Support logout (session invalidation).
3. **Authorization**:
   - Protect certain endpoints (e.g. user profile) so only authenticated users can access them.
   - Reject unauthenticated access with a clear status.
4. **Capability Composition**:
   - The service composes networking, database, and cryptography capabilities into a single coherent application.
   - Every function declares its capabilities; no undeclared side-effects.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/auth_service.omni`**: Primary program implementing the service.
3. **`tests/test_auth_service.py`**: Automated test suite verifying registration, login, authorization, and logout flows (with in-memory storage).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes — **with special attention to how well multiple capabilities compose**.

### Verification Criteria
- `omni check source/auth_service.omni` exits with code 0.
- Protected endpoints reject unauthenticated requests.
- All tests in `tests/` pass.