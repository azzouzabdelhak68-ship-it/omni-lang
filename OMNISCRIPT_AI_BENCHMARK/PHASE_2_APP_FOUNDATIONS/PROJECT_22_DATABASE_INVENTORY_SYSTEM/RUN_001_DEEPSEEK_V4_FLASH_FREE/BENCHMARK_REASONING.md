# BENCHMARK_REASONING.md — Run 001 (DEEPSEEK_V4_FLASH_FREE)

Project: PHASE_2 / PROJECT_22_DATABASE_INVENTORY_SYSTEM
Run dir: E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_22_DATABASE_INVENTORY_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\

This file is a LIVE research ledger. It is maintained in real time while I work and is intentionally
NOT polished or rewritten after the fact.

---

## Session log

### Initial facts from task brief (infrastructure only)
- Compiler CLI: `python -m omni_compiler.cli <command> ...` (commands: check, run, build [targets: js, c, rust, wasm-browser, wasm-wasi], inspect, explain, verify, suggest, generate, trace).
- Stdlib via `import OMNISYS.<module>`; registry at E:\simualtion\omni_compiler\omnisys_registry.py; JS impls at E:\simualtion\omnisys\*.js; the database module is OMNISYS.db.
- Spec: E:\simualtion\OMNI_SPEC.md; docs: E:\simualtion\docs\.
- v7 constitution: must NOT be taught the mechanism being measured; investigate/probe/verify myself.
- .omni files must be UTF-8 WITHOUT BOM.

### Files/dirs created so far
- RUN dir, RUN/source, RUN/tests (created).

### Questions being investigated (initial)
1. What is the OmniScript syntax for module imports, function declarations, types, effects/capabilities?
2. What does `OMNISYS.db` expose? What schema/query/transaction API does it have in the compiler's MIR/checker/emitter?
3. How are effects enforced — how do I declare "database capability" at function boundaries?
4. What does `omni run` actually do (execute vs compile)?
5. How is the program executed for the JS target — is there a runtime harness?

---

## Q1: Exploring the compiler CLI and registry

I'll look at the registry, the spec, the docs index, and the CLI to establish the basics before probing.

### Findings so far

**Registry (`omnisys_registry.py`)** — `OMNISYS_MODULES["db"]` exposes EXACTLY 10 functions, all effect `"database"`:
`create_db(fn(Text) -> Database)`, `create_table(fn(Database, Text, Map) -> Table)`, `insert(fn(Table, Map) -> Map)`,
`select(fn(Table, fn) -> List)`, `update(fn(Table, fn, Map) -> Number)`, `delete(fn(Table, fn) -> Number)`,
`count(fn(Table, fn) -> Number)`, `drop_table(fn(Database, Text) -> Boolean)`, `schema(fn(Table) -> Map)`,
`table_size(fn(Table) -> Number)`.

**NO transactions, NO relationships, NO indexes, NO migrations, NO SQL/query-builder `query` function.** The db module README
and `docs/architecture/06-database.md` and OMNI_SPEC §17.6.1 all *promise* transactions/migrations/relationships, but the
registry (the compiler's single source of truth) does not ship them. TASK.md status BLOCKED is accurate.

**CLI (`cli.py`)**:
- `check` → lex+parse+analyze+MIR; prints `omni check: OK — <file>`; exit 0.
- `run` → compiles AND calls `emit_js(mir)` but DISCARDS the output. It NEVER executes the program. So `omni run` is
  compile-only (JS emission). Transactional verification must come from pytest and/or executing the built JS artifact.
- `build --target js` → writes a self-contained `.html` (default output = input stem + `.html`). The HTML uses a DOM
  (`renderUI`, `bindClicks` reference `document`). Native targets reject OMNISYS imports with E-BACKEND-001.

**JS runtime (`omnisys/db.js`)** — in-memory relational core: tables have `{tag, name, schema, rows[], nextId}`; `insert`
auto-assigns `id` (nextId++); `select(table, predicate)` filters with a JS function; `update(table, predicate, patch)` does
in-place `Object.assign` on matching rows (mutation, returns count); `delete` rebuilds rows; `count`; `drop_table`; `schema`;
`table_size`. Rows are mutated in place; there is NO rollback/constraint mechanism.

**Python mirror** — `packages/omnisys-db/src/omnisys_db/__init__.py` mirrors the JS lane exactly (test_conformance.py locks
registry contract). Useful for pytest to drive real db semantics.

**Language grammar (parser.py + lexer.py)**:
- `import OMNISYS.db` at top.
- `fn name(params: Type) -> RetType:` body `end`; effects clauses before body: `uses <cap>`, `reads <cap>`, `writes <cap>`,
  `pure`; also `require <expr>` / `ensure <expr>`.
- `type Name = { f: Type, ... }` custom structs; construct `Name(f=val, ...)` → JS object literal.
- Statements: assignment `x = expr`, `show expr` (→ console.log), `return expr`, `if cond: ... else: ... end`,
  `for v in iterable: ... end`, `break`, `continue`. Operators: `is`, `is not`, `and`, `or`, `not`(? — see parser: NOT token
  exists but no `not` unary in parse_primary — TODO verify), `greater than`/`less than`/`greater or equal`/`less or equal`,
  `>`, `<`, `>=`, `<=`, `+`, `-`, `*`, `/`. String interpolation `"{x.y}"`.
- Field access requires the object type to be a DECLARED custom type (checker `E-TYPE-002/003`). Loop variables are typed
  `Number` by the checker, so `for row in <List>` + `row.field` will FAIL unless row is a typed function parameter of a
  custom type. Predicates must therefore receive `row: Product`-typed params.

**Effect enforcement (checker.py)**:
- Functions declare capabilities; analyzer computes ACTUAL effects by walking the body: OMNISYS calls contribute their
  registry effect (all db calls → `database`); calls to user functions inherit the callee's declared `uses`; builtin names
  map (`db_query` → database, etc).
- `pure` + any actual effect → E-EFFECT-001. Actual minus declared `uses` → E-EFFECT-003 (undeclared capability).
- `reads`/`writes` clauses are PARSED but NOT enforced against actual effects — only `uses` matters (declared_uses = only
  `uses` list).
- **App block (`when app starts`) is declared with NO capabilities** → it cannot call db functions directly (would be
  E-EFFECT-003). The app block must call user functions that declare `uses database`.

**Emitter (emitter.py)**:
- OMNISYS runtime files inlined; calls emitted as `OMNISYS.db.create_db(...)` — BUT the JS runtime registers the namespace
  as lowercase `omnisys` (`root.omnisys`). Potential case mismatch!! MUST probe: does `OMNISYS.db.*` resolve in emitted JS?
  (grep found NO uppercase alias in omnisys/*.js). Likely emitted JS is broken for direct OMNISYS calls — this needs a probe.
- Struct → `{f: v}`; function args emitted verbatim (so passing a named function works as JS function ref).

**Environment**: node v24.17.0 available; Python 3.11.9.

### Next actions (probes)
1. Probe 1: minimal file importing OMNISYS.db — run `check`, `run`; inspect emitted JS for the `OMNISYS` vs `omnisys`
   namespace case issue.
2. Probe 2: named-function predicate into `select`/`count`.
3. Probe 3: capture-predicate reading a row value into a module-scope variable.
4. Probe 4: `build --target js` + execute the emitted JS under node with a `document` shim to see real runtime behavior.
## Q1 probes & results (recorded live)

### Probe 1 — probes/probe1_import_db.omni (import OMNISYS.db, create_db, create_table, insert, select)
- python -m omni_compiler.cli check → omni check: OK — probe1_import_db.omni, exit 0.
- python -m omni_compiler.cli run → omni run: OK, exit 0. **Confirmed: run emits JS and discards it; NO execution output** (no "done" printed, no console.log). So omni run is compile-only.
- uild --target js -o <out.html> → wrote HTML, exit 0.
- Grep of emitted HTML: program code calls OMNISYS.db.create_db(...) (uppercase) while inlined runtime registers omnisys.db (lowercase).
- 
ode harness.js probe1_import_db.html → **THREW: OMNISYS is not defined** — a real emitter/runtime namespace-case bug (the registry's resolve/is_omnisys_call accept OMNISYS.*, but the JS lane registers only omnisys.*; the emitter emits the source spelling).
- Harness workaround (documented in harness.js): normalize OMNISYS. → omnisys. in the emitted script body (runtime mentions only in comments/strings). With workaround: output [ { id: 1, name: 'bolt', stock: 5 } ] then done; no throw. Full pipeline works.
- **Ecosystem finding #1**: OMNISYS.* calls compile+check fine but the emitted JS is broken (ReferenceError) unless the artifact is normalized. Emitter/registry/JS-runtime namespace case mismatch.

### Probe 2 — probes/probe2_predicates.omni (predicates as named fns; capture side-channel)
- Pass named functions as predicate args to count/select/update/delete: WORKS (JS function refs emitted by name).
- update(t, pred, ItemPatch(stock=4)) mutates in place, returns count.
- Capture side-channel: a predicate can assign a module-scope variable (closure over let); only writes when matched (my first version wrote for every row → captured the LAST row — fixed by guarding with if).
- Correct output: 1, [gadget], 1, olt, 4, 1, 1, 1, done. exit 0.
- **Finding #2**: cross-function module-scope reads are ANALYSIS-ORDER dependent: check processes functions in SOURCE order; a function reading a module var assigned in a LATER function fails E-NAME-001 (SymbolTable fallback if name in self.symbols makes symbols visible once defined, but only after their defining function is analyzed). This forced a strict function-ordering discipline (setters first, then predicates, then logic).

### Probe 3 — probes/probe3_now.omni (OMNISYS.platform.now + negative delta)
- First attempt failed: Unexpected token '-' ... MINUS — **no unary minus / negative literals** in the grammar. Fix:  -2.
- Then failed E-NAME-001 last_stamp undefined — the analysis-order bug above; fixed by reordering (capture fn before reader).
- With fix: timestamps 1787012890071 etc. from OMNISYS.platform.now(); negative qty stored as -2; exit 0.
- **Finding #3**: platform.now() is available and pure (registry) — usable as movement timestamp.

### Probe 4 / 4b — capability enforcement negatives
- probe4_no_decl.omni (db call, no uses database): check → **E-EFFECT-003 "Capability database used without declaration."**, exit 1, with automatic fix suggestion uses database.
- probe4b_pure_effect.omni (db call in pure fn): check → **E-EFFECT-001 "Function declared 'pure' but uses ['database']"**, exit 1.
- **Verified**: the capability model correctly enforces declared data access for the database capability.

### Other findings
- 	race is a SYMBOLIC stepper: _eval_expr raises ValueError: unsupported function call for any FunctionCall; cannot execute OMNISYS calls. Not an execution path.
- inspect demo <file> returns the symbol record with declared_effects.uses: ["database"] — capability declarations are inspectable.
- OMNISYS.collections.list_slice does list.slice(start,end); on a JS string that returns a substring. Combined with OMNISYS.core.length, a REAL name-prefix predicate is expressible: length(row.name) >= len(prefix) and list_slice(row.name, 0, len) is prefix.
- show of a Map/object alone prints the JS object via console.log; concatenating a Map with text coerces to [object Object] — so schema maps are shown standalone.
- App block (when app starts) cannot perform effects directly; must call functions declared uses database.
- node v24.17.0 available; harness (probes/harness.js) shims document + normalizes the OMNISYS case bug.

## Design decisions (Q2)
1. Use the 10-function db API only (the implemented surface). Transactions do NOT exist in OMNISYS.db → implement a **validate-before-mutate** transaction (fail-fast) PLUS an explicit **compensation-based rollback** path (second update restoring the captured stock) to demonstrate "rollback on failure" honestly within the API's constraints.
2. Row values are readable ONLY inside predicates (field access requires a typed custom-type param; loop vars are typed Number). Use module-scope capture variables written by predicates (guarded by if) — the only value-read channel.
3. Queries: predicate-driven selects with parameter state set via setter functions; join implemented by nested selects from a predicate (join_report).
4. Schema maps passed as struct constructs whose field types are the Text type names (schema column type annotations).
5. Output protocol: scenario emits machine-readable KEY value lines; pytest parses them.
6. Function ordering discipline in source (analysis order): setters → build_inventory → capture/predicates → CRUD/transaction/queries → scenario → app block.
7. No equire/ensure contracts used (not needed by mission; erify requires SMT which is not an execution path).
8. Rejected alternatives: JSON snapshot-restore (serde) for rollback — re-insert reassigns ids (insert auto-id), breaking id relationships; also no row-replacement API; loop-iteration over select() results with field access — impossible (loop var typed Number).

## Q2: Building source/inventory.omni — errors, fixes, final results

### Iteration 1 — syntax error E-SYNTAX-001 "Expected COLON, got COMMA" at fn insert_category
- Cause: function PARAMETERS MUST carry type annotations in this language (
ame: Text); untyped params fail.
- Fix: typed all params (Table, Number, Text). Table is accepted as a nominal param type; the checker never validates it (no field access on table params anyway).

### Iteration 2 — E-IMPORT-003 "OMNISYS module 'core' used without being imported"
- Cause: OMNISYS.core.length needs core in imported_modules; importing OMNISYS.collections inlines core as a JS dep but does NOT mark it imported for the checker.
- Fix: add import OMNISYS.core.

### Iteration 3 — runtime ReferenceError "row is not defined"
- Cause A (emitter bug): the JS emitter declares let <v>; only for top-level ssign statements collected across function bodies MINUS all function parameter names. My local variable ow collided with every predicate's ow parameter → never declared.
- Cause B (emitter limitation): assignments nested inside if/or blocks are NOT collected by the emitter's 
eeded pass → capture vars (captured_stock, captured_price, captured_category_id, captured_category_name, everted) would be undeclared.
- Fix: renamed local ow → stored; initialized all nested-assigned capture vars to 0 inside eset_output (a top-level function-body assign, so let declarations are emitted).
- **Finding #4 (emitter)**: variable name collision with ANY function parameter suppresses the let declaration; nested assigns get no declaration. Workaround: pre-initialize nested-assigned module vars via an early top-level-assign function, and avoid local names that collide with parameter names.

### Iteration 4 — CATEGORY_QUERY returned wrong products
- Cause: capture_category_id captured the id into captured_category_id but never set current_category_id; the query predicate used stale current_category_id (3 from the earlier rename).
- Fix: capture_category_id also sets current_category_id = row.id.
- Lesson: the capture channel and the filter-parameter channel are separate module vars; both must be kept in sync.

### Final artifact behavior (node execution of built JS, exact output)
`
COUNT_CATEGORIES 3
COUNT_PRODUCTS 5
REJECT_NEG_PRICE reject:negative-price
REJECT_NEG_STOCK reject:negative-stock
COUNT_PRODUCTS_AFTER_REJECT 5
UPDATED_PRICE ok
PAN_PRICE 28
RENAMED_CATEGORY ok
DELETED_PRODUCT 1
COUNT_PRODUCTS_AFTER_DELETE 4
ADJUST_1 ok
ADJUST_2 ok
ADJUST_3 reject:insufficient-stock
ADJUST_4 reject:zero-delta
HAMMER_STOCK 30
MOVEMENT_COUNT 2
MOVEMENTS 1|1|10|restock;2|2|-2|sale;
ADJUST_ROLLBACK reject:rollback-done
PAN_STOCK_AFTER_ROLLBACK 7
MOVEMENT_COUNT_AFTER_ROLLBACK 2
CATEGORY_QUERY 3|pan|7;
LOW_STOCK 2|drill|2;
PREFIX_QUERY 1|hammer|30;
JOIN_VIEW 1|hammer|tools;2|drill|tools;3|pan|kitchen;4|shovel|outdoor;6|spade|outdoor;
SCHEMA_PRODUCTS
{ name: 'Text', price: 'Text', stock: 'Text', category_id: 'Text' }
done
`
Invariants demonstrated: hammer 20->30 with matching movement +10/restock; drill 4->2 with movement -2/sale; insufficient-stock and zero-delta rejected WITHOUT mutation or movement; rollback path restores pan 7 and adds no movement; category/prefix/low-stock queries correct; join view resolves category names.

### pytest suite (tests/test_inventory.py) — 14 passed
Covers: check exit 0; run is compile-only; all OMNISYS.db-calling functions declare uses database (AST walk); E-EFFECT-003 for undeclared db access; E-EFFECT-001 for pure+db; end-to-end Node execution invariants (CRUD, validation, transactions, rollback, relationships, low-stock/prefix/category queries, schema introspection); and a Python-mirror (omnisys_db) cross-check of the same transaction logic.

### Python-mirror discovery (Finding #5)
omnisys_db.select(table) requires the predicate ARGUMENT positionally; passing nothing raises TypeError: select() missing 1 required positional argument: 'predicate' — while the JS lane treats a missing predicate as "all rows" (	ypeof predicate === 'function'). Cross-lane API divergence: JS optional arg vs Python required positional. The pytest mirror tests pass None explicitly.

## Final verification (raw commands + exit codes)
`
$ python -m omni_compiler.cli check RUN_001_DEEPSEEK_V4_FLASH_FREE/source/inventory.omni
omni check: OK  inventory.omni
$ echo True -> 0

$ python -m omni_compiler.cli run RUN_001_DEEPSEEK_V4_FLASH_FREE/source/inventory.omni
omni run: OK
$ echo True -> 0
(no program output: run is compile-only — emits JS and discards it; it does NOT execute)

$ python -m omni_compiler.cli build RUN_001_DEEPSEEK_V4_FLASH_FREE/source/inventory.omni --target js -o RUN_001_DEEPSEEK_V4_FLASH_FREE/source/inventory.html
omni build: wrote ... (target=js); exit 0

$ node RUN_001_DEEPSEEK_V4_FLASH_FREE/probes/harness.js RUN_001_DEEPSEEK_V4_FLASH_FREE/source/inventory.html
(all scenario output above; harness exits 0; runtime exception count 0)

$ python -m pytest RUN_001_DEEPSEEK_V4_FLASH_FREE/tests/test_inventory.py -p no:cacheprovider
14 passed
`

## Honest verification status
- check exit 0: VERIFIED.
- un transactional scenario: NOT an execution — un is compile-only (emits JS, discards). The transactional invariants were verified by EXECUTING the built JS artifact under node (harness) and by the pytest suite (both end-to-end node assertions and the Python mirror replay).
- pytest suite: 14/14 pass.
- Capability enforcement: VERIFIED both directions (positive declaration required for every db-calling function; E-EFFECT-003 / E-EFFECT-001 on violations).
- The only host-side shim used is probes/harness.js, which (a) stubs document for the browser-shaped HTML and (b) normalizes the emitter's OMNISYS.* → omnisys.* namespace case bug. No language/compiler/registry/runtime files were modified.

## Unresolved questions
- Why the emitter/registry case mismatch (OMNISYS.* emitted vs omnisys.* registered) — presumably a design intent for the uppercase namespace with a missed alias; unresolved at the artifact level, worked around in the harness.
- Whether eads database / writes database are ever enforced: the checker only enforces uses (declared_uses = uses list only). Spec §17.5 lists reads/writes, but enforcement ignores them.
---

## Finishing session (re-verification, 2026-08-17)

This section records the fresh re-verification pass that finished the interrupted run and produced
RESULTS.md. No historical content above was modified.

### Fresh gate runs (exact commands + outputs)
1. `python -m omni_compiler.cli check ...\source\inventory.omni` -> `omni check: OK` EXIT=0. PASS.
2. `python -m omni_compiler.cli run ...\source\inventory.omni` -> `omni run: OK` EXIT=0, NO program output —
   re-confirmed compile-only (emits JS, discards; never executes). Recorded honestly as a boundary.
3. Capability negatives (re-run):
   - `probe4_no_decl.omni` (db call, no declaration) -> **E-EFFECT-003** "Capability database used without
     declaration." EXIT=1, automatic fix `add_declaration` inserting `    uses database`.
   - `probe4b_pure_effect.omni` (db call in pure fn) -> **E-EFFECT-001** "Function declared 'pure' but uses
     ['database']" EXIT=1.
   - Test-generated probes (`tests/_build/undeclared_db.omni`, `pure_db.omni`) -> same codes, EXIT=1.
4. `python -m omni_compiler.cli build ...\source\inventory.omni --target js -o ...\source\inventory.html`
   -> EXIT=0. Executed with `node ...\probes\harness.js` -> full scenario output, EXIT=0, no throw:
   COUNT_CATEGORIES 3 / COUNT_PRODUCTS 5 / REJECT_NEG_PRICE+STOCK rejected / 5 products after reject /
   UPDATED_PRICE ok, PAN_PRICE 28 / RENAMED_CATEGORY ok / DELETED_PRODUCT 1 / 4 after delete /
   ADJUST_1 ok (20->30, +10/restock) / ADJUST_2 ok (4->2, -2/sale) / ADJUST_3 reject:insufficient-stock /
   ADJUST_4 reject:zero-delta / HAMMER_STOCK 30 / MOVEMENT_COUNT 2 / MOVEMENTS 1|1|10|restock;2|2|-2|sale; /
   ADJUST_ROLLBACK reject:rollback-done / PAN_STOCK_AFTER_ROLLBACK 7 / MOVEMENT_COUNT_AFTER_ROLLBACK 2 /
   CATEGORY_QUERY 3|pan|7; / LOW_STOCK 2|drill|2; / PREFIX_QUERY 1|hammer|30; /
   JOIN_VIEW 1|hammer|tools;2|drill|tools;3|pan|kitchen;4|shovel|outdoor;6|spade|outdoor; /
   SCHEMA_PRODUCTS { name: 'Text', ... }. All transactional invariants demonstrated end-to-end.
5. `python -m pytest ...\tests\test_inventory.py -p no:cacheprovider -q` (workdir repo root) ->
   **14 passed in 3.14s**, EXIT=0. All tests green; nothing to fix.
6. BOM check: source/inventory.omni first three bytes = 35,32,79 (`# `) -> UTF-8 no BOM. PASS.
7. `python -m omni_compiler.cli inspect adjust_stock ...\source\inventory.omni` -> omni.symbol record with
   `declared_effects.uses: ["database"]`, reads/writes `[]`, pure `false`; EXIT=0. Capability declarations
   are programmatically inspectable.
8. NEW probe `probes/probe_reads_writes.omni` (created this session): `reads database` and `writes database`
   clauses on functions that perform db I/O. check -> **E-EFFECT-003 for `reads_only`** EXIT=1 — the
   `reads`/`writes` clauses are parsed but NOT recognized as capability declarations; only `uses` is enforced.
   This settles the unresolved "reads/writes enforcement" question: they are currently dead syntax.

### Fixes required this session
- None. The previous session's source and tests already satisfied every gate; no edits to
  source/inventory.omni or tests/test_inventory.py were needed.

### Files created this session
- `probes/probe_reads_writes.omni` (capability clause enforcement probe).
- `RESULTS.md` (the missing deliverable).

### Verification status (final)
- check exit 0: VERIFIED (EXIT=0).
- run transactional scenario: NOT an execution path — `run` is compile-only; transactional invariants were
  verified by executing the built JS artifact under Node and by the pytest suite (end-to-end node asserts +
  Python mirror replay). Recorded honestly.
- pytest: 14/14 pass.
- Capability enforcement: VERIFIED both directions (positive declaration required for every db-calling
  function; E-EFFECT-003 / E-EFFECT-001 on violations; reads/writes clauses ignored).