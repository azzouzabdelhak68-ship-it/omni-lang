# OMNISYS.http — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/08-networking.md`. Grounded in the JS references
`omnisys/http.js` + `omnisys/net.js` and the compiler registry
`OMNISYS_MODULES["http"]`.

## 1. Ecosystems studied

- **fetch / XMLHttpRequest** — method + URL + body → `Response`; JSON
  helpers (`json_get`/`json_post` mirror `res.json()`).
- **Express/Koa middleware** — handler chains around a request/response;
  `register` + the net middleware model mirror this.
- **Werkzeug/FastAPI** — request routing and response builders; `redirect`/
  `not_found` are the status-shaped helpers every framework exposes.
- **inproc:// model** — Node's http server on `127.0.0.1` for tests; OMNISYS
  makes the in-process dispatch explicit and deterministic (`register`), so
  tests need no sockets.

## 2. What was adopted

- Method-dispatch vocabulary: `get`/`post`/`put`/`delete` + generic `send`.
- URL parsing with an `inproc://` scheme as the portable transport; any other
  scheme requires a registered transport hook (mirrors `http.__transport`).
- Response values identical to `omnisys_net` (single portable shape).
- `redirect(location, status=302)` and `not_found(body)` response builders.

## 3. Strengths / weaknesses of the studied ecosystems

- fetch: ergonomic, promise-based; browser-only in origin.
- Express/Koa: superb middleware ergonomics; Node-only, callback/closure-heavy.
- FastAPI: typed and testable; Python-only, ASGI-specific.

OMNISYS keeps the *semantic* client/server model only: deterministic
in-process dispatch + a transport escape hook. The wire (TCP/TLS/HTTP on the
socket) is a future backend escape (`08-networking.md` §5).

## 4. Performance

- In-process dispatch is a dict lookup + a net `request` call — O(1) plus
  handler cost. No sockets, no I/O waits; deterministic and instant.

## 5. Type-system interaction / portability

- Registry types: `fn(Client, Text, Text, Text) -> Response`, `fn(Text) ->
  any`, etc. Python typing uses `Client`/`Response`/`Server`/`Transport`
  aliases over `dict[str, Any]` / `Callable`.
- `send(client, ...)` ignores its first argument — matching JS where the
  client value is likewise unused.

## 6. Lifecycle / error / concurrency model

- Module-level state: the inproc `register` map and the transport hook are
  process-global (like JS `registry`/`__transport`); tests reset them per
  case.
- Errors: malformed URL and unhandled scheme raise `omnisys_core.PanicError`
  with the exact JS messages.

## 7. AI usability

- The entire dispatch path is pure value plumbing over a JSON URL string and
  JSON bodies; an agent can bind a handler, call `json_post`, and inspect the
  parsed response — all in-process and deterministic.

## 8. Interop requirements

- Future escapes: real HTTP/1.1+ transport behind `register_transport`
  (TLS via `omnisys-crypto`, HTTP/2/3 negotiation deferred), preserving the
  `Response` shape.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/http.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `http.__transport` attribute escape | `register_transport(fn)` (clear with `None`) | Explicit public hook; same dispatch semantics |
| 2 | `http.register` / `__registerInproc` | `register(name, server)` | One public binding function |
| 3 | `http.__parseUrl` test hook | `_parse_url` private | Not in the registry surface |
| 4 | malformed URL: `core.panic(...)` | `panic('http: malformed url: ' + url)` | Same message + `PanicError` |
| 5 | `String(body)` when non-null | `str(body)` | Same for str/int; `None→''` sentinel |
| 6 | `parseUrl` regex `[a-z][a-z0-9+.-]*` scheme | same regex (`re.compile`) | Identical |
| 7 | JSON round-trip via `JSON.stringify` | `json.dumps`/`json.loads` | Same for canonical values; float formatting differs (spec §13.5) |

## 10. Verification

- `python -m pytest packages/omnisys-http/tests -q -W error` — 25 tests pass,
  zero warnings.
- Coverage: `packages/omnisys-http/src` **100% branch**.
- `mypy --strict packages/omnisys-http/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-http` — clean.