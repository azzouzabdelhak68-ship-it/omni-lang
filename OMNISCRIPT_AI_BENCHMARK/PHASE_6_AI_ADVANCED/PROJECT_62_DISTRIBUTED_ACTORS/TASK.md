# Benchmark Task 6.2: Distributed Actor Cluster

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `sim.actor` distributed runtime (JS) with cluster, nodes, spawn, send, receive, dead-letters, statistics, failover.
- **Missing**: `OMNISYS.async` (advanced) — first-class distributed actors, clustering, cancellation as language features.
- **Benchmark purpose**: Discovery/limitation testing only — assesses advanced-concurrency ergonomics against the current runtime.
- **Verified by**: `omni check`, `omni build --target js`, JS runtime smoke test.

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

Implement a distributed message-passing actor system with node membership, clustering, message routing, and failure handling.

### Functional Requirements
1. **Cluster Model**:
   - Define a cluster with multiple nodes.
   - Track node membership and detect node failure.
2. **Actors & Messaging**:
   - Spawn actors on nodes with an initial state and a message handler.
   - Send messages to actors; route by node and actor address.
3. **Failure Handling**:
   - Handle delivery to missing actors (dead letters).
   - Support restart policies for crashing actors.
   - Detect node loss and update membership.
4. **Statistics & Inspection**:
   - Report cluster statistics and per-node membership.
5. **Concurrency Semantics**:
   - Ensure deterministic processing order for a fixed script of sends.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/actor_cluster.omni`**: Primary program implementing the cluster.
3. **`tests/test_actor_cluster.py`**: Automated test suite verifying routing, dead letters, restart, and membership change.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/actor_cluster.omni` exits with code 0.
- Deterministic behavior for a fixed message script.
- Dead letters and node-failure handling are exercised and tested.