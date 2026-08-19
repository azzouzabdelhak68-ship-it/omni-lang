# BENCHMARK_REASONING — Project 2.4 Multi-Client Messaging Server

Model: deepseek-v4-flash-free (opencode)
Run dir: `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_24_NETWORKING_CHAT_SERVER\RUN_001_DEEPSEEK_V4_FLASH_FREE`
Start: 2026-08-17

This file is a LIVE research ledger. Entries are chronological; nothing is rewritten after the fact.

---

## 1. Task intake (from TASK.md)

Mission: multi-client real-time messaging server supporting connection lifecycles, message broadcasting, and protocol handling.

Functional requirements:
1. Server lifecycle: start, accept multiple concurrent clients, shut down cleanly; live set of connected clients.
2. Protocol handling: parse incoming messages into structured records (sender, channel, payload, timestamp); handle join/leave explicitly.
3. Broadcasting: deliver a client's message to all other connected clients; channel-scoped delivery.
4. Concurrency: handle concurrent arrivals without corrupting the client registry.
5. Capability declaration: declare network usage and connection side-effects at function boundaries.

Deliverables (all inside run dir):
1. `BENCHMARK_REASONING.md` (this file)
2. `source/chat_server.omni`
3. `tests/test_chat_server.py` (simulated clients)
4. `RESULTS.md` (MODEL_RESULT + ECOSYSTEM_RESULT)

Acceptance:
- `omni check source/chat_server.omni` exits 0
- capability model correctly enforces declared network usage
- all pytest tests pass

TASK.md STATUS metadata says `BLOCKED` — "Missing: OMNISYS.net — server lifecycle, WebSocket/RPC transport, connection handling, concurrency. Runnable once OMNISYS.net ships in v6." Discovery question #1: is that stale? The registry and omnisys/net.js already exist. Must verify empirically.

## 2. Infrastructure recon

Operational facts (given, not discovered):
- Compiler CLI: `python -m omni_compiler.cli <check|run|build|inspect|explain|verify|suggest|generate|trace>`
- `import OMNISYS.<module>` stdlib model
- Registry: `E:\simualtion\omni_compiler\omnisys_registry.py`; JS impls: `E:\simualtion\omnisys\*.js`
- Spec `OMNI_SPEC.md`; docs under `E:\simualtion\docs\`
- Files must be UTF-8 without BOM (lexer rejects BOM)
- Sibling reference run: `PROJECT_23_HTTP_REST_CLIENT\RUN_001_DEEPSEEK_V4_FLASH_FREE` (same phase, studied as compiler-behavior examples)

What I inspected:
- `TASK.md` (read fully) — see §1.
- `omnisys_registry.py` (read fully, 521 lines). Findings:
  - `OMNISYS.net` EXISTS. js_file `omnisys/net.js`, deps `("core","collections")`. Functions with `network` effect: `server`, `start`, `request`, `get`, `post`, `middleware`. Pure: `response`, `response_json`, `status_of`, `body_of`.
  - `OMNISYS.http` also exists (network effects) — irrelevant but confirms v6 shipped net/http.
  - `OMNISYS.serde` (`json_encode/json_decode`) PURE — no capability token for serialization.
  - `OMNISYS.platform.now()` registered PURE (`fn() -> Number`), JS = `Date.now()`.
  - `is_omnisys_call` requires the exact fn in the registry table — JS-only functions are NOT callable from OmniScript source. Both `omnisys.X` and `OMNISYS.X` spellings resolve at CHECK time.
- `omnisys/net.js` (read fully, 63 lines): request/response model. `net.server(handler)` → `{tag:"server", handler, middlewares:[]}`; `net.start(server)` → sets `server.running = true`; `net.request(server, method, path, body)` builds `req {method: upper, path, body: String, headers:{}}` and calls `server.handler(req)`; `net.get/post` wrappers; `net.response_json(status, value)` → `{status, headers, body: JSON.stringify(value)}`. NO stop/shutdown API. NO real sockets/WebSockets — deterministic in-process synchronous transport.
- `omni_compiler/cli.py` (read fully): `run` is COMPILE-ONLY (tokenize→parse→analyze→MIR→emit_js, prints "omni run: OK", no execution). `build --target js` writes self-contained HTML (default `file.with_suffix(".html")`); parent dir must pre-exist. `check` prints OK on success / JSON diagnostic on failure (exit 1).
- `omni_compiler/emitter.py` (read fully). Key emission rules:
  - OMNISYS module JS sources are INLINED dependency-ordered into the script. Runtime namespace is lowercase `omnisys.*`.
  - Call names emitted VERBATIM → source MUST use lowercase `omnisys.<module>.<fn>` (uppercase `OMNISYS.*` passes checker but is undefined at runtime).
  - Functions with `network` in declared uses → emitted `async function`.
  - Module-scope `let` declarations = `{all assign names across all fn bodies + entry block} − {all param names}`. A local assigned inside a function whose name equals ANY function parameter is NOT declared → strict-mode ReferenceError at runtime while `omni check` passes. (Sibling confirmed for `res`, `payload`, `elapsed`.)
  - Text literals: `{expr}` = interpolation slot; literal `{`/`}` in Text is unsafe.
  - Struct constructs emit as plain JS object literals; custom types emit only as JSDoc comments (no runtime struct machinery).
  - Entry block wrapped in `batchUpdate(function(){...})` which calls `renderUI()` → touches `document`. Node harness needs document stubs.
- `omni_compiler/checker.py` (read fully). Effect enforcement:
  - `_walk_call` with `inherit=True` inside function bodies: adds callee's declared `uses` (transitive). App block uses `inherit=False` + declared uses = [] → app block may call declared network functions but must NOT call `omnisys.net/http.*` directly (E-EFFECT-003).
  - `E-EFFECT-001` pure+actual; `E-EFFECT-003` undeclared capability (with automatic `uses network` fix).
  - Field access only allowed on values of declared custom types; call results type as "unknown" → `E-TYPE-002`. Loop variables are hard-typed `Number` → field access on loop items statically rejected.
  - No static argument/arity type matching at call sites → typed-parameter re-wrapping idiom works.
  - Function names are valid identifiers → a function can be passed as an argument (e.g. `net.server(route)`).
  - The checker auto-defines a `result` symbol per function scope (return type). `reads`/`writes` are parsed but NOT enforced.
- `omni_compiler/parser.py` (read fully):
  - Function calls: `name(args)` positional; named args (`x = ...` after `(`) → StructConstruct (ALL fields required, E-TYPE-005 otherwise).
  - Comparisons: `is`, `is not`, `greater than`, `less than`, `greater or equal`, `less or equal`, `>=`, `<=`, `>`, `<`. NO `and`/`or`/unary `not` in grammar (lexer tokenizes them; parser never consumes them) — sibling confirmed E-SYNTAX-001 on `and`.
  - No try/catch/finally, no await, no methods.
  - `for x in <expr>:` is the only loop; `break`/`continue` exist.
- `omni_compiler/lexer.py` (read fully): NUMBER pattern `\d+(\.\d+)?(e...)` — `0` is a NUMBER literal; TEXT keeps quotes (emitter strips); `greater or equal`/`greater than`/`less or equal`/`less than` tokenized as GREATER_OR_EQUAL/GREATER/etc with those value strings. `not` is a keyword token but unused by parser except after `is`.
- `omnisys/core.js` (read): `panic` throws `Error`; `is_empty(x)` = length 0; `length` handles string/array/object.
- `omnisys/collections.js` (read): `list_push` MUTATES in place + returns; `list_join` = `list.map(String).join(sep)`; `set_add/remove` use indexOf on VALUES (object identity — useless for struct dedupe); no `map_get`/`map_has` issues.
- `omnisys/platform.js` (read): `now()` = `Date.now()`; `sleep_ms` busy-waits.
- `docs/omnisys/net/README.md` (read): STALE — says status "planned" and documents a public API (`fn listen(port: Int)`, `fn connect(host, port)`, `fn send(socket, data)`) that does NOT exist in the registry/runtime. The real API is the request/response handler model.
- Sibling `PROJECT_23.../RUN_001...` deliverables (read fully): BENCHMARK_REASONING.md (7 ecosystem discoveries), api_client.omni (idioms), test_api_client.py (pytest harness pattern), node_driver.js (vm sandbox driver pattern), snippets. Confirmed: Node v24 + pytest 9.1.1 available; vm.runInContext with DOM stubs; top-level OmniScript functions become sandbox globals; `__RESULT__` JSON printed by driver.
- `docs/CAPABILITY_MATRIX.md` (read): net → network; http → network. Consistent with registry.

## 3. Key design hypotheses

H1. The OMNISYS.net "server" is a synchronous request/response handler, NOT a socket server. "Clients" are simulated protocol peers that POST /connect, /disconnect, /send and GET /clients, /messages. This satisfies the mission within the shipped API (TASK.md's BLOCKED status is likely STALE).

H2. Shared live state (client registry, message log, shutdown flag) can be modeled with module-scope mutable `let` variables (the emitter emits `let <name>;` at module scope for assigned names). The handler mutates them per request; because the transport is single-threaded/synchronous, arrivals are serialized by construction → registry corruption risk is eliminated, satisfying the concurrency requirement in spirit.

H3. The handler MUST be a PURE (non-async) function so `net.request` returns a real Response synchronously. Network capability (`uses network`) is declared on the transport-calling lifecycle functions (start_server, connect_client, disconnect_client, send_message, list_clients, get_messages, read_channel, shutdown_server). This is the mapping of "network usage and connection side-effects at function boundaries" given the vocabulary has only `network` (no distinct "connection" token).

H4. JSON parse → re-wrap through typed-parameter helpers (no field access on "unknown"). All local variable names must be disjoint from ALL parameter names (emitter `let` bug). Loop variables iterate lists; items re-wrapped via typed-param helpers.

H5. Shutdown modeled as protocol operation: POST /shutdown sets a module `shut_down` flag; subsequent requests → 503. (net.js has no stop API.)

H6. `omni run` is compile-only (H in cli.py); execution must be demonstrated via the built JS artifact driven in Node by pytest snippets.

Open questions to probe:
Q1. check accepts `import OMNISYS.net` + `omnisys.net.server(route)` with `route` a pure fn passed as reference?
Q2. E-EFFECT-003 when a function calls `omnisys.net.*` without `uses network`?
Q3. App block direct `omnisys.net.*` call rejected (E-EFFECT-003) while delegation to declared fn OK?
Q4. Do module-scope `let` vars persist across handler invocations in the emitted JS (shared registry)?
Q5. Does the emitted artifact run in Node (DOM stubs) with the full connect→send→read→disconnect flow?
Q6. Does malformed JSON body panic un-catchably (no try/catch in language)?
Q7. `omnisys.net.listen` (docs README) rejected at check time (registry has no `listen`)?
Q8. Does `run` print "omni run: OK" (compile-only)?

---

(Probe execution log starts below; entries are appended in time order as I run commands.)
---

## 4. Resumption log (2026-08-18) — finishing the run

The prior attempt stopped after §3 with probes still outstanding and the deliverables
missing (tests/test_chat_server.py, RESULTS.md). This resumption re-ran every gate,
discovered that the compiler frontend had materially changed since the first pass,
fixed the source, and completed the suite. Nothing above is rewritten; all new
findings are appended here.

### 4.1 Gates re-run (exact commands + output)

- `python -m omni_compiler.cli check source/chat_server.omni`
  → `omni check: OK · chat_server.omni`, exit 0. (Initially FAILED with E-EFFECT-004 —
  see 4.2.)
- `python -m omni_compiler.cli run source/chat_server.omni`
  → prints `chat_server.omni loaded: call start_server() then drive the chat protocol`,
  exit 0. **`run` now EXECUTES the program under Node** (cli.py:142-191 emits JS to a
  temp HTML, runs `scripts/run-omnisys.js` with DOM stubs, forwards the `show` output).
  This contradicts the first-pass record (§2: "run is COMPILE-ONLY"). Honest record:
  `run` verifies the entry block runs; it does NOT exercise server logic (functions are
  only callable from the compiled artifact).
- `python -m omni_compiler.cli build source/chat_server.omni --target js --output build/chat_server.html`
  → `omni build: wrote build\chat_server.html (target=js)`, exit 0.
- Connect/disconnect, parsing, broadcast, shutdown and concurrency were verified by
  running the built artifact under Node (tests/node_driver.js + snippets) — see 4.5.

### 4.2 Compiler drift: E-EFFECT-004 (module-data reads/writes) now enforced

First-pass §2 recorded "reads/writes are parsed but NOT enforced". On resumption the
checker rejects that claim: `check` failed with `E-EFFECT-004` "Module data
'client_registry' accessed via reads without declaration" (checker.py:781-801,
`_enforce` compares `_walk_data_access` collected module identifiers against the
`reads`/`writes` clauses). `module_scope` = names assigned in the `when app starts`
block (checker.py:174). Fix: every function that directly references a module resource
declares `reads <resource>` (`client_registry`, `message_log`, `shut_down_flag`).
Functions that ASSIGN a module name are silently exempt because the assignment puts
the name in `local_names` (checker.py:599,663-667) — a checker blind spot equivalent
to the emitter shadow bug below.

### 4.3 Compiler drift: emitter now emits function-local `let` that SHADOWS module data

First-pass §2 recorded the emitter emits module-scope `let` only and NO function
locals (→ ReferenceError). On resumption emitter.py:367-369 emits
`let <fn_locals>;` inside every function for all assigned names minus params. Any
function that ASSIGNED a module resource (`client_registry = list_push(...)`) got a
function-local `let client_registry;` shadow → the module registry was never mutated
(observed crash: `Cannot read properties of undefined (reading 'push')`).
**Design fix**: functions never assign module resources; they mutate them in place
via OMNISYS.collections mutators called as BARE STATEMENTS
(`omnisys.collections.map_set(client_registry, ...)`), which the parser accepts
(parser.py:365-372 → FunctionCall statement) and the emitter renders as `expr;`
(emitter.py:138-139). `list_push`/`map_set`/`map_remove` all mutate their first
argument in place (collections.js), so no assignment target is introduced and no
local `let` shadows the module value. Verified in build/chat_server.html:565-567
(module lets) and :653/:664/:683/:737 (statement mutators).

### 4.4 Compiler drift: bindClicks / DOM expectations

The emitter now appends `bindClicks()` which calls
`document.getElementById("app").addEventListener(...)` (emitter.py:382-389).
tests/node_driver.js's DOM stub lacked `addEventListener` → HARNESS_ERROR
`addEventListener is not a function`. Driver stub extended with `addEventListener`
(and `createElement`) on the `getElementById` result.

### 4.5 Runtime findings from the compiled artifact

- Full chat flow (connect×4, duplicate 409, channel-scoped broadcast, disconnect,
  ghost 404, shutdown 200 → 503 after) passes in Node.
- Parsing: `parse_message` returns the structured record
  {sender, channel, payload, timestamp}; the server stamps `omnisys.platform.now()`
  at broadcast (stored timestamps positive numbers).
- Broadcast is channel-scoped: `alice→general` delivered to `bob,carol`, excludes
  sender and off-topic `dave`.
- Validation: empty body / missing fields → 400, unknown sender → 404, unknown path →
  404, bad method → 405, duplicate connect → 409.
- **Q6 answered**: a NON-EMPTY malformed JSON body (e.g. `"{not-json"`) panics
  UN-CATCHABLY (`serde.json_decode` throws SyntaxError; the language has no try/catch)
  → driver exits rc=2. Empty bodies are guarded (400 "empty body") so the panic only
  bites on genuinely malformed JSON. Documented as a runtime limitation.
- Concurrency: 10 interleaved joins + 9 broadcasts in one burst keep the registry
  and message log consistent (registryStable, joinCount=10, logCount=9). Because the
  OMNISYS.net transport is synchronous and single-threaded, arrivals are serialized
  by construction — concurrency is *modeled*, not truly parallel.
- Capability enforcement (probes): missing `uses network` → E-EFFECT-003; app block
  calling `omnisys.net.*` directly → E-EFFECT-003; docs-phantom `omnisys.net.listen`
  → E-NAME-001 (docs README lags the registry). `inspect` confirms
  `start_server.uses=[network]`, `parse_message.pure`, `client_names.reads=[client_registry]`.

### 4.6 Deliverables status

- BENCHMARK_REASONING.md — this file (live, completed).
- source/chat_server.omni — passes check (exit 0); server semantics demonstrated via
  the compiled artifact.
- tests/test_chat_server.py — 18 pytest cases, all PASS (2.76 s).
- RESULTS.md — written (see run dir).

### 4.7 Honest verification ledger (what was / wasn't verified)

Verified by compiler: static acceptance (check), entry-block execution (run), and
negative capability enforcement (probes → E-EFFECT-003 / E-NAME-001 / E-EFFECT-004).
Verified by Node artifact execution: connect/disconnect, duplicate detection,
parsing, channel-scoped broadcast, validation codes, clean shutdown, concurrency
burst consistency. NOT verified: real sockets/WebSockets (OMNISYS.net is an
in-process synchronous handler model — no transport exists), true parallel
concurrency, and graceful handling of malformed JSON (panics, see 4.5).