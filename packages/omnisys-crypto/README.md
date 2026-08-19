# OMNISYS.crypto

Python reference implementation of the OMNISYS `crypto` module: SHA-256 /
SHA-1 hashing, HMAC-SHA256, UTF-16 hex encoding, secure random bytes, a
portable AES-style cipher, a KDF, and constant-time comparison.

- **Registry**: `OMNISYS_MODULES["crypto"]` — 10 functions. Four declare the
  `secrets` capability (`random_bytes`, `encrypt_aes`, `decrypt_aes`, `kdf`);
  the rest are pure. `js_deps` = `("core", "error")`.
- **Import**: `from omnisys_crypto import sha256, sha1, hmac, to_hex, from_hex,
  random_bytes, encrypt_aes, decrypt_aes, kdf, constant_time_eq` — add
  `packages/omnisys-crypto/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: hex strings are lowercase; `encrypt_aes` returns
  `{"tag": "cipher", "iv": <hex>, "data": <hex>}`; `decrypt_aes` consumes that
  map and returns text.
- **Semantics**: mirrors `omnisys/crypto.js` — `to_hex`/`from_hex` work on
  UTF-16 code units (per-character `ord`/`chr`, NOT UTF-8 `.hex()`); `sha256`
  /`sha1`/`hmac` use `hashlib`; `random_bytes(n)` is
  `secrets.token_hex(max(0, n))`; `kdf(password, salt, iterations)` chains
  sha256 rounds (minimum 1); `constant_time_eq` uses
  `hmac.compare_digest` (constant-time).
- **Cipher**: real AES-256 is a documented escape. The portable
  `encrypt_aes`/`decrypt_aes` XOR each UTF-16 code unit against a keystream of
  hex digits derived from `sha256(key)` with an incrementing counter
  (`sha256(hexKey + ":" + counter++)`), matching the JS lane exactly. The `iv`
  is included but is informational; it does not perturb the keystream.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.