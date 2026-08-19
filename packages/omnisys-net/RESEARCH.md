# OMNISYS.net — Research & Design Notes (v6 Phase 2)

Research gate for the Python reference implementation of `OMNISYS.net`
(portable server/request/response model + middleware). Produced before
implementation per spec §17.8 and `docs/architecture/13-package-system.md`
§7, using the eleven questions from `docs/architecture/04-api-design-principles.md`
§1 (spec §17.3 "Do Not Wrap — Design Native"). The JS reference implementation
(`omnisys/net.js`) and the registry contract
(`omni_compiler/omnisys_registry.py`, `OMNISYS_MODULES["net"]`) are the
semantic authorities; this document records where the Python lane mirrors
them, where it deviates, and why.

Ecosystems studied: Node.js `http`/`https`, Express, Koa, WSGI, ASGI
(Starlette/FastAPI), Python stdlib (`http.server`, `urllib.request`,
`http.client`), WebSockets (RFC 6455 / `ws` / `websockets`), JSON-RPC, gRPC,
Go `net/http`, and Rust `hyper`/`tower`. Architecture anchor:
`docs/architecture/08-networking.md` (net owns transport + the wire
contract; http owns routing/middleware/status semantics).

---

## 1. The eleven questions (§17.3)

### 1.1 What problem is it solving?

Give OmniScript a networking vocabulary: a server value, a way to start it,
a request-driving function, verb conveniences (`get`/`post`), a middleware
composer, and typed `Response` builders/accessors — all deterministic and
testable in-process, no sockets required. `OMNISYS.http` builds routing on
top of this same semantic API.

### 1.2 Which concepts survived because they're genuinely useful?

- A single request value (`method`, `path`, `body`, `headers`) and a single
  response value (`status`, `headers`, `body`) — the only two shapes the
  whole module needs.
- A server as a plain handler function (or None) — no object lifecycle, no
  ports, no sockets. This is the "portable core" of every ecosystem studied.
- Middleware as `(req, next_fn) -> Response` — the Express/WSGI/ASGI/tower
  pattern that every model and every learner already knows.
- Status codes as plain numbers and `501 "no handler"` as the deterministic
  answer for a handlerless server.

### 1.3 Which exist due to historical constraints?

- Express's `req`/`res` mutation dance (stack, status, headers are mutable
  properties). OMNISYS.net models requests and responses as inert values.
- WSGI's `environ` dict and `start_response` callback — a CPython-specific
  artifact of the synchronous CGI model.
- Node's `Buffer`/`stream` body model and `this`-binding headaches (the
  final closure wrapper in `net.middleware` exists partly to avoid `this`
  leaks). Python has no such concern.
- gRPC/HTTP2 multiplexing and frame machinery — a transport reality, not a
  semantic need.

### 1.4 Which APIs are awkward due to the host language?

- JS `String(x)` coerces anything (`null` → `'null'`); Python `str(x)`
  coerces but renders `None` as `'None'`. Both coerce, but the renderings
  differ for falsy corner cases.
- JS truthiness: `{}` and `[]` are truthy; Python `{}`/`[]` are falsy. This
  changes `status_of`/`body_of` on empty objects (§6).
- JS `undefined` vs Python `None`: `request` treats `body` `undefined`/`null`
  as `""`; Python's `None` plays that role.
- JS `JSON.stringify` emits compact separators (`{"a":1}`) and never escapes
  non-ASCII; Python `json.dumps` defaults to spaces and `\uXXXX` escapes —
  both corrected in `response_json` for parity.
- JS `Number` is a single float type (`JSON.stringify(1.0)` → `"1"`); Python
  distinguishes `1.0` from `1` (`json.dumps(1.0)` → `"1.0"`).

### 1.5 Which abstractions are hard for AI agents?

- Full HTTP/1.1 state machines, chunked transfer encoding, connection
  keep-alive semantics, header casing rules — invisible complexity with zero
  payoff for a portable core.
- Socket lifecycle and ownership (who closes the connection, when) — the
  architecture doc's own open question (08-networking.md §5).
- Async event-loop plumbing (`async` module) — never required to write or
  test a handler.
- Express-style mutable `req`/`res` — hard to reason about, hard to
  property-test. Immutable value shapes are the agent-friendly choice.

### 1.6 Which concepts become first-class Omni concepts?

- **Request** and **Response** as plain Maps — same literal syntax as any
  other OmniScript value; agents can construct, diff, and round-trip them
  with `serde.json_encode`/`json_decode`.
- **Server** as a plain Map with a callable `handler` — `{"tag": "server",
  "handler": fn, "middlewares": []}`; the `network` capability is metadata
  on the registry entry.
- **Middleware as a function of `(req, next_fn)`** — the onion model made
  explicit: the first entry in the list is the outermost layer and runs
  first; responses flow back up through the chain.

### 1.7 Which remain libraries?

- Real HTTP/1.1/2/3 transport, TCP/TLS sockets, DNS, WebSocket framing,
  HTTP/2 multiplexing, gRPC/GraphQL — all backend escapes behind the same
  semantic API (08-networking.md §5: "Real transport ... is a future escape
  that keeps this same semantic API").
- Routing, status-code vocabulary, JSON body conventions — those live in
  `OMNISYS.http`.

### 1.8 Which map to the effect/capability system?

Six functions declare `network` in the registry: `server`, `start`,
`request`, `get`, `post`, `middleware`. Four are pure: `response`,
`response_json`, `status_of`, `body_of`. The conformance test
`test_network_effect_marking_matches_registry` locks the exact partition.
The `_pure`/`_fn` markers are capability metadata only: this Python package
implements every function as a plain synchronous function, because the
model is in-process and deterministic (no real I/O occurs).

### 1.9 What belongs in the portable semantic layer?

- Server construction, auto-start on first request, request normalization
  (uppercase method, stringified path/body, empty headers).
- Middleware composition with explicit ordering semantics.
- Response construction, JSON responses, and status/body accessors with the
  exact falsy fallbacks.
- The `501 "no handler"` convention for a server with a falsy handler.

### 1.10 What must remain backend-specific?

- Socket accept/connect loops, TLS handshakes (via `crypto`), event-loop
  integration (via `async`), actual HTTP wire encodings, WebSocket
  framing, connection pooling, retries, redirects.
- Backend performance engines (Node `http`, Rust `hyper`, Go `net/http`).

### 1.11 What is the escape hatch?

- `request` drives any server value, so a handler can be any callable — the
  portable layer never blocks a backend-specific handler.
- `headers` is an open dict on both Request and Response; `status`/`body`
  are free-form on construction, so backend specifics (cookies, content
  types, streaming bodies) can ride along as ordinary values.
- `response_json` accepts any JSON-compatible value (like `serde.json_encode`).

---

## 2. Ecosystem survey

### 2.1 Node.js `http`/`https` (the JS lane's host runtime)

- **Strengths:** event-driven server/client; `request`/`response` objects
  are the universal JS shapes; `net.js` borrows their `status`/`headers`/
  `body` vocabulary directly.
- **Weaknesses:** mutable `IncomingMessage`/`ServerResponse`; `this`-binding
  hazards in handlers; streams everywhere (body as `Buffer`, not text).
- **Performance:** excellent for its niche; irrelevant to an in-process
  model.
- **Portability:** JS-only; no interop surface for the Python lane.
- **Lesson adopted:** keep `status`/`headers`/`body` as the two value shapes;
  drop streams and mutability entirely.

### 2.2 Express / Koa middleware (the `middleware` function's ancestor)

- **Express:** `(req, res, next)`; middlewares are registered in order and
  run in order, with `next()` passing control. `app.use` composes.
- **Koa:** onion model — middlewares run in registration order on the way
  in and reverse order on the way out, with `next()` returning a Promise.
- **Strengths:** the `(req, next_fn)` signature is the most widely
  understood composition pattern in web programming; AI models can write it
  from memory.
- **Weaknesses:** Express mutates `req`/`res` in place and relies on
  `res.status(...).json(...)` chains; Koa's async onion is awkward to
  reason about deterministically.
- **Portability:** both are JS-framework-specific.
- **Lesson adopted:** the pure `(req, next_fn) -> Response` shape (as in
  `net.js`); no mutation of `req`, no promise semantics. The `net.js` loop
  wraps the list so the *first* entry is outermost and runs first — matching
  Express's registration-order intuition — and responses flow back up in
  reverse (Koa's onion).

### 2.3 WSGI

- **Strengths:** the canonical Python synchronous server/middleware
  contract; middleware is a plain callable wrapping another callable — the
  exact nesting pattern `net.middleware` uses.
- **Weaknesses:** the `environ` dict is a grab-bag of CGI leftovers; the
  `start_response(status, headers)` callable protocol is bizarre to read
  and write; no request/response *values* at all.
- **Performance:** fine for its era; C-backends exist.
- **Portability:** CPython-centric (PEP 3333).
- **AI usability:** poor — `environ` keys and the `start_response` protocol
  are things models get wrong.
- **Lesson adopted:** the value-oriented middleware call; reject the
  callback protocol entirely.

### 2.4 ASGI (Starlette / FastAPI / Uvicorn)

- **Strengths:** modern Python; `(scope, receive, send)` is uniform across
  HTTP/WS/lifespan; middleware via `__call__` wrapping; async-native.
- **Weaknesses:** three-part scope/receive/send interface is heavy for a
  portable core; everything async — un-testable without an event loop;
  `send`/`receive` are awaited callables, not values.
- **Performance:** excellent (uvloop); again transport-bound.
- **AI usability:** mixed — async plumbing distracts from the actual
  handler logic.
- **Lesson adopted:** async stays in `OMNISYS.async`; the portable `net`
  core is synchronous and value-passing, so handlers are trivially
  testable.

### 2.5 Python stdlib (`http.server`, `urllib.request`, `http.client`)

- **Strengths:** zero-dependency reference implementations; `BaseHTTPRequestHandler`
  and `urlopen` are the stdlib ground truth for the eventual escape.
- **Weaknesses:** `http.server` handlers are class-based (`do_GET` methods,
  mutable `self`); `urllib` returns file-like wrappers; no middleware story.
- **Performance:** acceptable; not competitive with async stacks.
- **Portability:** stdlib everywhere.
- **Lesson adopted:** stdlib-only implementation for the Python lane
  (`json` only); the stdlib is the future backend escape, not the model for
  the portable API.

### 2.6 WebSockets (RFC 6455 / `ws` / `websockets`)

- **Strengths:** the only first-class bidirectional browser channel;
  `ws` (Node) and `websockets` (Python) are mature.
- **Weaknesses:** persistent-connection lifecycle (open/close/ping-pong),
  frames vs messages, origin checks, subprotocol negotiation — a large
  surface with no value in an in-process model.
- **Performance:** message-framing cost is transport-level.
- **Lesson adopted:** out of scope for the portable core; `08-networking.md`
  names WebSockets under `net`'s transport ownership, so a future escape
  may expose it behind the same request/response model.

### 2.7 RPC: JSON-RPC, gRPC, GraphQL

- **JSON-RPC:** simple request/response envelope (`id`, `method`, `params`)
  — elegant, but it is a *protocol*, not an API shape.
- **gRPC:** schema-first, HTTP/2, codegen — directly violates the "no
  codegen, portable core" rule; service definitions are a second grammar.
- **GraphQL:** a query language plus a resolution layer; heavyweight, and
  its introspection/executor complexity has no place in `net`.
- **Lesson adopted:** none of these belong in the portable core; an RPC
  layer would be a backend escape on top of `net`'s request/response model.

### 2.8 Go `net/http` / Rust `hyper` + `tower`

- **Go `net/http`:** `Handler = func(w, r)` with the `ServeMux`; middleware
  is `func(http.Handler) http.Handler` — the same wrapper-nesting idea.
  Strengths: simple, uniform. Weaknesses: `w`/`r` mutation, no value
  responses.
- **Rust `hyper`/`tower`:** `Service = fn(Request) -> Future<Response>`;
  tower composes layers (the type-level onion). Strengths: rigorous, typed
  request/response values (like ours). Weaknesses: async `Future` coupling,
  static types, high learning curve.
- **Lesson adopted:** both confirm the `Request -> Response` service shape
  and the wrapping-composition model; neither's transport machinery is
  portable.

---

## 3. Cross-cutting analysis

### 3.1 Strengths / weaknesses of the chosen design

**Strengths**

- Ten functions, six `network` + four pure, stdlib-only (`json`): trivially
  portable and testable.
- The whole model is synchronous and in-process: no event loop, no sockets,
  no lifecycle — every behavior is a pure function of its arguments
  (plus the auto-start side effect on the server value, which JS also has).
- Value shapes (Server/Request/Response) are plain JSON-friendly dicts:
  serializable, greppable, diffable, and property-testable.
- Deterministic middleware ordering with a one-sentence rule: first entry
  in the list runs first.
- Handlers are plain callables; the `501 "no handler"` convention makes a
  handlerless server a first-class, testable state.

**Weaknesses**

- No real transport: nothing actually goes over a wire. This is the
  intended trade-off (08-networking.md §5) — `http` and future backend
  escapes provide it.
- Auto-start mutates the server value; callers sharing a server value
  observe the `"running": true` flag appear.
- JS/Python truthiness and coercion differences create a small set of
  documented deviations (§6).

### 3.2 Performance

- All functions are O(1) or O(n) in message size with no copying beyond
  construction; `middleware` wraps O(n) closures per chain build.
- `response_json` uses C-accelerated `json.dumps`.
- For the target workload (small, schema-shaped, in-process messages),
  performance is a non-issue; real throughput belongs to backend escapes.

### 3.3 Ergonomics

- Names read as plain verbs and match the JS lane exactly — one mental
  model for both backends.
- Middleware authors write `def mw(req, next_fn): ... return next_fn(req)`,
  the most widely known web-programming shape there is.
- The `Response` accessors (`status_of`, `body_of`) make responses inert
  data that handlers and tests can assert on.

### 3.4 Type-system interaction (dynamic vs static typing)

- Registry signatures use `fn(fn) -> Server`, `fn(Server, Text, Text, Text)
  -> Response`, etc.; Python mirrors them with `Callable`, `Server`,
  `Request`, `Response` TypeAliases (`dict[str, Any]`) and `str`/`int`.
- `Request`/`Server`/`Response` are TypeAliases, deliberately *not* in
  `__all__` — the public surface is exactly the ten registry names.
- `cast` bridges the untyped dict access (`server["handler"]`) to the typed
  `Handler`/`int`/`str` views required by `mypy --strict`.

### 3.5 Portability

- Stdlib-only (`json`); runs on any CPython ≥3.11 with no install surface.
- The registry lists `js_deps = ("core", "collections")` for the JS inliner,
  but the Python lane imports nothing — `net.js` has no panic conditions and
  uses no collection helpers, so `omnisys_core` is not needed.
- Behavior is platform-independent: strings, ints, and JSON are
  locale-independent.

### 3.6 Lifecycle / error model

- No exceptions in the portable core: the only "failure" is the
  deterministic `501 "no handler"` response. The JS lane likewise never
  throws for contract-conforming inputs.
- `request` auto-starts a not-running server (JS `if (!server.running)
  server.running = true`), so a fresh server is usable immediately.
- `start` is the explicit form; both are idempotent.

### 3.7 AI usability

- Ten greppable names, two value shapes, one middleware signature — a
  model can enumerate the whole module from memory.
- Handlers are plain functions of a plain dict: an agent can write, test,
  and verify them with no framework knowledge.
- `response_json`'s compact, non-escaped JSON text is human/LLM-readable
  and diffs cleanly (matching `JSON.stringify`, as `serde.json_encode`
  does).

### 3.8 Interop

- All values are JSON-friendly, so any handler output can be serialized via
  `serde` and transported by any backend escape.
- Cross-lane interop is the headline goal: the Python lane reproduces the
  JS value shapes and defaults exactly (deviations in §6), so a request
  built on one lane behaves identically on the other.
- `response_json` bodies round-trip through `json.loads`/`JSON.parse`
  identically.

---

## 4. Concrete design decisions for THIS Python implementation

1. **`server(handler=None)` mirrors JS exactly.** JS `net.server()` with no
   argument stores `undefined`; Python defaults the handler to `None`. The
   value shape is `{"tag": "server", "handler": handler, "middlewares": []}`
   — byte-identical to the JS reference.
2. **`request` auto-starts before building the request.** `if not
   server.get('running'): server['running'] = True` reproduces JS truthiness
   for absent (`None`), `False`, `0`, `''`, and empty-collection flags.
   `.get` also tolerates hand-built servers that omit the key.
3. **Request normalization is exact:** `str(method).upper()`, `str(path)`,
   `'' if body is None else str(body)`, `headers: {}`. Python `None` plays
   the role of JS `undefined`/`null`.
4. **Handler dispatch guards on falsiness** (`if not handler`), reproducing
   JS `if (!server.handler)`; a `cast` keeps `mypy --strict` clean. Falsy
   handlers (`None`, `0`, `''`, `[]`, `False`) all answer `501 "no handler"`.
5. **`middleware` implements the JS loop literally**, including the
   immediately-invoked closure form:
   `wrapped = (lambda _mw, _nxt: (lambda _req: _mw(_req, _nxt)))(mw, wrapped)`,
   plus the final `lambda req: wrapped(req)` wrapper. Result: the first
   entry in the list is outermost and runs first; responses unwind in
   reverse. (Verified against Node: `middleware(h, [a, b])` executes
   `a, b, h`.)
6. **`response` always stringifies the body** (`str(body)`), matching JS
   `String(body)`.
7. **`response_json` uses `ensure_ascii=False` and compact separators**
   (`separators=(',', ':')`), so the body text matches JS `JSON.stringify`
   byte-for-byte for JSON-compatible values (non-ASCII verbatim,
   `{"a":1}` not `{"a": 1}`).
8. **`status_of`/`body_of` follow the contract's `not response`
   formulation** — 0/'' for any falsy response (including `{}`/`[]`, which
   are truthy in JS; see deviation D5).
9. **`__all__` is exactly the ten registry names**; TypeAliases
   (`Request`, `Server`, `Response`, `Handler`, `Middleware`) are private.
10. **No `omnisys_core.panic` import.** The task rule says "where
    applicable", and `net.js` has zero panic conditions — the module has no
    failure branches at all.
11. **Stdlib only** (`json`); the module can be copied into any Python
    environment.

---

## 5. Deviations from the JS reference

| # | JS (`omnisys/net.js`) | Python (`omnisys_net`) | Impact |
|---|---|---|---|
| D1 | `String(null)` → `'null'` in `response` | `str(None)` → `'None'` | `response(200, None)` bodies differ. Contract text mandates `str(body)`; registry types body `Text`, so this is an out-of-contract corner. |
| D2 | `JSON.stringify` on `undefined` value → body `"undefined"` | `response(200)` with no body raises `TypeError` (body is a required param) | Omitted-argument misuse only; registry requires a body. |
| D3 | `JSON.stringify(1.0)` → `'1'` (single float type) | `json.dumps(1.0)` → `'1.0'` | Integral floats in `response_json` bodies differ; spec §13.5 sanctions float rendering differences between backends. |
| D4 | `middleware` tolerates a falsy handler (`undefined`) | handler is typed `Callable[[Request], Response]` (registry: `fn(fn, List) -> fn`) | Passing a non-callable handler is a static error in Python; both lanes throw `TypeError` at call time if a chain step actually calls `next`. |
| D5 | `{}`/`[]` are truthy: `status_of({})` → `undefined`, `body_of({})` → `undefined` | `{}`/`[]` are falsy: `status_of({})` → `0`, `body_of({})` → `''` | Contract text (`0 if not response else ...`) adopts Python truthiness; the JS result for an empty object is `undefined`, never a useful status. |
| D6 | `String(false)` → `'false'`, `String(true)` → `'true'` | `str(False)` → `'False'`, `str(True)` → `'True'` | Boolean bodies in `response` render differently; registry types body `Text`, so out of contract. |
| D7 | `method.toUpperCase()` uses Unicode-aware case mapping | `str(method).upper()` uses Unicode-aware case mapping | Behaviorally identical; noted for completeness. |
| D8 | JS `undefined` (`request(server, m, p)` omitting body) | `body` defaults to `None` | Same observable result (`""`); covered by D1's `None` mapping. |

Every deviation is documented and covered by either a unit test or an
explicit RESEARCH note; none affects contract-conforming `Text`/JSON usage.

---

## 6. Open questions

1. **Real transport escape:** the architecture doc (08-networking.md §5)
   names socket lifecycle ownership, TLS integration (`crypto`), and
   HTTP/2/3 plans as open. The Python lane keeps them backend escapes.
2. **`middleware` falsy-handler tolerance:** the registry types the handler
   `fn(fn, List) -> fn`, so the Python lane rejects a non-callable handler
   statically (D4). If a future use case needs JS-style leniency, the type
   can widen to `Callable | None` with a runtime guard.
3. **`response_json` separator policy:** compact separators were chosen for
   byte-parity with `JSON.stringify`. `serde.json_encode` keeps default
   separators (`{"a": 1}`); the two Python functions therefore differ in
   spacing for the same value. Revisit if cross-module text equality
   matters.
4. **Header capitalization:** `content-type` is lowercase to match the JS
   literal; real HTTP headers are case-insensitive, so any backend escape
   should normalize on transport.
5. **Streaming / large bodies:** the in-process model builds full strings.
   A streaming escape belongs in `http` or a backend, not the portable core.

---

## 7. How to read the gates for this module

- **Coverage:** every branch is exercised — auto-start on/off (absent/True/
  False `running`), `body is None` vs not, falsy vs truthy handler, empty vs
  non-empty middleware list, middleware chain invocation (inner closure
  body), falsy vs real responses in `status_of`/`body_of`; ≥95% branch
  enforced, 100% aimed.
- **Conformance:** `tests/test_conformance.py` locks the ten registry names,
  their callability, their module origin, the exact `__all__` set
  (`_ALLOWED_EXTRA` empty), and the six-`network`/four-pure effect
  partition.
- **Properties:** `tests/test_properties.py` pins middleware chain order
  soundness (forward run, reverse unwind, request identity through the
  chain), request normalization invariants (uppercased method, stringified
  path/body, empty headers), auto-start invariants, and shape soundness
  (response shapes, `response_json` round-trips, falsy accessors).
- **Typing/linting:** mypy `--strict` on `src` (zero errors), ruff clean
  (E, F, I, UP, B, SIM, N, D, PL, T20, PTH, ERA, Q, TID, RET; line length
  100; single quotes).

The research gate, the registry contract, and the JS reference together
determine every line of this implementation; there is no
backend-specific behavior hidden in the portable core.