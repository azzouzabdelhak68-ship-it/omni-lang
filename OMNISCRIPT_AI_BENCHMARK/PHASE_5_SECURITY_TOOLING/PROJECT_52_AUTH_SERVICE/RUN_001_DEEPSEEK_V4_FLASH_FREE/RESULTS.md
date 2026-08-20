# RESULTS — Phase 5 Project 5.2: Authenticated Web Service

## MODEL_RESULT

### Task Completion Status: ✅ COMPLETE

**Summary**: Built a full authenticated web-service program (`source/auth_service.omni`) on the v6 OmniScript compiler using the `OMNISYS.auth`, `OMNISYS.crypto`, `OMNISYS.collections`, `OMNISYS.platform`, and `OMNISYS.serde` modules. It delivers:

1. **Registration** — users stored with `salt$kdf-hash` (never plaintext); duplicate usernames rejected (409).
2. **Login** — password verified against the stored hash; unknown users and wrong passwords rejected (401); success issues a JWT-style signed token.
3. **Tokens** — issue (`omnisys.auth.token` with role + expiry claims), verify (`omnisys.auth.verify_token` + service-side signature/expiry/revocation checks).
4. **Authorization** — protected `/profile` (any authenticated user) and `/admin` (admin-role only, 403 otherwise); unauthenticated access rejected with status 401.
5. **Logout** — presented token added to a revocation set; later verification returns `token revoked` (401).
6. **Sessions** — `omnisys.auth.session_new` / `session_valid` exercised; valid and expired sessions reported correctly.
7. **Capability composition** — all 9 service functions declare `uses secrets` at their boundaries; `omni check` enforces this (E-EFFECT-003 for any missing declaration).

### Execution Efficiency
- `omni check` exits 0 (single pass; no warnings).
- `omni build` (target js) emits a self-contained HTML artifact.
- `omni verify` exits 0 — 9 functions, all `no-contracts`.
- `omni run` executes the full demo under Node (exit 0).
- **pytest: 27/27 passed in ~9.8s** (compiler acceptance, capability-declaration inspection via `omni inspect`, and runtime behavioral tests driving the emitted JS under a DOM-stub harness).

### Invalid Assumptions Encountered
1. **Sibling 5.5 ledger claimed empty map literal `{}` is rejected by the parser.** Probing the current compiler shows `{}` parses, checks, and emits fine (`probe_01`). Assumption invalidated — the 5.5 finding is stale or was a misdiagnosis.
2. **Sibling 5.5 ledger claimed custom struct field access fails on function returns (E-TYPE-002).** `probe_02` shows user-function struct returns DO support `.field` access on the current compiler. (The limitation remains only for OMNISYS call results, which resolve to `unknown`.)
3. **Token expiry via `omnisys.auth` alone.** `verify_token` validates signature only; `auth.token` auto-adds `sub`/`iat` but not `exp`. Expiry had to be implemented by the service using a claims-based `exp` compared against `platform.now()/1000` (note `platform.now()` returns **milliseconds** while `auth.token`/`session_new` timestamps are **seconds**).
4. **Immutable-style store threading.** `omnisys.collections.map_set` mutates the map in place and returns the same reference — "returns the updated store" is alias-based. A test wrote the logout revocation into the shared store before the profile check (order bug); fixed in the test. Documented as an ecosystem finding.

---

## ECOSYSTEM_RESULT

### API Findings
| Aspect | Finding |
|--------|---------|
| `OMNISYS.auth` | **IMPLEMENTED** (TASK.md "Missing" status is stale): `token(Text, Map, Text)->Text`, `verify_token(Text, Text)->Map`, `token_subject`, `hash_password`, `verify_password`, `session_new`, `session_valid` — all tagged `uses secrets` |
| Token format | Compact 2-part `base64url(payload).hmac-sig` signed token (JWT-style); header-less, self-describing claims |
| `verify_token` scope | Signature-only validation; returns `{valid, sub, claims}`; expiry/role are the caller's responsibility |
| `OMNISYS.crypto` | `sha256`/`hmac`/`to_hex`/`from_hex` pure; `random_bytes` `uses secrets`; `kdf`, `constant_time_eq` backing `auth.hash_password` |
| `OMNISYS.platform.now()` | Pure; returns `Date.now()` (ms) — mismatches the seconds used by auth timestamps |
| `OMNISYS.http`/`net` | Exists; `inproc://` in-memory dispatch, real transports require a registered escape. Not exercised for real networking |
| `token_subject` | Present but self-defeating: calls `verify_token(token, "")` with an empty secret, so real tokens never verify through it |

### Language Findings
| Aspect | Finding |
|--------|---------|
| Empty map literal `{}` | **Valid** (parser `parse_map_literal` accepts it) — contradicts the 5.5 ledger |
| Map write | `m["k"] = v` is NOT an assignment target; use `omnisys.collections.map_set` |
| Map mutation semantics | `map_set`/`list_push` mutate in place AND return the same reference (aliasing) |
| Struct returns | User-fn struct returns resolve to the declared type → `.field` access works (E-TYPE-002 only applies to OMNISYS calls / `unknown`) |
| Struct field types | Restricted to Number/Text/Boolean/List/None — a `Map` field is rejected (E-TYPE-001) |
| `uses secrets` | Required in any fn calling a secrets-tagged OMNISYS fn (E-EFFECT-003 if missing; E-EFFECT-001 if the fn is `pure`) |
| App block capabilities | The `when app starts:` block has NO effect-clause syntax — it can never directly call secrets-tagged functions; wrapper functions are mandatory |
| Capability inheritance | Function→function: caller must declare the caps its callees declare (verified via delegation of `svc_issue_token` from `svc_login`) |
| Module-scope names | Names assigned in the app block are module-scope; functions touching them need `reads`/`writes` declarations (E-EFFECT-004) |
| `result` keyword | Reserved inside functions; service avoids it (uses explicit result maps) |

### Compiler Findings
| Aspect | Finding |
|--------|---------|
| `omni check` | Full tokenize→parse→analyze→MIR; exit 0 on success; JSON diagnostic on failure |
| `omni inspect <fn>` | Emits `declared_effects.uses` — enables machine-checked capability-declaration tests |
| `omni verify` | SMT prover proves simple arithmetic require/ensure (`status: verified`, probe_05a); no contracts → `no-contracts` |
| `omni build` | JS target inlines imported OMNISYS runtime dependency-ordered; native targets reject omnisys-calling programs (E-BACKEND-001) |
| `omni run` | Runs emitted HTML under Node with DOM stubs; real auth flows execute correctly (exit 0) |
| Auto-fix diagnostics | E-EFFECT-003 proposes `uses secrets` — but the app block fix is unapplicable (no syntax slot), misleading in that context |

### Diagnostic Findings
- E-EFFECT-003: `Capability secrets used without declaration.` — precise, includes the offending function name and an applicable (for functions) auto-fix.
- E-EFFECT-001: `Function declared 'pure' but uses ['secrets']` — cleanly catches a pure function delegating to a secrets function.
- Diagnostics carry `schema: omni.diagnostic`, `location`, `context`, `fixes` — machine-readable for test assertions.

### Capability/Effect Findings
| Aspect | Finding |
|--------|---------|
| Composition model | `secrets` composes cleanly: multiple capabilities can be declared per boundary (`uses secrets` suffices here; `network`/`database` would be additive) |
| Pure helpers under `uses secrets` | Legal: pure OMNISYS calls inside a secrets fn do not add other capabilities |
| Enforcement | Per-function and per-app-block; app block is the weak spot (no declaration syntax) |
| No undeclared side-effects | `omni check` guarantees every `auth`/`crypto` call is declared; verified by tests via `omni inspect` |

### Backend Findings
| Backend | Status |
|---------|--------|
| JS lane (Node) | Full auth pipeline works: hashing, signing, verification, expiry, revocation, sessions |
| DOM-stub harness | Emitted functions attach to globalThis via `vm.runInThisContext` → directly driveable from test epilogues |
| Native (C/Rust/WASM) | Blocked for OMNISYS-calling programs (E-BACKEND-001); auth would need a native OMNISYS runtime |

### Documentation Findings
- TASK.md STATUS `BLOCKED` is **stale**: `OMNISYS.auth` is registered and fully runtime-functional.
- 5.5 run ledger contains two stale findings (`{}` rejected; struct field access on fn returns rejected) — contradicts current compiler behavior.
- No per-module README for `auth`/`crypto` runtime semantics; the ms-vs-seconds timestamp mismatch and signature-only `verify_token` are undocumented and had to be discovered from `omnisys/auth.js` + `platform.js`.

### Positive Discoveries
1. `OMNISYS.auth` + `crypto` compose into a complete, runtime-working authentication service in ~200 lines — capability composition across modules works end to end.
2. `omni inspect` enables mechanical verification of capability declarations in tests.
3. `omni verify`'s SMT prover does prove contracts (`verified`), not just `no-contracts`.
4. `omni run` / the DOM-stub harness gives a real runtime test loop for OMNISYS programs (no test double needed).
5. Map literals + `map_get`/`map_set` give a workable JSON-shaped data layer for service results.

### Proposed Changes
| Priority | Change | Rationale |
|----------|--------|-----------|
| HIGH | Add `exp` verification to `omnisys.auth.verify_token` (and honor it) | Expiry is core to token auth; today it's entirely service-side |
| HIGH | Fix `omnisys.auth.token_subject` (verify against the caller-provided secret, not `""`) | Currently self-defeating for real tokens |
| MEDIUM | Allow `Map` as a struct field type | Forces Map-result-only service patterns; structs can't carry a store |
| MEDIUM | Give the app block an effect-clause (or auto-inherit callee caps) | The only boundary that cannot declare capabilities; E-EFFECT-003's auto-fix is unapplicable there |
| MEDIUM | Align `platform.now()` units with auth timestamps (or add `now_seconds()`) | ms-vs-seconds mismatch is a silent trap |
| MEDIUM | Support map-index assignment `m["k"] = v` | Common, natural operation; currently a syntax error |
| LOW | Update TASK.md 5.2 status and 5.5 ledger stale claims | Both misdescribe the current compiler |

---

## Verification Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| `omni check` exits 0 | ✅ | `omni check: OK — auth_service.omni` |
| `omni build` succeeds | ✅ | wrote `source/auth_service.html` (target=js) |
| `omni verify` clean | ✅ | 9 functions, all `no-contracts` |
| Protected endpoints reject unauthenticated | ✅ | `profile (anonymous)` → 401; `admin (bob)` → 403 |
| Wrong password rejected | ✅ | 401 `wrong password` |
| Expired token rejected | ✅ | 401 `token expired` (negative-TTL token) |
| Logout/revocation | ✅ | 401 `token revoked` after logout |
| Sessions | ✅ | `session valid` / `session expired` |
| All tests pass | ✅ | **27 passed in 9.76s** |

## Files Produced

```
RUN_001_DEEPSEEK_V4_FLASH_FREE/
├── BENCHMARK_REASONING.md        # Investigation ledger (probes, raw outputs, rules)
├── RESULTS.md                    # This summary
├── probes/                       # 8 probe .omni files + results (see ledger)
├── source/
│   ├── auth_service.omni         # Main service program (10 functions + entry demo)
│   └── auth_service.html         # Build artifact (target=js)
└── tests/
    └── test_auth_service.py      # 27 tests (compiler + capability + runtime)
```