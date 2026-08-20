# BENCHMARK REASONING LEDGER — Phase 5 Project 5.2: Authenticated Web Service (RUN_001_DEEPSEEK_V4_FLASH_FREE)

> Continuous observable research ledger. Written as investigation happened; not polished retroactively.

## 0. Mission & Starting State

Read `PROJECT_52_AUTH_SERVICE/TASK.md` (STATUS: BLOCKED, claims `OMNISYS.auth` missing). Read sibling `PROJECT_55_NATIVE_INTEROP_ESCAPE_HATCH/RUN_001_CLAUDE_3_5/` (BENCHMARK_REASONING.md, RESULTS.md, source, tests) to mirror structure/conventions.

**Given facts (verified before starting):** `OMNISYS.auth` IS registered (token, verify_token, token_subject, hash_password, verify_password, session_new, session_valid — all `uses secrets`). `OMNISYS.crypto` (sha256/hmac/to_hex/from_hex pure; random_bytes secrets). `OMNISYS.platform.now()` pure. `OMNISYS.collections` map/list helpers pure.

## 1. Files Inspected

- `omni_compiler/omnisys_registry.py` — full OMNISYS module/function/effect table (lines 64–484). Auth module at lines 410–421: all fns `secrets`. Crypto at 395–409: `random_bytes` secrets, rest pure. `platform.now` pure. `serde.json_encode` pure.
- `omnisys/auth.js` — token = b64url(JSON).sig (2-part "compact signed token"), verify_token returns `{valid, sub, claims}`, hash_password = `salt$kdf(password,salt,128)`, session_new/session_valid.
- `omnisys/crypto.js` — sha256/hmac/kdf/constant_time_eq; nodeCrypto used when available.
- `omnisys/core.js`, `omnisys/collections.js` (map_get/map_set/map_has mutate + return same object), `omnisys/platform.js` (`now()` = `Date.now()` MILLISECONDS), `omnisys/http.js` (inproc:// in-memory dispatch, no real TCP).
- `omni_compiler/checker.py` — effect enforcement: `enforce_app_block_effects` (declared uses empty; `inherit=False`), `enforce_function_effects` (`inherit=True`), `_walk_call` (omnisys_effects added to `actual`; callee declared uses inherited only when `inherit=True`), `_enforce` E-EFFECT-001/003/004/010/011/012, `_walk_expr_data_access` (E-EFFECT-004 module-scope reads/writes), `_assigned_names_ast` (app block names = module scope), `_resolve_type_of` (user fn calls resolve return type via symbol table; OMNISYS calls -> 'unknown'), custom struct field types restricted to {Number, Text, Boolean, List, None}.
- `omni_compiler/parser.py` — `parse_map_literal` accepts `{}` (empty) and `{k: v}`; named-arg `Name(field = v)` = StructConstruct; `parse_function` effects clauses; `global` keyword.
- `omni_compiler/emitter.py` — `_omnisys_runtime` inlines imported module JS dep-ordered; `_js_expr` map -> JS object, struct -> JS object, `show` -> console.log; `emit_js` module-scope names as top-level `let`; functions attach at top level (vm.runInThisContext => globalThis).
- `omni_compiler/cli.py` — check/build/run/verify/inspect; build default output `source/<stem>.html`; `_reject_omnisys_on_native_target` (E-BACKEND-001) for native targets.
- `tests/test_emitter.py` `_run_emitted` — Node DOM-stub harness pattern (harness + epilogue + JSON logs).
- `scripts/run-omnisys.js` — `omni run` Node runner with DOM stubs.

## 2. Questions & Hypotheses (initial)

1. Is `OMNISYS.auth` actually usable? (TASK.md says BLOCKED/Missing.)
2. Does empty map literal `{}` parse? (5.5 ledger claimed "parser rejects".)
3. Do struct-typed function results allow `.field` access? (5.5 claimed E-TYPE-002.)
4. How does `uses secrets` enforcement behave for functions vs the app block?
5. Can the emitted JS actually execute auth flows under Node (`omni run` / DOM-stub harness)?
6. How is expiry encoded/checked given `auth.token` adds only `sub`+`iat`, and `platform.now()` returns ms while `auth.session_new` uses seconds?
7. Module-scope name collisions: app-block-assigned names trigger E-EFFECT-004 reads/writes inside functions.

## 3. Probes & Raw Outputs (each probe in `probes/`)

### Probe 1 — `probe_01_empty_map.omni` (empty `{}`, `{k: v}`, map_get/map_set/map_has/map_keys)
```
> python -m omni_compiler.cli check probes/probe_01_empty_map.omni
omni check: OK — probe_01_empty_map.omni
EXITCODE=0
```
**Interpretation:** Empty map literal `{}` PARSES AND CHECKS on the current compiler. The 5.5 ledger claim ("parser rejects empty map literal") is STALE/incorrect for this compiler version (parse_map_literal explicitly accepts `{}`). Decision: use map literals freely.

### Probe 2 — `probe_02_struct_field.omni` (struct return + `.ok`/`.message` field access)
```
omni check: OK — probe_02_struct_field.omni
EXITCODE=0
```
**Interpretation:** Custom struct returns DO support field access on the current compiler (`_resolve_type_of(FunctionCall)` resolves user-fn return types). 5.5's E-TYPE-002 claim is stale for user functions (it remains true for OMNISYS calls which resolve to 'unknown'). Decision: structs are usable, but I chose Maps for results to carry the store + status uniformly (Map fields are NOT allowed in `type` declarations — field types restricted to Number/Text/Boolean/List/None — so structs cannot embed a store).

### Probe 3 — secrets capability enforcement (3 files)
`probe_03a_no_secrets.omni` (fn calls `omnisys.auth.hash_password` with NO declaration):
```
{
  "code": "E-EFFECT-003",
  "message": "Capability secrets used without declaration.",
  "details": "bad_hash performs secrets I/O but declares no capability for it.",
  ...auto-fix: add "    uses secrets"
}
EXITCODE=1
```
`probe_03b_with_secrets.omni` (fn declares `uses secrets`, called from app block):
```
omni check: OK — probe_03b_with_secrets.omni
EXITCODE=0
```
`probe_03c_app_direct.omni` (app block calls `omnisys.auth.hash_password` DIRECTLY):
```
{
  "code": "E-EFFECT-003",
  "message": "Capability secrets used without declaration.",
  "details": "app starts performs secrets I/O but declares no capability for it.",
  ...auto-fix: add "    uses secrets"  (but the app block has no effect-clause syntax)
}
EXITCODE=1
```
**Interpretation:** (a) functions need `uses secrets` to call secrets-tagged OMNISYS fns; (b) app block CANNOT declare capabilities — the auto-fix text cannot even be applied. Rule confirmed: wrap ALL capability-using logic in named fns declaring `uses secrets`; app block calls the wrappers (calls to functions are NOT inherited into app block's `actual` because `inherit=False`). Also probed E-EFFECT-001 (probe_05b): `pure` fn calling a `uses secrets` fn → "Function declared 'pure' but uses ['secrets']", EXITCODE=1.

### Probe 4 — `probe_04_token_flow.omni` (full token issue/verify/expiry)
```
> python -m omni_compiler.cli check probes/probe_04_token_flow.omni
omni check: OK — probe_04_token_flow.omni
EXITCODE=0

> python -m omni_compiler.cli run probes/probe_04_token_flow.omni
token: eyJzdWIiOiJhbGljZSIsImlhdCI6MTc4NzE3MzMwOSwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzg3MTc2OTA5LjA0fQ.c58b6ba6879d5c1bbcbbe280
verify good: OK: alice
verify stale: ERROR: expired
verify bad: ERROR: invalid
EXITCODE=0
```
**Interpretation:** Full runtime works under Node. `verify_token` checks signature only; expiry must be implemented by the SERVICE (compare `claims.exp` to `platform.now()/1000`). Negative TTL gives a deterministic expired token. This unlocked runtime behavioral tests.

### Probe 5 — contracts (verify) + pure enforcement
`probe_05a_contracts.omni` (`require a greater than 0`, `ensure result greater than 0`):
```
> python -m omni_compiler.cli verify probes/probe_05a_contracts.omni
... "function": "add_positive", "status": "verified"
EXITCODE=0
```
`probe_05b_pure_violation.omni`: E-EFFECT-001 (see Probe 3 interpretation).
**Interpretation:** The SMT contract prover DOES prove simple arithmetic require/ensure (status "verified", not "no-contracts"). Positive discovery. Main program keeps no contracts (all `no-contracts`), consistent with sibling runs; contract demo recorded here as evidence.

## 4. Architecture & Code Decisions

**Goal:** registration/login, JWT-style token issue + verify w/ expiry, password hashing (never plaintext), role/access enforcement on protected endpoints, logout (revocation), sessions, and `uses secrets` declarations at EVERY function boundary.

1. **Pure-functional store threading.** In-memory store = Map `{__revoked__: [], <username>: {salt, hash, role}}`. Map index WRITE `m["k"] = v` is a syntax error (INDEX read `m["k"]` is fine; WRITE is not — the parser only supports `[` for expression, assignment target must be a bare identifier), so the service mutates via `omnisys.collections.map_set` and returns the updated store in the result Map. This also avoids E-EFFECT-004 module-data `reads`/`writes` declarations (module-scope state would require declaring `reads users`/`writes users` per function). REJECTED alternative: `global` module-state store (E-EFFECT-004 friction + alias semantics).
2. **Maps for results**, not structs: results need `store` (a Map) which can't be a struct field type. `{ok, status, message, token, subject, role, store}` maps.
3. **Expiry.** `svc_issue_token` builds claims `{role, exp: platform.now()/1000 + ttl}`; `svc_verify` checks `now_sec > exp` after signature verification. Handles the ms-vs-seconds mismatch explicitly.
4. **Revocation.** `svc_logout` pushes token into `__revoked__` list; `svc_verify` rejects revoked tokens first.
5. **Capability boundaries.** All 9 service functions declare `uses secrets` (they call `omnisys.auth.*`/`crypto.random_bytes` directly or delegate to another secrets fn). Pure helpers (`map_get`, `map_has`, `json_encode`, `platform.now`) used inside them are fine under `uses secrets`.
6. **App block** only calls named service functions and `show`s JSON (never touches secrets directly — E-EFFECT-003 otherwise).
7. **Runtime tests** drive emitted JS via a DOM-stub harness (mirror of `tests/test_emitter.py::_run_emitted`): `vm.runInThisContext` places emitted functions on globalThis, so an epilogue calls `svc_*`/`endpoint_*` directly with a fresh store and returns JSON through a `__OUT__` log line. No direct compiler imports in the test (pure subprocess + node), so `python -m pytest tests/` works from the run dir.

## 5. Errors Encountered & Interpretations (during test bring-up)

**Bug 1 — 2 pytest failures (`test_protected_endpoint_authorizes_authenticated`, `test_role_based_access_control`).**
Symptom: profile returned `401 "token revoked"` and admin returned `401` in the harness, while the entry-block demo worked.
Debug: built `probes/_dbg.html`, ran a node harness calling the emitted functions directly — profile WAS `{ok:true, status:200}`. Replicated the EXACT test epilogue → `profileOk: {ok:false, status:401, message:"unauthorized: token revoked"}`.
Root cause: `omnisys.collections.map_set` MUTATES the map in place and returns the same object. `svc_logout(reg.store, ...)` therefore mutated the shared `reg.store`, adding `loginOk.token` to `__revoked__` BEFORE the profile/admin checks ran. My test epilogue order was wrong, and my admin expectation was also wrong (`tester` was registered with role `user`, so admin SHOULD be 403).
Fix: reorder epilogue (profile/admin checks before logout), register a separate `boss` (admin) for the grant path and assert `tester` (user) gets 403.
Ecosystem note: "returns updated store" is aliased mutation at runtime — callers must treat store threading as order-sensitive.

**Race 1 — a `probe_03c_app_direct.omni` write vanished** while two bash checks ran in parallel; re-wrote the file, re-checked, got the expected E-EFFECT-003.

## 6. Discovered Language / Compiler Rules (verified by probes + source)

- Empty `{}` map literal: VALID (parser accepts; contradicts 5.5 ledger).
- `{k: v}` map literal → JS object; read via `map_get`/`m["k"]`; WRITE via `map_set` ONLY (`m["k"] = v` as assignment target is invalid).
- `omnisys.collections.map_set` mutates AND returns same ref (aliasing).
- Struct-typed user-function returns support `.field` access; OMNISYS fn returns resolve to 'unknown' (field access on those fails → use map_get).
- `uses secrets` required in any fn calling a secrets-tagged OMNISYS fn; undeclared → E-EFFECT-003; pure + secrets → E-EFFECT-001.
- App block has NO effect-clause syntax: direct secrets call → E-EFFECT-003 on "app starts"; auto-fix unapplicable. Wrapper functions are the ONLY way.
- Function → function capability inheritance (`inherit=True`): caller must declare caps its callees declare.
- Names assigned in the app block become module scope → E-EFFECT-004 (`reads <name>`/`writes <name>`) inside functions. Avoid by not touching module names in fns.
- `platform.now()` = ms; `auth.session_new`/`auth.token` iat/expiresAt = seconds. Convert `now()/1000`.
- `auth.verify_token` checks signature only — expiry/role checks are the service's job.
- `omni verify` proves require/ensure (e.g. simple arithmetic → status "verified"); no contracts → "no-contracts".
- `omni run` executes emitted JS under Node (DOM stubs); build default target `js` writes `source/<stem>.html`.
- `omni inspect <fn>` reports `declared_effects.uses` — usable to assert capability declarations in tests.
- Native targets (c/rust/wasm) reject programs that CALL omnisys fns (E-BACKEND-001); JS lane is the reference backend.

## 7. Alternatives Considered & Rejected

- **`global` module-state store**: rejected — E-EFFECT-004 declarations on every function + aliasing confusion; functional threading is cleaner and check-passing.
- **Struct `AuthResult` with a `store` field**: rejected — `Map` is not a valid struct field type (E-TYPE-001).
- **`OMNISYS.http` inproc server for real endpoint simulation**: rejected for the main flow — http/net need `uses network`, and in-proc dispatch still requires the app to drive requests; endpoint functions with explicit stores demonstrate the same authorization semantics more directly. Noted as future composition work.
- **Direct compiler imports in tests** (`from omni_compiler.emitter import emit_js`): rejected — pytest runs from the run dir where omni_compiler isn't importable; subprocess+node keeps tests self-contained.
- **Asserting on the fixed demo stdout only**: rejected in favor of the epilogue harness which drives the service with arbitrary inputs.

## 8. Unresolved Questions

- Whether `omnisys.auth.token_subject` is usable (it calls `verify_token(token, "")` with an empty secret — signature check would fail for real tokens). Not needed by the service; documented as an ecosystem finding.
- Whether `OMNISYS.http`/`OMNISYS.net` provide a real transport outside `inproc://` (registry shows http client requires `uses network` + registered transport). Untested for real networking.
- How `omni verify` behaves for contracts over Maps/imperative state (probed only arithmetic contracts).

## 9. Final Verification (raw outputs)

- `python -m omni_compiler.cli check source/auth_service.omni` → `omni check: OK — auth_service.omni`, EXITCODE=0.
- `python -m omni_compiler.cli build source/auth_service.omni` → `omni build: wrote .../source/auth_service.html (target=js)`, EXITCODE=0.
- `python -m omni_compiler.cli verify source/auth_service.omni` → schema omni.verify.batch; 9 functions, all `no-contracts`, EXITCODE=0.
- `python -m omni_compiler.cli run source/auth_service.omni` → full demo: register (201), duplicate (409), login (200+token), wrong password (401), unknown user (401), profile alice (200), anonymous (401 invalid signature), admin alice (200 granted), admin bob (403 forbidden), expired (401), logout + revoked (401), sessions valid/expired. EXITCODE=0.
- `python -m pytest tests/ -q` (from run dir) → `27 passed in 9.76s`.