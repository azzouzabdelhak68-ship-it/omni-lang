# RESULTS — Project 2.3: External REST API Client

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
Date: 2026-08-17
Live research ledger: `BENCHMARK_REASONING.md` (kept during work, not retro-polished).

## MODEL_RESULT

Task completion status: **COMPLETE — all deliverables produced and all acceptance criteria verified.**

Deliverables (absolute paths):
1. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE\BENCHMARK_REASONING.md`
2. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE\source\api_client.omni`
3. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE\tests\test_api_client.py`
4. `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE\RESULTS.md`

Acceptance criteria verification:

| Criterion | Verification | Pass |
|---|---|---|
| `omni check source/api_client.omni` exits 0 | `python -m omni_compiler.cli check source\api_client.omni` → `omni check: OK`, EXIT=0 | PASS |
| Capability model enforces declared network usage | `inspect fetch_users` shows `uses:["network"]`; missing-declaration probe → E-EFFECT-003 (EXIT=1); app-block direct http call → E-EFFECT-003 (EXIT=1); `classify_error` is pure (uses:[]) | PASS |
| All tests pass | `python -m pytest -p no:cacheprovider ...\tests\test_api_client.py` → **18 passed, 0 failed** (3.49s) | PASS |
| `omni run` behavior investigated | Confirmed run COMPILES AND EXECUTES under Node (`scripts/run-omnisys.js`), forwards `show` output, exit 0; `build --target js` emits a self-contained HTML with inlined OMNISYS JS; `check` = tokenize→parse→analyze→MIR | PASS |

Execution efficiency:
- ~16 compiler invocations (check/run/build/inspect/explain/verify/generate + probes), ~13 Node harness runs, one pytest run. All verification completed in a single session.
- Effort was dominated by probe-driven discovery of 7 non-obvious language/compiler behaviors (see ECOSYSTEM_RESULT), not by writing the ~180-line program.

Invalid assumptions encountered (all corrected in-session, recorded in BENCHMARK_REASONING.md):
1. Assumed `and`/`or` logical operators exist (spec §6.3 documents them; lexer tokenizes them) — the parser never implements them. Rewrote with nested `if`.
2. Assumed locals assigned inside functions get emitted `let` declarations — the emitter suppresses any name that is a parameter of ANY function, causing strict-mode `ReferenceError`s (`res`, `payload`, `elapsed`). Renamed locals to avoid collisions.
3. Assumed decoded JSON can be field-accessed into structs — `E-TYPE-002` rejects field access on "unknown" typed values. Adopted typed-parameter re-wrapping idiom.
4. Assumed `import OMNISYS` implicitly provides `omnisys.core.*` — checker demands explicit `import OMNISYS.core` (E-IMPORT-003).
5. Assumed `OMNISYS.http` was missing (TASK.md STATUS: BLOCKED) — the registry already ships it; docs lag behind the registry (READMEs say "planned").
6. Assumed the app block could call http functions — E-EFFECT-003; the entry block must delegate to declared network functions.
7. Assumed braces in Text literals are fine — the emitter treats `{...}` as interpolation slots; `{"id":1}` becomes broken JS. Avoided JSON literals in source.

## RE-VERIFICATION (session continuation, 2026-08-18)

The compiler was modified during parallel runs (sibling run 2.4 and sub-agents): `omni run` now EXECUTES
programs under Node instead of being compile-only, and the emitter now emits function-scope `let` locals
(excluding entry-point module names). Re-verified under the FINAL compiler state:

- `omni check` → OK, EXIT=0; `omni run` → executes, EXIT=0.
- pytest → **18 passed, 0 failed**. Two fixes were required to reach this state, both test-harness-level,
  not source-level:
  1. `tests/node_driver.js` document shim lacked `addEventListener`; the emitted runtime unconditionally
     wires UI event delegation (`document.getElementById("app").addEventListener(...)`) even for a non-UI
     program, so every artifact load threw. Added `addEventListener() {}` to the `getElementById` stub.
  2. `test_run_passes` asserted the old compile-only banner `"omni run: OK"`; updated to assert execution
     (exit 0, non-empty program output).
- Emitter note: the earlier "module-scope `needed − param_names`" defect finding is superseded — the emitter
  now scopes locals to each function and treats entry-point-assigned names as module state (a name written by
  a function that was pre-declared at the entry point updates the module variable instead of shadowing it).
  The run's program was already written to avoid name collisions, so no source change was needed.

## ECOSYSTEM_RESULT

### API (OMNISYS)
- `OMNISYS.http` and `OMNISYS.net` are SHIPPED in the registry and JS runtime (v6), contradicting TASK.md's "Missing / BLOCKED" status. Registry surface: `client/send/get/post/put/delete/json_get/json_post` (network effects) + `redirect/not_found` (pure). JS also defines `response/response_json/register/__registerInproc/__parseUrl` that are NOT in the registry (unusable from OmniScript).
- Transport model: `inproc://host/path` dispatches to registered in-process servers (deterministic, synchronous, testable); any other scheme requires `http.__transport` (JS escape) or panics. No real wire HTTP/TCP transport exists.
- API gaps for this mission: no headers parameter on `http.get/post/send`; no timeout parameter anywhere in http/net; `json_get/json_post` discard status (return parsed body only); `http.send` takes a client but the client is a placeholder tag object; `status_of/body_of` exist on `net` but are not mirrored on `http` in the registry.
- `OMNISYS.serde` (`json_encode/json_decode`, etc.) is declared PURE — there is no capability token for serialization; nothing to declare at function boundaries (finding for the "serialization side-effects" requirement).

### Language
- Effect system (§8): `uses/reads/writes/pure` at function top; enforcement is transitive only inside function bodies (`inherit=True`), NOT in the app block. App block can call declared network functions but not `omnisys.http.*` directly (E-EFFECT-003). No `uses` declarations allowed on `when app starts` itself.
- No `any` type; call results type as "unknown"; field access requires a declared custom type (E-TYPE-002). No static argument/arity type checking — enables the typed-parameter re-wrapping idiom for JSON deserialization.
- `for` loop variable is hard-typed `Number` in the checker, so field access on loop items is statically rejected (same wrapper idiom needed).
- Logical `and`/`or` operators are documented (spec §6.3) and tokenized but NOT parsed — silent gap.
- Text interpolation `{expr}` is the only string builder and also the HTML slot mechanism; literal `{`/`}` in Text is unsafe.
- `for item in <list>` is the only iteration; `List` items are untyped.
- No try/catch/finally, no await, no async primitives in the grammar.

### Compiler
- `run` compiles AND executes under Node (forwards `show` output, exit 0); `build --target js` emits a self-contained HTML with inlined OMNISYS JS; `check` = tokenize→parse→analyze→MIR.
- **Emitter defect (high severity):** module-scope `let` declarations are `needed − param_names`; a local assigned inside a function whose name collides with any parameter is undeclared → strict-mode `ReferenceError` at runtime while `omni check` still passes. (Verified for `res`, `payload`, `elapsed`; workaround = rename locals.)
- Call names emitted verbatim: lowercase `omnisys.*` resolves against the inlined runtime; uppercase `OMNISYS.*` passes the checker but is undefined at runtime.
- `omni build --target js` does not create the output directory (FileNotFoundError on missing parent).
- Custom-type JSDoc emission is malformed (`// interface User { //   fields: {...} }` instead of per-field lines) — cosmetic.
- `build --target c/rust/wasm-*` rejects any OMNISYS import with E-BACKEND-001 + automatic "use --target js" fix (§8.3 per-back-end check works).

### Diagnostic
- Rich `omni.diagnostic` JSON: code, category, severity, message, details, span, location, context, machine-actionable `fixes` (automatic `add_declaration` inserting `uses network`; `replace_span` for E-BACKEND-001).
- Errors carry concrete, model-actionable fixes. `explain`/`suggest`/`generate` commands exist; `verify` reports `no-contracts` for functions without require/ensure (exit 0); `generate` drafts AST-walking pytest stubs (does not execute).
- Negative probes verified: E-EFFECT-003 (undeclared network), E-TYPE-002 (field access on unknown), E-IMPORT-003 (module not imported), E-SYNTAX-001 (parser gap), E-NAME-001 (unknown function e.g. `http.register`).

### Documentation
- `docs/omnisys/http|net/README.md` are STALE: status "planned", public API sketch (`fn get(url) -> Result`) does not match the shipped registry surface. `docs/CAPABILITY_MATRIX.md` and module docs lag the registry. OMNI_SPEC §17 (v6 OMNISYS charter) matches the registry better than the per-module READMEs.

### Capability/Effect
- Enforcement is real and transitive inside functions: calling `omnisys.http.get` without `uses network` fails E-EFFECT-003; `pure` functions cannot do network work (E-EFFECT-001). The auto-fix text is inserted verbatim.
- Backends: only the JS lane provides OMNISYS; native targets are blocked at compile time.
- Observed wrinkle: functions declared with `uses network` are emitted `async`, but the language has no `await`, so any app-level call receives an un-observable Promise; a panicking network call in the app block becomes an unhandled promise rejection (Node crashes). Network programming is only drivable from an external harness (or would need an `await`-capable host).

### Backend (JS runtime)
- Runtime verified in Node v24 via `vm.runInContext` with DOM stubs: pure functions (request construction, serde, classification, typed parsing) execute correctly; `inproc://` stub servers drive `fetch_users`/`create_user` end-to-end (200→ok, 404→not_found, POST body routing, slow-server→timeout); unknown-host calls panic ("no transport").
- `__registerInproc`/`__parseUrl`/`__transport` are harness hooks only — invisible to OmniScript source.
- `platform.now()` = `Date.now()` (pure) enables measured timeout enforcement.

### Positive Discoveries
1. `OMNISYS.http`/`OMNISYS.net` already ship in v6 — TASK.md's BLOCKED status is stale; the benchmark is actually runnable.
2. The `inproc://` in-process transport is a clean, deterministic, testable HTTP client/server seam.
3. The effect checker with automatic fixes is genuinely usable and catches undeclared network I/O at compile time.
4. The typed-parameter re-wrapping idiom provides a sound (if indirect) path for deserializing JSON into declared structs without adding `any`.
5. `inspect` returns the full typed/effect symbol record, enabling programmatic capability auditing.
6. Backend capability gating (E-BACKEND-001) cleanly prevents silently broken native builds.
7. Diagnostics are machine-actionable JSON throughout (check/inspect/verify/explain), consistent with the AI-first design goal.

### Proposed Changes
1. Emitter: declare function-scope locals with `let` (or `var`) inside each emitted function instead of the module-scope `needed − param_names` heuristic (fixes the `ReferenceError` defect class).
2. Emitter/parser: implement `and`/`or` (§6.3) or explicitly reject them with a diagnostic (currently a confusing `Expected COLON, got 'and'`).
3. Registry: surface `http.register` / `http.response` / `http.response_json` as first-class OMNISYS functions so `inproc://` server registration is expressible in the language (enables in-language testing and removes the harness-only escape).
4. API: add optional headers and timeout parameters to `http.get/post/send` (or a `with_headers`/`with_timeout` builder) to close the mission's request-formatting and timeout requirements at the API level.
5. Language: add try/catch (or a `decode_checked` serde function returning a Result/Option) so malformed-payload handling does not require pre-decode heuristics.
6. Docs: regenerate `docs/omnisys/*` READMEs and CAPABILITY_MATRIX from the registry; mark TASK.md status as runnable.
7. Add `await` (or promise-flattening in the emitter for synchronous calls) so `uses network` functions are observable from the app entry block.