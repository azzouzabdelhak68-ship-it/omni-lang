# OMNISYS.auth

Python reference implementation of the OMNISYS `auth` module: signed tokens,
password hashing, and sessions — built on OMNISYS.crypto.

- **Registry**: `OMNISYS_MODULES["auth"]` — 7 functions, all declaring the
  `secrets` capability. `js_deps` = `("core", "crypto")`.
- **Import**: `from omnisys_auth import token, verify_token, token_subject,
  hash_password, verify_password, session_new, session_valid` — add
  `packages/omnisys-auth/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Token = `body.signature` (base64url JSON body + first 24
  hex chars of HMAC-SHA256); Session = `{"tag": "session", "token": ...,
  "subject": ..., "expiresAt": <unix-seconds>}`; `verify_token` returns
  `{"valid": true, "sub": ..., "claims": {sub, iat, ...}}` or
  `{"valid": false, "reason": "malformed"|"signature"|"payload"}`.
- **Semantics**: mirrors `omnisys/auth.js` — `token` merges `sub` + `iat` with
  the given `claims` (claims win on conflict); `verify_token` checks shape,
  HMAC signature (constant-time), then JSON payload; `token_subject` verifies
  against the empty secret; `hash_password` = `salt$kdf(password, salt, 128)`;
  `session_new` expires at `now + (ttlSeconds || 3600)`.
- **Note**: real JWT/OAuth2 and bcrypt/PBKDF2 are documented escapes; this is
  the portable deterministic core. Sessions persist through the host (db).

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.