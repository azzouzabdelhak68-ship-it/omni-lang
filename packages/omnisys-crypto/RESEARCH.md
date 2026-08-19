# OMNISYS.crypto — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/crypto.js` and the compiler registry
`OMNISYS_MODULES["crypto"]`.

## 1. Ecosystems studied

- **Node `node:crypto`** — the JS lane's crypto source: `createHash`,
  `createHmac`, `randomBytes`, `pbkdf2` (this lane's `kdf` is a custom
  sha256 chain instead). Pattern kept: hex digests, HMAC keyed by text.
- **WebCrypto (`crypto.subtle`)** — the browser lane. Kept conceptually:
  SHA-256/SHA-1 as the hashing vocabulary.
- **Python `hashlib` / `hmac` / `secrets`** — the Python standard-library
  equivalents used here directly (no re-implementation needed).

## 2. What was adopted

- `sha256`/`sha1`/`hmac` via `hashlib`/`hmac` (real primitives, matching the
  Node path of the JS lane).
- `random_bytes(n)` = `secrets.token_hex(n)` — CSPRNG, hex output identical in
  shape to Node `randomBytes(n).toString('hex')`.
- `to_hex`/`from_hex` as UTF-16 code-unit hex (per-character `ord`/`chr`),
  exactly mirroring the JS lane's `charCodeAt`/`String.fromCharCode`.
- `encrypt_aes`/`decrypt_aes` as the JS XOR keystream cipher, and
  `constant_time_eq` via `hmac.compare_digest` (constant-time).

## 3. Strengths / weaknesses of the studied ecosystems

- Node `node:crypto`: battle-tested, fast; Node-bound (the whole reason for a
  portable lane).
- WebCrypto: async-only, browser-bound, and its AES is real AES (an escape).
- Python stdlib: portable, synchronous, and provides the same primitives —
  the best fit for the reference lane.

## 4. Performance

- Hashing/HMAC are C-backed; `_key_stream` for AES encrypt/decrypt is O(text
  length) sha256 calls (JS-identical, documented slow path). `kdf` is O(rounds).

## 5. Type-system interaction / portability

- Registry types: `fn(Text) -> Text`, `fn(Number) -> Text`, `fn(Text, Text) ->
  Map`, `fn(Map, Text) -> Text`, etc. Python types annotate `Any` inputs
  coerced with `str()`/`int()` (JS coerces with template strings / `| 0`).

## 6. Lifecycle / error / concurrency model

- Stateless pure functions plus `secrets`-capability functions. Errors:
  `from_hex` on invalid hex raises `ValueError` (JS produces `NaN`-garbage;
  divergence documented below). No shared mutable state.

## 7. AI usability

- Everything is a string or a small JSON map — an agent can hash, HMAC, derive
  keys, encrypt/decrypt, and compare in constant time without a runtime, and
  verify results against Node in one line.

## 8. Interop requirements

- Future escapes: real AES-256-GCM, PBKDF2/scrypt, RSA/ECDSA — all
  documented as escapes; the portable lane stays dependency-free.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/crypto.js`) | Python (this package) | Reason |
|---|--------------------------|-----------------------|--------|
| 1 | `from_hex` yields `NaN`-affected garbage on invalid input | raises `ValueError` | Python's `int` rejects non-hex; explicit error is safer |
| 2 | `randomBytes(n)` throws for negative `n` | clamps to `max(0, n)` | matches `kdf`'s `Math.max(1, ...)` clamping philosophy |
| 3 | `constant_time_eq` uses manual XOR loop | `hmac.compare_digest` | equivalent constant-time primitive, simpler |
| 4 | `encrypt_aes`'s `iv` participates in nothing | same (informational) | JS also ignores the `iv` in the keystream; kept for shape parity |

## 10. Verification

- `python -m pytest packages/omnisys-crypto/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-crypto/src` **100% branch**.
- `mypy --strict packages/omnisys-crypto/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-crypto` — clean.