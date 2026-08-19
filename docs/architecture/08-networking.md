# OMNISYS Networking Architecture

**Deliverable §14I.** Low-level networking (`net`) and high-level HTTP
(`http`), designed native for OmniScript.

Module READMEs: [`../omnisys/net/README.md`](../omnisys/net/README.md),
[`../omnisys/http/README.md`](../omnisys/http/README.md).

---

## 1. Layering

```
OMNISYS.http (routing, middleware, high-level client/server)
        │
        ▼
OMNISYS.net (TCP, UDP, WebSockets, request/response primitives)
        │
        ▼
     async (non-blocking I/O) · crypto (TLS) · serde (payloads)
```

- `net` owns transport and the wire contract.
- `http` owns semantics: routing, middleware ordering, request/response
  modeling, status codes, JSON bodies.
- `async` provides the concurrency substrate; `crypto` provides TLS
  (spec §17.6.4 for the capability mapping).

## 2. OMNISYS.net — Transport Layer

```omni
import OMNISYS.net

srv   = server(handler)          # create server
start(srv)                       # begin accepting
resp  = request(srv, "GET", "/api/items", "")
mw    = middleware(handler, [log, auth])
```

- `server`, `start`, `request`, `get`, `post` — client + server in one model.
- `middleware` composes handlers; ordering semantics are explicit.
- `response`, `response_json`, `status_of`, `body_of` — a typed `Response`
  value, independent of the host socket API.

## 3. OMNISYS.http — High-Level HTTP

```omni
import OMNISYS.http

c    = client()
resp = send(c, "GET", "https://api.example.com/v1", "")
data = json_get("https://api.example.com/v1")
```

- `client`, `send`, `get`, `post`, `put`, `delete` — the everyday verbs.
- `json_get`/`json_post` — deserialize directly to OmniScript values.
- `redirect`, `not_found` — semantic response builders.

## 4. Capabilities

Every network-touching function declares `uses network` (§17.5). TLS, when
enabled, additionally touches `crypto`/`secrets`. A pure middleware pipeline
that never touches the wire stays pure.

## 5. Open Design Questions (carried from READMEs)

- Socket lifecycle ownership
- TLS integration point (`crypto`)
- Middleware ordering semantics
- HTTP/2 and HTTP/3 support plan