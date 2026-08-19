# Benchmark Task 2.2: Inventory Management System

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, custom types, `List`, functions, effects enforcement.
- **Missing**: `OMNISYS.db` — schema definition, SQL/query builder, transactions, relationships, indexes, migrations.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.db` ships in v6.
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

Implement a relational inventory management system supporting schema definition, transactional data updates, relationships, and query composition.

### Functional Requirements
1. **Schema Definition**:
   - Define products (id, name, price, stock quantity) and categories with a defined relationship.
   - Define a stock movement record type tracking quantity changes with timestamps.
2. **CRUD Operations**:
   - Insert, read, update, and delete products and categories.
   - Record stock movements whenever inventory quantities change.
3. **Transactions**:
   - Perform multi-step operations atomically: adjusting stock MUST create a matching movement record.
   - On any failure, roll back to the prior consistent state.
4. **Queries & Relationships**:
   - Query products by category, by stock threshold (low-stock reporting), and by name prefix.
   - Join product and category data into combined views.
5. **Validation & Effects**:
   - Reject negative prices or negative stock.
   - Declare all data access at function boundaries via the capability model.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/inventory.omni`**: Primary program implementing the inventory system.
3. **`tests/test_inventory.py`**: Automated test suite verifying CRUD, transactions, relationships, and low-stock queries.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/inventory.omni` exits with code 0.
- `omni run source/inventory.omni` executes a transactional scenario without violating invariants.
- All tests in `tests/` pass.