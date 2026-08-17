# OMNISYS.http

## Purpose

High-level HTTP client and server: routing, middleware, request/response
modeling.

## Public API surface

```omni
import OMNISYS.http

fn serve(port: Int, router: Router) -> Result
fn get(url: Text) -> Result
```

## Dependencies

- `core`
- `net`

## Effects/capabilities used

- `uses network`

## Status

planned

## Open Questions

- Middleware ordering semantics
- HTTP/2 and HTTP/3 support plan

<!-- CAPABILITIES: network -->