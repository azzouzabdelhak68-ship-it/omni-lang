# OMNISYS Security Architecture

**Deliverable §14L.** Cryptography, authentication/authorization, and the
secrets capability.

Module READMEs: [`../omnisys/crypto/README.md`](../omnisys/crypto/README.md),
[`../omnisys/auth/README.md`](../omnisys/auth/README.md).

---

## 1. Scope

| Module | Owns |
|--------|------|
| `crypto` | Hashing, encryption/decryption, signatures, KDF, TLS |
| `auth` | AuthN/AuthZ, OAuth, JWT, sessions, identity |

The security story is two modules plus one capability discipline:
`secrets` is a first-class capability, so key material and credentials are
never silently accessible.

## 2. OMNISYS.crypto

```omni
import OMNISYS.crypto

sha256("data")                        # pure hash
key = kdf("password", salt, 100000)   # uses secrets
enc = encrypt_aes(key, "payload")     # uses secrets
```

- Pure primitives: `sha256`, `sha1`, `hmac`, `to_hex`, `from_hex`,
  `constant_time_eq`.
- Secrets-touching: `random_bytes`, `encrypt_aes`, `decrypt_aes`, `kdf`.
- TLS builds on the same primitives for the networking layer
  (spec §17.6.4).

## 3. OMNISYS.auth

```omni
import OMNISYS.auth

tok = token(subject, claims, secret)      # sign
map = verify_token(tok, secret)           # verify → subject/claims
s   = session_new(subject, secret, 3600)
session_valid(s)
```

- `token`, `verify_token`, `token_subject` — JWT-style tokens.
- `hash_password`, `verify_password` — credential handling.
- `session_new`, `session_valid` — session lifecycle.
- Sessions persist through `db`; token signing/validation through `crypto`.

## 4. Capability Discipline (spec §17.5)

| Operation | Capability |
|-----------|------------|
| Key derivation / crypto with key material | `uses secrets` |
| Random bytes / encryption / decryption | `uses secrets` |
| Token signing / password hashing | `uses secrets` |
| Session storage | `reads database` / `writes database` |

A pure function can hash data (`sha256`) but cannot derive a key or sign a
token — the compiler enforces the boundary.

## 5. Threat Posture

- Secrets never appear in logs or snapshots (capability-gated).
- Constant-time comparison for sensitive equality.
- Tokens are verified, never trusted from input.
- TLS uses `crypto` primitives rather than host-special magic.

## 6. Open Design Questions (carried from READMEs)

- Algorithm whitelist
- Key management/storage model
- Session revocation model
- Multi-tenant isolation