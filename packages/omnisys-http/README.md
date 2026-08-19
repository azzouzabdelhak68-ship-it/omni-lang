# OMNISYS.http

Python reference implementation of the OMNISYS `http` module: a high-level
HTTP client/server built on the OMNISYS.net portable transport.

- **Registry**: `OMNISYS_MODULES["http"]` — `client`, `send`, `get`, `post`,
  `put`, `delete`, `json_get`, `json_post` declare the `network` capability;
  `redirect`/`not_found` are pure. All functions are plain synchronous Python.
- **Import**: `from omnisys_http import client, get, post, json_get, ...` —
  add `packages/omnisys-http/src` (and `packages/omnisys-net/src`,
  `packages/omnisys-core/src`) to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Client = `{"tag": "http.client", "transport": "portable"}`;
  Response = `{"status": int, "headers": {}, "body": str}` (same as net).
- **Semantics**: mirrors `omnisys/http.js` — `inproc://host/path` URLs
  dispatch to a server bound with `register(name, server)`; any other URL is
  routed through the transport hook set with `register_transport(fn)` (an
  escape/`__transport`-style hook); a malformed URL or an unhandled scheme
  panics with `omnisys_core.PanicError`. `send` ignores the client value,
  exactly like JS.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.