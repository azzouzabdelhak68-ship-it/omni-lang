# RESULTS — Project 2.2: Database / Inventory Management System

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
Date: 2026-08-17
Live research ledger: `BENCHMARK_REASONING.md` (kept during work, not retro-polished; a finishing
re-verification section was appended, no history rewritten).

## MODEL_RESULT

Task completion status: **COMPLETE — all deliverables produced and all acceptance criteria verified.**
TASK.md declares this project `BLOCKED` because `OMNISYS.db` lacks transactions, migrations and
relationships; the registry-confirmed 10-function surface (see ECOSYSTEM_RESULT) is sufficient to build a
correct, invariant-preserving inventory system with validate-before-mutate transactions plus an explicit
compensation-based rollback path, verified end-to-end.

Deliverables (absolute paths):
1. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_22_DATABASE_INVENTORY_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\BENCHMARK_REASONING.md`
2. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_22_DATABASE_INVENTORY_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\source\inventory.omni`
3. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_22_DATABASE_INVENTORY_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\tests\test_inventory.py`
4. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_22_DATABASE_INVENTORY_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\RESULTS.md`

Supporting artifacts (in the same run dir): `source\inventory.html` (built JS artifact),
`probes\harness.js` (Node harness with `document` shim), 8 probe files.

Acceptance criteria verification:

| Criterion | Verification | Pass |
|---|---|---|
| `omni check source/inventory.omni` exits 0 | `python -m omni_compiler.cli check ...\source\inventory.omni` → `omni check: OK` EXIT=0 | PASS |
| Capability model enforces declared data access (database) | Every OMNISYS.db-calling function declares `uses database` (AST-walk test); missing-declaration probe → **E-EFFECT-003** EXIT=1; `pure`+db probe → **E-EFFECT-001** EXIT=1; `inspect adjust_stock` shows `uses:["database"]` | PASS |
| `omni run` executes a transactional scenario without violating invariants | `run` compiles AND executes the program under Node (`scripts/run-omnisys.js`), exit 0, full scenario output including `done`. The transactional invariants were also verified by EXECUTING the built JS artifact under Node (harness) and by the pytest suite (14 end-to-end assertions + Python-mirror replay) | PASS |
| All tests pass | `python -m pytest ...\tests\test_inventory.py -p no:cacheprovider` (workdir repo root) → **14 passed, 0 failed** (3.14s), EXIT=0 | PASS |

Transactional invariants demonstrated (Node execution of the built artifact, machine-readable `KEY value`
output): hammer 20→30 with matching movement `1|1|10|restock`, drill 4→2 with `2|2|-2|sale`; insufficient
stock and zero-delta adjustments rejected **without any mutation or movement**; the compensation-based
rollback path restored pan to 7 and added no movement (MOVEMENT_COUNT stayed 2); category / low-stock /
name-prefix queries and the product↔category join view returned the expected rows; schema introspection
round-tripped the `Text` column types.

Execution efficiency:
- ~15 compiler invocations (check/run/build/inspect/explain/verify/generate plus negative probes) and ~13
  Node harness runs in the original session, plus 8 compiler invocations / 1 build+Node / 1 pytest in the
  finishing re-verification session. A further continuation session fixed the module-scope issue below and
  re-verified all gates green.
- Effort was dominated by probe-driven discovery of the OMNISYS.db surface and 7 non-obvious
  language/compiler behaviors (see ECOSYSTEM_RESULT), not by writing the ~395-line program or its tests.
  A continuation session surfaced ONE additional blocker not caught by the finisher (see RE-VERIFICATION):
  the emitter's module-scope model required source restructuring.

Invalid assumptions encountered (all corrected in-session, recorded in BENCHMARK_REASONING.md):
1. Assumed `OMNISYS.db` ships transactions / migrations / relationships / a query builder because
   `docs/architecture/06-database.md` and OMNI_SPEC §17.6.1 promise them — the registry (the compiler's
   single source of truth) exposes exactly 10 functions and none of those. TASK.md `BLOCKED` is accurate;
   transactions were built as validate-before-mutate + compensation rollback on top of the shipped API.
2. Assumed the emitted JS resolves `OMNISYS.*` calls — the JS runtime registers only lowercase `omnisys.*`,
   so the built artifact throws `OMNISYS is not defined` while `omni check` passes. Worked around in the
   harness by normalizing the emitted namespace.
3. Assumed `omni run` executes the program — during the original session it was compile-only (emits JS,
   discards it); execution was demonstrated via the built JS artifact under Node and via pytest. NOTE: the
   compiler has since been changed (concurrent session work) so `omni run` now EXECUTES under Node; see
   RE-VERIFICATION below.
4. Assumed negative numeric literals are expressible (`-2`) — no unary minus in the grammar; used `0-2`.
5. Assumed `for`-loop variables can access row fields — loop vars are hard-typed `Number`; row values are
   readable only inside predicates whose parameter is a declared custom type, so module-scope capture
   variables (guarded predicates) became the only value-read channel.
6. Assumed function analysis order is irrelevant to module-scope reads — reads of a module var assigned in a
   later-defined function fail E-NAME-001; strict setter-first source ordering was required.
7. Assumed the emitter declares nested-assigned locals and any local name — the `let` set is
   `needed − param_names` for top-level assigns only; locals colliding with any parameter, or assigned inside
   `if`/`for`, get no declaration (strict-mode ReferenceError at runtime). Renamed locals and pre-initialized
   capture vars in `reset_output`.

## ECOSYSTEM_RESULT

### API (OMNISYS)
- `OMNISYS.db` registry surface is EXACTLY 10 functions, all effect `"database"`: `create_db(fn(Text) ->
  Database)`, `create_table(fn(Database, Text, Map) -> Table)`, `insert(fn(Table, Map) -> Map)`,
  `select(fn(Table, fn) -> List)`, `update(fn(Table, fn, Map) -> Number)`, `delete(fn(Table, fn) -> Number)`,
  `count(fn(Table, fn) -> Number)`, `drop_table(fn(Database, Text) -> Boolean)`, `schema(fn(Table) -> Map)`,
  `table_size(fn(Table) -> Number)`. **No transactions, no relationships, no indexes, no migrations, no SQL /
  query-builder `query` function** — despite docs and OMNI_SPEC §17.6.1 promising all of them.
- Schema maps are plain `Map` column-type annotations passed to `create_table`; `schema(table)` returns them
  (round-trip verified: `{ name: 'Text', price: 'Text', ... }`).
- `insert` auto-assigns row `id` (monotonic `nextId++`), so "restore by re-insert" strategies for rollback
  would break id relationships; no row-replacement API exists.
- `OMNISYS.platform.now()` (pure, registry) provides real movement timestamps; `OMNISYS.core.length` +
  `OMNISYS.collections.list_slice` compose a real name-prefix predicate (list_slice on a string = substring).

### Language
- Custom `type` structs (`type ProductRow = { id: Number, ... }`), constructed with `Struct(name=v)`. Field
  access is allowed ONLY on function parameters typed as a declared custom type — this is the predicate idiom
  the whole program is built on. Loop variables are typed `Number`, so iterating a `select` result and reading
  `row.field` is statically impossible (E-TYPE-002); the predicate + module-state channel substitutes.
- Effects clauses: `uses <cap>`, `reads <cap>`, `writes <cap>`, `pure`, plus `require`/`ensure` (not used —
  `verify` is an SMT path, not execution). `when app starts` declares NO capabilities and cannot call
  `OMNISYS.db.*` directly (E-EFFECT-003); it must delegate to functions declared `uses database`.
- No unary minus / negative literals (`-2` is a syntax error); no `and`/`or`/unary `not` in the parser.
  Operators verified: `is`, `is not`, `+`, `-`, `*`, `/`, `less than`, `greater than`, `greater or equal`,
  `less or equal`; `{}` interpolation is the only string builder.

### Compiler
- `check` = tokenize→parse→analyze→MIR, prints `omni check: OK`, exit 0. `run` = same pipeline plus JS
  emission that is then DISCARDED (`omni run: OK`, never executes). `build --target js` writes a self-contained
  HTML with the OMNISYS runtime inlined.
- **Emitter defect (high severity):** the emitted `let` declarations are module-scope `needed − param_names`
  collected only across top-level assigns; any local whose name matches a parameter of ANY function, or any
  variable assigned inside `if`/`for`, is emitted without a declaration → strict-mode `ReferenceError` while
  `omni check` still passes. Workarounds: rename locals (`stored`), pre-initialize nested-assigned module vars
  in an early top-level function (`reset_output`).
- **Emitter/runtime namespace mismatch:** calls are emitted verbatim from source spelling (`OMNISYS.db.*`), but
  the inlined JS runtime registers only `omnisys.*` (lowercase). Built artifacts throw `OMNISYS is not
  defined`. The harness normalizes `OMNISYS.`→`omnisys.`.
- Function analysis order is source order and module-scope reads resolve only against already-analyzed
  functions (later-defined assignments are invisible → E-NAME-001). Deterministic but surprising.
- `inspect <symbol> <file>` returns a full `omni.symbol` record (type, `declared_effects` incl. `uses`,
  exported) — capability declarations are programmatically auditable. `build --target c/rust/wasm-*` rejects
  OMNISYS imports with E-BACKEND-001.

### Diagnostic
- Structured `omni.diagnostic` JSON everywhere: code, category, severity, message, details, span, location,
  context, and machine-actionable `fixes`. E-EFFECT-003 carries an **automatic** `add_declaration` fix
  inserting the exact `    uses database` text; E-EFFECT-001 carries a suggested `replace_span` (remove
  `pure`). `explain`/`suggest`/`generate` exist; `verify` reports `no-contracts` for contract-free functions.
- Verified codes: E-EFFECT-003 (undeclared database capability), E-EFFECT-001 (pure + database effect),
  E-IMPORT-003 (module used without import), E-SYNTAX-001 (untyped parameter), E-NAME-001 (unknown symbol /
  analysis-order read), E-TYPE-002 (field access on non-custom-typed value).

### Documentation
- Docs are STALE relative to the registry (compiler's single source of truth): `docs/architecture/06-database.md`
  and OMNI_SPEC §17.6.1 promise transactions, migrations and relationships that the registry does not ship;
  the registry's exact 10-function surface matches `packages/omnisys-db` (locked by test_conformance.py) and
  `omnisys/db.js`. Per-module READMEs claim more than the checker/runtime expose — a significant trap.

### Capability/Effect
- Enforcement is real and transitive inside functions: any `OMNISYS.db.*` call without `uses database` fails
  E-EFFECT-003 (exit 1) with an automatic fix; `pure` functions cannot touch the database (E-EFFECT-001).
  Verified both directions (positive requirement on all 14 db-calling functions via AST walk; negatives via
  probes). The app block is capability-less and must delegate.
- **`reads`/`writes` clauses WERE parsed but NOT enforced at original-session time** — but enforcement has
  since been added: E-EFFECT-004 now fires for module data accessed via `reads`/`writes` without declaration
  (see RE-VERIFICATION). A function declared `uses database` still passes without fine-grained
  read/write separation; the current grammar expresses per-RESOURCE (variable) reads, not per-capability
  read/write roles. There is still no way to express coarse read-only vs write-only database roles, which a
  relational DB mission would otherwise want.

### Backend (JS runtime, `omnisys/db.js`)
- In-memory relational core: tables `{tag, name, schema, rows[], nextId}`; `insert` auto-ids; `update` mutates
  matching rows in place with `Object.assign` and returns the count; `delete` rebuilds rows; `count`/`select`
  filter via JS predicates; `drop_table`/`schema`/`table_size`. No constraints (negative values pass through
  if unguarded), no rollback, no indexes.
- Verified in Node v24 (via harness with DOM stubs): full CRUD, validation guards, both transaction paths,
  relationship join, and all three query families execute correctly and deterministically.
- Cross-lane divergence: the Python mirror `omnisys_db.select(table)` REQUIRES the predicate argument
  positionally (TypeError otherwise), while the JS lane treats a missing predicate as "all rows". The pytest
  mirror passes `None` explicitly. The two lanes are not API-identical despite test_conformance.py.

### Positive Discoveries
1. The 10-function `OMNISYS.db` surface is small but sound: schema, CRUD, predicate-driven select/count, and
   introspection compose into a correct relational application; `schema()` gives a real introspection round-trip.
2. The capability model genuinely enforces declared data access for `database` — compile-time, with automatic,
   exact fix text. This is a strong AI-first affordance.
3. `inspect` exposes the declared-effect record per symbol, enabling tooling to audit data access statically.
4. The predicate + module-state channel, though indirect, is a deterministic, side-channel-free pattern for
   parameterized queries (category / threshold / prefix / join) entirely within the language.
5. `platform.now()` (pure) makes movement timestamps real, enabling audit-style stock movement records.
6. Backend capability gating (E-BACKEND-001) cleanly prevents silently broken native builds for OMNISYS code.
7. The JS artifact (single HTML, runtime inlined) is portable and executable headlessly with trivial DOM
   stubs — good for CI-style verification of compiled OmniScript.

### Proposed Changes
1. Registry/db: ship a transaction primitive (e.g. `transaction(fn(Table, ...) -> X)` or a `begin`/`commit`/
   `rollback` surface) and document constraints on `insert`/`update` so the benchmark's "atomic stock +
   movement, rollback on failure" requirement can be met natively instead of via compensation patterns.
2. Docs: regenerate `docs/architecture/06-database.md` and OMNI_SPEC §17.6.1 from the registry; either delete
   or clearly mark the promises (transactions, migrations, relationships, indexes, query builder) as roadmap.
3. Emitter: declare function-scope locals inside each emitted function (or a var/let pass over actual scopes)
   instead of the module-scope `needed − param_names` heuristic — fixes the ReferenceError defect class.
4. Emitter/runtime: emit the canonical `omnisys.*` (or register an uppercase alias) so checked programs run
   unchanged; currently every OMNISYS-consuming artifact needs a post-build rewrite.
5. Checker: enforce (or explicitly reject) `reads`/`writes` clauses; at minimum, accept `reads database` /
   `writes database` as valid declarations so the finer-grained capability grammar isn't dead syntax.
6. Language: add unary minus / negative literals (or an explicit diagnostic) and implement or reject the
   documented `and`/`or` operators — both are currently silent parser gaps.
7. Cross-lane: make the Python `omnisys_db` mirror match the JS lane's optional predicate (or encode the
   requirement in the registry contract) so the two lanes are drop-in equivalent for test replay.
8. Language/emitter: make function-assigned names module-scope by default (or add an explicit module-state
   keyword), so setter-written shared state does not require entry-point pre-declaration; and emit the
   unconditional `bindClicks` UI wiring only for programs that actually declare click handlers.

## RE-VERIFICATION (session continuation, 2026-08-18)

The compiler changed during concurrent run work: `omni run` now EXECUTES under Node, and the emitter scopes
`let` locals to each function while treating entry-point-assigned names as module state. Re-verified under
the FINAL compiler state:

- Gates: `check` OK EXIT=0; `run` executes the full scenario EXIT=0; pytest **14 passed, 0 failed**.
- **Blocker found by actually executing the built artifact:** the program's design assumed "module-scope
  state written by setter functions" (table handles + capture vars assigned inside `build_inventory` /
  `reset_output` / capture predicates). Under the emitter, names assigned in a function are function-locals,
  so `run_scenario` hit `ReferenceError: categories_tbl is not defined` while `check` still passed — a real
  language-model gap: OmniScript has no way to make a name module-scope except by assigning it in the entry
  block. Fixed in `source/inventory.omni` by pre-declaring every module var in `when app starts`
  (tables, `output_lines`, all `captured_*`, all `current_*`, `target_id`, `reverted`) and adding the now-
  enforced `reads <var>` declarations to every function that reads them (E-EFFECT-004). The setter +
  capture-predicate + query-parameter pattern then works as intended.
- **Harness fix:** `probes/harness.js` document shim lacked `addEventListener`; the emitted runtime
  unconditionally wires UI event delegation even for a non-UI program. Added `addEventListener() {}` to the
  `getElementById` stub.
- **Test fix:** `test_run_command_is_compile_only` asserted the old compile-only banner; renamed to
  `test_run_command_executes_program` and asserted execution output (`done`, `COUNT_CATEGORIES 3`).
- Net-new ecosystem findings recorded: (a) module-state model requires entry-point pre-declaration (see
  Proposed Changes 8); (b) the emitter emits the unconditional `bindClicks` UI wiring for every program;
  (c) `reads`/`writes` enforcement is now live (E-EFFECT-004) with automatic `declare-reads-<resource>`
  fixes — the earlier "dead syntax" finding is superseded.