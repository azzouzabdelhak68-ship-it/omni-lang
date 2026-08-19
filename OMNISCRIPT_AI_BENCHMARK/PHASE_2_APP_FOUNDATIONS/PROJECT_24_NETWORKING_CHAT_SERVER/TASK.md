# Benchmark Task 2.4: Multi-Client Messaging Server

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, functions, loops, `network` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.net` — server lifecycle, WebSocket/RPC transport, connection handling, concurrency.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.net` ships in v6.
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

Implement a multi-client real-time messaging server supporting connection lifecycles, message broadcasting, and protocol handling.

### Functional Requirements
1. **Server Lifecycle**:
   - Start the server, accept multiple concurrent clients, and shut down cleanly.
   - Track connected clients as a live set.
2. **Protocol Handling**:
   - Parse incoming messages into structured records (sender, channel, payload, timestamp).
   - Handle client join/leave events explicitly.
3. **Broadcasting**:
   - Deliver a client's message to all other connected clients.
   - Support channel-scoped delivery.
4. **Concurrency**:
   - Handle concurrent message arrivals without corrupting the client registry.
5. **Capability Declaration**:
   - Declare network usage and connection side-effects at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/chat_server.omni`**: Primary program implementing the server.
3. **`tests/test_chat_server.py`**: Automated test suite verifying connect/disconnect, parsing, and broadcast logic (simulated clients).
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/chat_server.omni` exits with code 0.
- The capability model correctly enforces declared network usage.
- All tests in `tests/` pass.