# OMNISYS.auth — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/auth.js` and the compiler registry
`OMNISYS_MODULES["auth"]`.

## 1. Ecosystems studied

- **JWT / JWS (RFC 7519/7515)** — the compact signed-token pattern this lane
  mirrors (header/body/signature, base64url, HMAC-SHA256). Kept: compact
  `body.signature` tokens with constant-time signature verification.
- **OAuth2 / OpenID Connect** — flows and scopes; not adopted (an escape) —
  the registry surface is single-token primitives only.
- **bcrypt / PBKDF2 / scrypt** — purpose-built password KDFs; the JS lane
  uses the custom sha256-chain `crypto.kdf`, so this lane matches that.
- **Session stores** — in-memory/db session maps with TTL; mirrored via
  `expiresAt`.

## 2. What was adopted

- Compact token = base64url(JSON payload) + `.` + first 24 hex chars of
  HMAC-SHA256(secret, body).
- `sub`/`iat` payload with claims merge (claims override on conflict).
- `verify_token` three-stage check: shape → signature → payload, with an
  explicit `reason` map instead of panics.
- Password hash `salt$kdf(password, salt, 128)`; verification re-derives and
  compares in constant time.
- Session maps with `expiresAt`; `session_valid` tolerates falsy input.

## 3. Strengths / weaknesses of the studied ecosystems

- JWT: standardized, stateless; needs a real signing library and has no
  revocation story.
- OAuth2: complete authZ; heavyweight, flow-based.
- bcrypt/PBKDF2: strong KDFs; dependency-backed (escape for production).
- Session stores: revocable, simple; require persistence (the host's job).

## 4. Performance

- Token sign/verify are O(payload) base64url + one HMAC. Password hash/verify
  run `crypto.kdf` at 128 rounds. No locking in the single-threaded model.

## 5. Type-system interaction / portability

- Registry types: `fn(Text, Map, Text) -> Text`, `fn(Text, Text) -> Map`,
  `fn(Text, Text) -> Boolean`, `fn(Text, Text, Number) -> Map`. Python uses
  `Token`/`Session`/`VerifyResult` aliases over `str` / `dict[str, Any]`.

## 6. Lifecycle / error / concurrency model

- Stateless functions (plus time-dependent `iat`/`expiresAt`). No panics:
  verification failures are encoded in the result map's `reason`. Session
  validity is a pure time comparison against `int(time.time())`.

## 7. AI usability

- A token is a plain string and a session a JSON map — an agent can mint,
  verify, extract subjects, hash/verify passwords, and check session expiry
  without a runtime, and reason about failures via the `reason` field.

## 8. Interop requirements

- Future escapes: real JWT libraries, OAuth2 flows, bcrypt/PBKDF2/scrypt,
  server-side session stores — all consume the same compact-token semantics.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/auth.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `b64url` = hex round-trip then base64 of UTF-16 binary | base64url of UTF-8 directly | Payloads are ASCII (JSON escapes), so identical for all real tokens |
| 2 | `verify_token` returns `sub` undefined when absent | `payload.get('sub')` → `None` | Same semantics; JSON `null` serializes as `null` |
| 3 | `payload.sub` accessed directly | `payload.get('sub')` + non-dict guard | Python indexing would raise; explicit guard maps to `reason: payload` |
| 4 | `new TextDecoder().decode(bytes)` (UTF-8) | `base64.urlsafe_b64decode(...).decode('utf-8')` | Same for ASCII payloads |
| 5 | `token.iat = Math.floor(Date.now()/1000)` | `int(time.time())` | Same unix-seconds semantics |

## 10. Verification

- `python -m pytest packages/omnisys-auth/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-auth/src` **100% branch**.
- `mypy --strict packages/omnisys-auth/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-auth` — clean.