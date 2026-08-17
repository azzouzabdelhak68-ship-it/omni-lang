# OMNISYS.auth

## Purpose

Authentication and authorization: OAuth, JWT, sessions, identity management.

## Public API surface

```omni
import OMNISYS.auth

fn login(credentials: Credentials) -> Result
fn authorize(token: Text, scope: Text) -> Result
```

## Dependencies

- `core`
- `crypto` (token signing/validation)
- `db` (session storage)

## Effects/capabilities used

- `reads database`
- `writes database`

## Status

planned

## Open Questions

- Session revocation model
- Multi-tenant isolation

<!-- CAPABILITIES: auth; database -->