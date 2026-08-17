# OMNISYS.net

## Purpose

Low-level networking: TCP, UDP, WebSockets; client/server and middleware.

## Public API surface

```omni
import OMNISYS.net

fn listen(port: Int) -> Result
fn connect(host: Text, port: Int) -> Result
fn send(socket: Socket, data: Bytes) -> Result
```

## Dependencies

- `core`
- `async`

## Effects/capabilities used

- `uses network`

## Status

planned

## Open Questions

- Socket lifecycle ownership
- TLS integration point (`crypto`)

<!-- CAPABILITIES: network -->