# BENCHMARK_REASONING — Project 2.3 HTTP/REST API Client

Model: deepseek-v4-flash-free (opencode)
Run dir: `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE`
Start: 2026-08-17

This file is a LIVE research ledger. Entries are chronological; nothing is rewritten after the fact.

---

## 1. Task intake (from TASK.md)

Mission: external REST API integration client — format requests (GET/POST, query strings, headers, JSON bodies), deserialize typed responses, handle errors/timeouts, respect capability declarations.

Deliverables (inside run dir):
1. `BENCHMARK_REASONING.md` (this file)
2. `source/api_client.omni`
3. `tests/test_api_client.py` (stubbed responses)
4. `RESULTS.md` (MODEL_RESULT + ECOSYSTEM_RESULT)

Acceptance:
- `omni check source/api_client.omni` exits 0 (CLI is `python -m omni_compiler.cli check ...`)
- capability model correctly enforces declared network usage
- all pytest tests pass

TASK.md status metadata says STATUS: BLOCKED — "Missing: OMNISYS.http". Discovery question #1: is that stale? The registry (v6) already contains `OMNISYS.http` and `OMNISYS.net`. Need to verify empirically.

## 2. Infrastructure recon (what the harness told me + what I read)

Operational facts (given, not discovered):
- Compiler CLI: `python -m omni_compiler.cli <check|run|build|inspect|explain|verify|suggest|generate|trace>`
- `import OMNISYS.<module>` is the stdlib import model
- Registry: `E:\simualtion\omni_compiler\omnisys_registry.py`
- JS impls: `E:\simualtion\omnisys\*.js`
- Spec: `E:\simualtion\OMNI_SPEC.md`; docs under `E:\simualtion\docs\`
- Files must be UTF-8 without BOM.

What I inspected:
- `TASK.md` (read fully) — see §1.
- `omnisys_registry.py` (read fully, 521 lines). Findings:
  - `OMNISYS.http` EXISTS in the registry. Module deps: `("core", "net")`. All 10 http functions are declared with `effects = {"network"}`: `client`, `send`, `get`, `post`, `put`, `delete`, `json_get`, `json_post`, `redirect`, `not_found`.
  - `OMNISYS.net` EXISTS. deps `("core","collections")`. `server/start/request/get/post/middleware` use network; `response/response_json/status_of/body_of` are pure.
  - `OMNISYS.serde` exists — `json_encode/json_decode/...` are all PURE (no effects). So "serialization side-effects" have NO capability token in the vocabulary; the checker cannot require a capability for serde calls. Interesting finding for the "serialization side-effects" requirement.
  - `OMNISYS.platform.now` is declared PURE (timestamp, no capability needed).
  - Registry exposes `is_omnisys_call` with ROOT_NAMESPACES = ("omnisys", "OMNISYS") — BOTH spellings resolve.
  - `OMNISYS.http` JS file has extra functions NOT in the registry: `response`, `response_json`, `register`, `__registerInproc`, `__parseUrl`. Because `is_omnisys_call` requires fn ∈ registry, those are NOT callable from OmniScript source (checker would see an unknown name).
- `omnisys/http.js` (read fully). Findings:
  - In-process transport: `inproc://host/path` dispatches to a registered in-process server (registry object in JS). Deterministic, testable.
  - Non-inproc URLs require `http.__transport` (JS escape) else `core.panic("http: no transport ...")`.
  - `http.get(url)` returns `{status, headers, body}` via `net.request`.
  - `http.json_get` = `JSON.parse(res.body)` — discards status; panics (throws) on malformed JSON.
  - No timeout parameter anywhere in the http API surface.
- `omnisys/net.js` (read fully): `net.request(server, method, path, body)` builds req `{method, path, body, headers:{}}` and calls `server.handler(req)`; response shape `{status, headers, body}`. `net.server(handler)` creates `{tag:"server", handler, middlewares:[]}`.
- `omni_compiler/cli.py` (read fully): 
  - `run` DOES NOT EXECUTE. It compiles (`tokenize→parse→analyze→to_mir`) and calls `emit_js(mir)` then prints "omni run: OK". Compile-only. (Harness warned me to investigate this; confirmed.)
  - `build --target js` writes a self-contained HTML file (default `file.with_suffix(".html")`).
  - `check` runs the full pipeline and prints OK on success, JSON diagnostic on failure (exit 1).
- `omni_compiler/emitter.py` (read fully). Findings:
  - OMNISYS modules' JS sources are INLINED (dependency-ordered) into the emitted HTML script. So the runtime `omnisys.*` namespace is defined at top of script.
  - Call names are emitted VERBATIM: `omnisys.http.get(...)` in source → `omnisys.http.get(...)` in JS. Since the runtime namespace is lowercase `omnisys`, source calls MUST use lowercase `omnisys.<module>.<fn>` to work at runtime (capital `OMNISYS.` passes the checker but would emit `OMNISYS.http.get(...)` which is undefined at runtime). ← KEY DISCOVERY, needs probe verification.
  - `show` → `console.log(...)`.
  - Functions whose effects include `network` are emitted as `async function ...`.
  - App entry (`when app starts`) is wrapped in `batchUpdate(function(){...})` which calls `renderUI()` (touches `document`); then `bindClicks()` runs. So the emitted HTML script needs `document`/`window` stubs to eval in Node.
  - Custom types are emitted only as `// interface` JSDoc comments (no runtime struct machinery) — structs are plain JS objects.
- `omni_compiler/mir.py` (read fully): MIR preserves call names verbatim; no omnisys normalization.
- `omni_compiler/checker.py` (read fully). Effect-enforcement mechanics:
  - `BUILTIN_CAPABILITIES` maps names like `fetch/http_get/http_post/http_request` → network (legacy builtins).
  - Effect collection `_walk_call`: adds `omnisys_effects(call.name)` for any registered OMNISYS call (network for http.*, net.*-network fns). For user function calls with `inherit=True` (function bodies only), inherits callee's declared `uses`.
  - Enforcement `_enforce`: `pure`+actual → E-EFFECT-001; undeclared = actual - declared uses → E-EFFECT-003.
  - App block: `enforce_app_block_effects` uses declared uses = [] and `inherit=False` — so the app block may call user network functions freely (no transitive inheritance), but a DIRECT omnisys.http/net call in the app block adds network → E-EFFECT-003. Important architecture constraint: app block must delegate to a declared network function.
  - Type checking is mostly syntactic: `_resolve_type_of(FunctionCall)` → "unknown". Field access on a value typed "unknown" → E-TYPE-002. Struct construction requires all fields. **No static argument/arity type checking on function calls** — args are only analyzed, not matched to params.
  - Loop variable in `for` is hard-typed `Number` in the checker → field access on loop var → E-TYPE-002.
- `omni_compiler/parser.py` (read fully):
  - Dotted calls flatten to `FunctionCall(name="omnisys.http.get", args=...)`.
  - `type Name = { f: Type, ... }` type decl; struct construct `Name(f = expr, ...)` (named args only); no positional struct args.
  - No `try`/`catch`/`finally`, no methods, no `await` keyword in grammar.
  - Function signature: `fn name(p: T, ...) -> T:` then effect clauses then body, terminated by `end`.
- `omni_compiler/lexer.py` keyword map (read): `uses/reads/writes/pure/require/ensure/type/import/...` all present.
- `omnisys/core.js`, `error.js`, `serde.js`, `collections.js`, `platform.js` (read):
  - `core.panic(msg)` throws `Error`.
  - No try/catch in language → malformed JSON panics uncaught; error classification for malformed payloads must be done by inspection of the raw text (heuristic), not by catching decode failures.
  - `error.throw_error` throws too — no catch in language.
  - `platform.now()` = `Date.now()` (pure per registry).
  - `collections.list_join(list, sep)` = `list.map(String).join(sep)`.
  - `serde.json_encode` = `JSON.stringify`; `json_decode` = `JSON.parse` (throws on malformed).
- `docs/omnisys/http/README.md`, `net/README.md`: status "planned" (docs lag registry). The READMEs' public API surface (`fn serve`, `fn get(url) -> Result`) does NOT match the actual registry surface (`client/send/get/post/put/delete/json_get/json_post/...`). Docs are stale/aspirational.
- `examples/actors.omni`, `chaos.omni` (read): demo files use `sim.*` calls (v5.3) with no imports — those don't type-check against the registry (sim calls pass because checker allows any `sim.`-prefixed name). Not relevant to http.

Toolchain availability (verified): Python 3.11.9, pytest 9.1.1, node v24.17.0.

## 3. Open questions to probe

Q1. Does `omni check` accept `import OMNISYS.http` + `omnisys.http.get` in a function declared `uses network`?
Q2. Does `omni check` reject the same call when the function omits `uses network` (E-EFFECT-003)?
Q3. Does the app block reject a direct `omnisys.http.*` call (E-EFFECT-003) but accept delegation to a `uses network` function?
Q4. Is field access on the result of `omnisys.serde.json_decode` rejected (E-TYPE-002)? Does the typed-parameter workaround pass the checker?
Q5. Does the emitted JS actually run in Node (with document stubs) and does lowercase `omnisys.*` resolve (vs `OMNISYS.*`)?
Q6. Does the `inproc://` server registration work from the emitted JS to drive the network function end-to-end?
Q7. What does `omni run` output (confirm compile-only)?
Q8. What does `omni build --target js` produce and can pytest drive it?
Q9. Does `omni inspect` show declared effects for a `uses network` function?

## 4. Probe: minimal http module acceptance (Q1)

Wrote `probes/probe_http_ok.omni`:
```
import OMNISYS.http

fn fetch() -> Number:
    uses network
    res = omnisys.http.get("inproc://test/x")
    return 0
end
```
(no app block, no field access yet)

Command: `python -m omni_compiler.cli check probes\probe_http_ok.omni`
Result: (recorded below — raw output)

## 5. Probe: missing `uses network` (Q2)

Wrote `probes/probe_http_missing_effect.omni` (same as above but WITHOUT `uses network`).
Command: check → expect E-EFFECT-003.

## 6. Probe: app block direct vs delegated (Q3)

Wrote `probes/probe_app_network.omni` with both variants.

## 7. Probe: json_decode field access + workaround (Q4)

Wrote `probes/probe_json_field.omni` (direct field access on decode) and `probes/probe_json_field_workaround.omni` (typed-param wrapper).

(Execution of these probes is logged below as I run them.)

---

## PROBE EXECUTION LOG

### P1 (Q1): check minimal http module usage
Probe: `probes/probe_http_ok.omni` — `import OMNISYS.http` + `fn fetch() -> Number: uses network` calling `omnisys.http.get("inproc://test/x")`.
Command (workdir = run dir):
`python -m omni_compiler.cli check probes\probe_http_ok.omni`
Raw output:
```
omni check: OK — probe_http_ok.omni
EXIT=0
```
RESULT: Q1 confirmed — `OMNISYS.http` IS present in the registry (TASK.md's "Missing: OMNISYS.http / STATUS: BLOCKED" is STALE); check accepts http usage when `uses network` is declared.

### P2 (Q2): check missing capability declaration
Probe: `probes/probe_http_missing_effect.omni` (same, WITHOUT `uses network`).
Command: `python -m omni_compiler.cli check probes\probe_http_missing_effect.omni`
Raw output (abridged):
```
{
  "schema": "omni.diagnostic",
  "version": "1.0",
  "code": "E-EFFECT-003",
  "category": "effect",
  "severity": "error",
  "message": "Capability network used without declaration.",
  "details": "fetch performs network I/O but declares no capability for it.",
  "context": { "function": "fetch", "capability": "network" },
  "fixes": [ { "id": "declare-network", "kind": "add_declaration",
    "applicability": "automatic", "text": "    uses network\n" } ]
}
EXIT=1
```
RESULT: Q2 confirmed — capability enforcement works; diagnostic includes an automatic fix (insert `uses network`).

### P3 (Q3): app block direct call vs delegated call
Probes: `probes/probe_app_network.omni` (app calls `fetch()`, a `uses network` fn) vs `probes/probe_app_direct.omni` (app calls `omnisys.http.get` directly).
Commands + outputs:
```
python -m omni_compiler.cli check probes\probe_app_network.omni   → omni check: OK ... EXIT=0
python -m omni_compiler.cli check probes\probe_app_direct.omni    → E-EFFECT-003 ... EXIT=1
```
RESULT: Q3 confirmed. The `when app starts` block is enforced against declared uses = [] AND with `inherit=False` (no transitive inheritance from callees), so it may call declared network functions freely but must NOT invoke `omnisys.http/net.*` itself. Architectural consequence: the app entry must delegate network work to a function that declares `uses network`.

### P4 (Q4): json_decode field access
Probes:
- `probes/probe_json_field.omni` — `data = omnisys.serde.json_decode(body); return User(id = data.id, ...)`
- `probes/probe_json_field_workaround.omni` — re-wrap through typed-param helper `user_from_payload(payload: User) -> User`
Outputs:
```
check probe_json_field.omni          → E-TYPE-002 "Cannot access field 'id' on a non-struct value."
                                       details: "'unknown' is not a declared custom type" ... EXIT=1
check probe_json_field_workaround.omni → omni check: OK ... EXIT=0
```
RESULT: Q4 confirmed. Field access is statically restricted to declared custom types; the result of any call is typed "unknown", so `decoded.field` is rejected. The typed-parameter wrapper passes because the checker performs NO static argument/arity type matching at call sites. This is the deserialization idiom for this language.

### P5: `omni run` is compile-only (confirmed by reading cli.py, then running)
```
python -m omni_compiler.cli run probes\probe_json_field_workaround.omni → omni run: OK  EXIT=0
```
`run` runs tokenize→parse→analyze→to_mir→emit_js and prints OK. It does NOT execute the JS. (Verified in cli.py lines 136-147.)

### P6: `omni build --target js` produces a self-contained HTML artifact
Command: `python -m omni_compiler.cli build probes\probe_json_field_workaround.omni --target js --output build\probe_workaround.html`
First attempt failed with FileNotFoundError because `build/` did not exist (cli does not create parent dirs — `out.write_text` on missing dir). Recreated dir → `omni build: wrote build\probe_workaround.html (target=js) EXIT=0` (19210 bytes).
RESULT: build writes the HTML artifact; parent dir must pre-exist.

### P7: emitted JS runs in Node with DOM stubs (Q5)
Wrote `probes/run_probe.js` (vm.runInContext, document/window stubs). Ran against build\probe_workaround.html:
```
parse_user => {"id":7,"name":"Ada","email":"ada@x.com"}        ← pure fn works
__parseUrl inproc => {"host":"api","path":"/users","scheme":"inproc"}
```
BUT the app block `r = fetch(); console.log(r)` produced an unhandled promise rejection (panic: no transport for 'inproc' — no server registered yet) that crashed Node. Confirms:
- lowercase `omnisys.*` in source → emitted verbatim → resolves against inlined runtime namespace. (Q5 confirmed; uppercase `OMNISYS.*` would pass the checker but be undefined at runtime.)
- App-block network calls return un-awaited Promises; failures become unhandled rejections.
Decision: the deliverable's `when app starts` block stays PURE; network functions are exercised by tests.

### P8: inproc:// end-to-end (Q6)
`probes/run_probe2.js` registered an inproc server AFTER eval and awaited `fetch()` → still crashed because the app block had already panicked during eval. Conclusion: registration must exist before any network call; since OmniScript cannot call `http.register` (not in registry), stub servers must be registered by the harness before driving network functions. Verified end-to-end later via the pytest snippets.

### P9: emitter `let`-declaration collision bug (discovered while building api_client.omni)
Emitted `let` declarations for app/fn-assigned variables are `needed - param_names`. Any name that is a parameter of ANY function is excluded from the module-scope `let` set. Assignment to such a name inside another function (e.g., `res = ...` where `res` is a param of `response_status`) → strict-mode `ReferenceError: res is not defined` at runtime, even though `omni check` passes.
Raw evidence (node): 
```
ReferenceError: res is not defined   at fetch_users (api_client.js:716:7)
ReferenceError: payload is not defined  at create_user (api_client.js:733:11)
ReferenceError: elapsed is not defined  at fetch_users (api_client.js:720:11)
```
Confirmed `Select-String '^let ' build\api_client.html` → only conn,data,get,items,outcome,post,t0,t1,users declared.
Correction: renamed locals `res`→`resp`, `payload`→`json_body`, `elapsed`→`duration` (none collide with any parameter) → runs clean. This is a genuine compiler defect worth reporting (shadowing-safe renaming is the workaround).

### P10: `and`/`or` logical operators missing from the parser
Writing `if status greater or equal 200 and status less than 300:` → `E-SYNTAX-001 ... Expected token type TokenType.COLON, got TokenType.AND ('and') at line 125, col 36`.
Reading parser.py: `parse_expression` → `parse_binary_expr` → `parse_comparison` → `parse_term` → `parse_factor` → `parse_primary`; NO clause consumes the AND/OR token types (lexer tokenizes them; spec §6.3 documents them). The parser's grammar never implements logical operators.
Correction: rewrote the 2xx check as nested `if status >= 200: if status < 300: ...`.

### P11: `omnisys.core.*` requires explicit `import OMNISYS.core`
`omni check` on api_client.omni → E-IMPORT-003 "OMNISYS module 'core' used without being imported" for `omnisys.core.is_empty` even though core is implicitly inlined via module deps. The checker requires an explicit import statement per module whose functions the source calls. Added `import OMNISYS.core`.

### P12: final api_client.omni acceptance
```
python -m omni_compiler.cli check source\api_client.omni   → omni check: OK — api_client.omni   EXIT=0
python -m omni_compiler.cli run source\api_client.omni      → omni run: OK                    EXIT=0
python -m omni_compiler.cli build source\api_client.omni --target js --output build\api_client.html → EXIT=0 (24462 bytes)
```

### P13: inspect shows declared effects
```
python -m omni_compiler.cli inspect fetch_users source\api_client.omni
  → {"name":"fetch_users","type":"fn(Text, Number) -> ErrorKind",
     "declared_effects":{"uses":["network"],"reads":[],"writes":[],"pure":false}, ...} EXIT=0
python -m omni_compiler.cli inspect classify_error source\api_client.omni
  → declared_effects uses:[] pure:true EXIT=0
```

### P14: backend capability rejection
```
python -m omni_compiler.cli build source\api_client.omni --target c     → E-BACKEND-001 EXIT=1
python -m omni_compiler.cli build source\api_client.omni --target rust  → E-BACKEND-001 EXIT=1
```
"OMNISYS modules require the JS lane." Automatic fix suggests `--target js`. §8.3 per-back-end capability check works as specced.

### P15: explain / verify / generate
```
python -m omni_compiler.cli explain source\api_client.omni → "omni explain: no errors found" EXIT=0
python -m omni_compiler.cli verify source\api_client.omni  → omni.verify.batch, every function status "no-contracts" EXIT=0
python -m omni_compiler.cli generate source\api_client.omni parse_user → AST-walking pytest draft (evaluates expressions via symbol table, not the JS runtime)
```

### P16: pytest suite
Command (cwd = repo root E:\simualtion):
```
python -m pytest -p no:cacheprovider OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE\tests\test_api_client.py -v
```
Raw result: **18 passed in 3.49s** (all tests green; full list recorded in the run transcript above).

The test suite drives the COMPILED JS artifact in Node (`tests/node_driver.js`) with DOM stubs and registers `inproc://` stub servers to exercise the network functions end-to-end, plus negative compiler tests (missing `uses network`, direct app-block network call, unknown `http.register` call).

---

## VERIFICATION SUMMARY (recorded)

| Criterion | Command | Result |
|---|---|---|
| check exits 0 | `python -m omni_compiler.cli check source\api_client.omni` | EXIT=0 |
| run (compile-only) exits 0 | `python -m omni_compiler.cli run source\api_client.omni` | EXIT=0 |
| build js artifact | `python -m omni_compiler.cli build source\api_client.omni --target js --output build\api_client.html` | EXIT=0 |
| capability enforcement | negative probes + `inspect` | E-EFFECT-003 / uses=[network] |
| pytest suite | `python -m pytest ... tests\test_api_client.py` | 18 passed, 0 failed |

## HONEST VERIFICATION BOUNDARY

- `omni run` does NOT execute code; it is compile-only. End-to-end execution was instead demonstrated by (a) executing the built JS artifact in Node, and (b) the pytest suite driving the artifact. This satisfies the acceptance criterion in spirit: request-construction, response-parsing, and error-classification logic are all demonstrated against stubbed responses in the executed artifact.
- The OMNISYS.http runtime in this build has NO real wire transport: non-`inproc://` URLs panic ("no transport") unless a harness sets `http.__transport`. "Connection failures" at the wire level therefore cannot be exercised; the classification for status 0 is implemented and unit-tested, and the panic path is tested as the observable failure mode.
- Timeouts are enforced as a measured-elapsed vs. budget policy in `fetch_users`/`create_user` (using the pure platform clock around the call) — verified end-to-end with a slow stub server. The OMNISYS.http API itself exposes no timeout parameter, and `async.timeout(task, ms)` (registry) is the only timeout primitive, requiring a Task/Promise that the synchronous http functions never produce.
- Malformed-payload detection is a pre-decode heuristic (empty body) because the language has no try/catch: `json_decode` throws (via `core.panic`) un-catchably on malformed JSON. Richer malformed detection would need a serde-level validator that decodes to a schema without throwing; none exists.

## FINAL DECISION RECORD

1. Use lowercase `omnisys.<module>.<fn>` in source (emitted verbatim → matches runtime namespace).
2. Keep `when app starts` pure (delegate network work to declared `uses network` functions).
3. Deserialize JSON via typed-parameter re-wrapping helpers (only statically legal field access path).
4. Avoid `{`/`}` in text literals (emitter's `_js_text` treats them as interpolation slots).
5. Avoid variable names that collide with any function parameter (emitter `let` bug).
6. Classify malformed payloads by empty-body heuristic; document richer detection as unimplemented.
7. Tests drive the built artifact in Node with `inproc://` stub servers; negative compiler probes included.