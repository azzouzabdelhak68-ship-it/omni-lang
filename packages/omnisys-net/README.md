# OMNISYS.net

## Purpose
In-process, synchronous, deterministic request/response model (server value + handler + middleware chain), plus pure `Response` builders and accessors.

## Public API surface
`server`, `start`, `request`, `get`, `post`, `middleware`, `response`, `response_json`, `status_of`, `body_of`

## Dependencies
`omnisys_core` (for `Result`, `Option`, `Error` types)

## Effects/capabilities used
`network` (declared by `server`, `start`, `request`, `get`, `post`, `middleware`); `response`, `response_json`, `status_of`, `body_of` are pure

## Status
stable

## Open Questions
None at this time.

---

Python reference implementation of the OMNISYS `net` module: an in-process, synchronous, deterministic request/response model (server value + handler + middleware chain), plus the pure `Response` builders and accessors.

- **Registry**: `OMNISYS_MODULES["net"]` — `server`, `start`, `request`, `get`, `post`, `middleware` declare the `network` capability; `response`, `response_json`, `status_of`, `body_of` are pure. The `network` effect is metadata here: every function is a plain synchronous Python function.
- **Import**: `from omnisys_net import server, request, ...` — add `packages/omnisys-net/src` to `PYTHONPATH`, or rely on the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: Server = `{"tag": "server", "handler": callable_or_None, "middlewares": []}` (auto-started with `"running": true` on first request); Request = `{"method": str, "path": str, "body": str, "headers": {}}`; Response = `{"status": int, "headers": {}, "body": str}`.
- **Semantics**: mirrors `omnisys/net.js` exactly — `request` auto-starts the server, uppercases the method, stringifies path/body, and answers `501 "no handler"` when the handler is falsy; `middleware` composes the chain so the first entry in the list runs first; `response_json` matches JS `JSON.stringify` (`ensure_ascii=False`, compact separators).

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation from the JS reference.