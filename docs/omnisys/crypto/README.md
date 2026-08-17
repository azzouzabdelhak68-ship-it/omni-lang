# OMNISYS.crypto

## Purpose

Cryptography: hashing, encryption/decryption, digital signatures, key
derivation, TLS.

## Public API surface

```omni
import OMNISYS.crypto

fn hash(data: Bytes, algo: Text) -> Bytes
fn encrypt(key: Key, data: Bytes) -> Result
fn sign(key: Key, data: Bytes) -> Result
```

## Dependencies

- `core`

## Effects/capabilities used

- `uses crypto`

## Status

planned

## Open Questions

- Algorithm whitelist
- Key management/storage model

<!-- CAPABILITIES: crypto -->