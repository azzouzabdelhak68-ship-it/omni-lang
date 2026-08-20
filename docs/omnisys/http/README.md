# OMNISYS.http

## Purpose

High-level HTTP client and server: routing, middleware, request/response
modeling. All operations return Tasks (Promises) enabling timeout composition
via `OMNISYS.async.with_timeout`.

## Public API surface

```omni
import OMNISYS.http
import OMNISYS.async

fn client() -> Client
fn send(client: Client, method: Text, url: Text, body: Text, timeout: Number) -> Task
fn get(url: Text, timeout: Number) -> Task
fn post(url: Text, body: Text, timeout: Number) -> Task
fn put(url: Text, body: Text, timeout: Number) -> Task
fn delete(url: Text, timeout: Number) -> Task
fn json_get(url: Text, timeout: Number) -> Task
fn json_post(url: Text, value: any, timeout: Number) -> Task
fn redirect(location: Text, status: Number) -> Response
fn not_found(body: Text) -> Response
fn response(status: Number, body: Text) -> Response
fn response_json(status: Number, value: any) -> Response
fn register(name: Text, server: Server) -> Server
```

## Dependencies

- `core`
- `net`
- `async`

## Effects/capabilities used

- `uses network`

## Status

stable

## Open Questions

- Middleware ordering semantics
- HTTP/2 and HTTP/3 support plan

<!-- CAPABILITIES: network -->