# OMNISYS Capability Matrix

**Deliverable §14C.** How OMNISYS modules map onto OmniScript's effect and
capability system.

The effect system (OMNI_SPEC.md §8) is the **single** permission model — no
module has its own. A function that calls an OMNISYS API must declare the
capability that API requires, and the compiler enforces it (a `pure` function
calling `omnisys.fs.write_file` fails to compile with `E-EFFECT-001`).

---

## 1. Module → Capability Map

| Module | Capability(s) used |
|--------|--------------------|
| `core` (incl. collections/serde/error) | `panic` (abort-capable fns: `panic`, `throw_error`, `json_decode`, `base64_decode`) |
| `ui` | `screen`, `input` |
| `db` | `database` |
| `graphics` | `GPU` |
| `gpu` | `GPU` |
| `net` | `network` |
| `http` | `network` |
| `audio` | `audio`, `microphone` |
| `video` | `camera`, `video` |
| `fs` | `filesystem` |
| `crypto` | `crypto` (pure hashing), `secrets` (key material) |
| `auth` | `auth`, `database` |
| `sim` | `simulation` (optional `GPU` for physics) |
| `ai` | `AI`, `GPU` |
| `test` | `test` (pure) |
| `async` | `async` (pure; `network` in distributed mode) |
| `platform` | `platform`, `camera`, `microphone`, `process` |
| `scene` | `scene`, `GPU` |

The machine-readable form is generated from the `<!-- CAPABILITIES: … -->`
tags in the module READMEs:
[`../CAPABILITY_MATRIX.md`](../CAPABILITY_MATRIX.md).

## 2. Capability Vocabulary

The full vocabulary (spec §8.2 plus the platform-layer additions):

```
network   filesystem   database   camera   microphone
GPU       process      secrets    screen   input
audio     video        auth       crypto   AI
simulation  scene      platform   test     async
panic
```

`panic` is not a resource: it marks functions that may **abort control flow**
(throw) at runtime. Per the honesty rule the declaration must match behavior,
so a `pure` function that calls an abort-capable OMNISYS function
(`omnisys.core.panic`, `omnisys.error.throw_error`, fallible serde decoders)
fails with `E-EFFECT-001`; callers must declare `uses panic`.

## 3. Enforcement Model

1. **Declaration.** A function declares capabilities via `uses`/`reads`/
   `writes`/`pure` (spec §8.1).
2. **Registry knowledge.** The compiler knows each OMNISYS call's required
   capabilities from `omnisys_registry.py` (`omnisys_effects(name)`).
3. **Transitive inference.** Calling an OMNISYS function (or any function)
   inherits its effects transitively (spec §8.4).
4. **Per-backend gate.** A capability must be provided by the selected target
   backend (spec §8.3). The gate is **per-capability, not per-import**: the JS
   lane is the reference OMNISYS runtime, so a program that actually calls an
   `omnisys.*` function is rejected on native (C/Rust/WASM) targets with
   `E-BACKEND-001`. An import-only program (an `import OMNISYS` that never
   invokes an OMNISYS function) consumes no capability and builds on native
   targets — the documented §8.3 carve-out.
5. **Compile-time rejection.** Violations produce `omni.diagnostic` JSON with a
   stable code and a ranked, machine-applicable fix.

## 4. Why One Model

- **AI**: one rule to reason about; the registry makes every call's cost known.
- **Learners**: nothing to memorize — a `pure` function is pure, everywhere.
- **Devs**: no per-framework permission systems to learn or audit.

*See also:* [`03-backend-matrix.md`](03-backend-matrix.md) for which
capabilities exist per target.