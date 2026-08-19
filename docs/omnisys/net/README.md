# OMNISYS.net

## Purpose

In-process, deterministic request/response model for testing and simulation. Not a real socket layer.

## Public API surface

```omni
import OMNISYS.net

fn server(handler: fn) -> Server
fn start(server: Server) -> Server
fn request(server: Server, method: Text, path: Text, body: Text) -> Response
fn get(server: Server, path: Text) -> Response
fn post(server: Server, path: Text, body: Text) -> Response
fn middleware(handler: fn, chain: List) -> fn
fn response(status: Number, body: Text) -> Response
fn response_json(status: Number, value: any) -> Response
fn status_of(response: Response) -> Number
fn body_of(response: Response) -> Text
```

## Dependencies

- `core`
- `collections`

## Effects/capabilities used

- `uses network`

## Status

stable

## Open Questions

None at this time.

## Value shapes

- Server = `{"tag": "server", "handler": callable_or_None, "middlewares": [], "running": Boolean}`
- Request = `{"method": Text, "path": Text, "body": Text, "headers": Map}`
- Response = `{"status": Number, "headers": Map, "body": Text}`

## Semantics

`request` auto-starts the server if not already running, uppercases the method, and stringifies path/body. Returns 501 "no handler" when handler is falsy. `middleware` composes the chain so the first entry runs first. `response_json` matches JS `JSON.stringify` with compact separators.

<!-- CAPABILITIES: network -->