# OMNISYS

**OMNISYS** is the official application framework and standard ecosystem for
OmniScript. The language core remains small; capabilities belong in OMNISYS
modules, not language keywords.

See [`../../OMNI_SPEC.md`](../../OMNI_SPEC.md) §17 for the full OMNISYS charter.

## Module Tree

The canonical 17-module tree (from `OMNI_SPEC.md` §17.1), plus the implicit
`core` root export (`import OMNISYS` provides `core` without a sub-import):

| Module | Purpose |
|--------|---------|
| `core` | Implicit root export: prelude, result/option, validation. Subsumes `collections`, `serde`, `error` as internal submodules |
| `ui` | Cross-platform UI |
| `db` | Data platform |
| `graphics` | Rendering abstraction |
| `gpu` | GPU compute |
| `net` | Networking |
| `http` | High-level HTTP client/server |
| `audio` | Audio I/O |
| `video` | Video |
| `fs` | Filesystem |
| `crypto` | Cryptography |
| `auth` | Authentication/Authorization |
| `sim` | ECS, physics, simulation |
| `ai` | AI/ML |
| `test` | Testing |
| `async` | Async/concurrency |
| `platform` | Platform APIs |
| `scene` | 3D scene graph |

## Dependency Map

- **Phase 1 (Foundations)**: `core` (incl. `collections`, `serde`, `error`),
  `async`, `fs`, `test`
- **Phase 2 (App Foundations)**: `ui`, `db`, `net`, `http`
- **Phase 3 (Graphics/GPU/Sim)**: `graphics`, `gpu`, `scene`, `sim`
- **Phase 4 (Media/Platform)**: `audio`, `video`, `platform`
- **Phase 5 (Security)**: `crypto`, `auth`
- **Phase 6 (AI/Advanced)**: `ai`, `async` (advanced), `pkg`

## Subsystem READMEs

- [`core/README.md`](core/README.md)
- [`ui/README.md`](ui/README.md)
- [`db/README.md`](db/README.md)
- [`graphics/README.md`](graphics/README.md)
- [`gpu/README.md`](gpu/README.md)
- [`net/README.md`](net/README.md)
- [`http/README.md`](http/README.md)
- [`audio/README.md`](audio/README.md)
- [`video/README.md`](video/README.md)
- [`fs/README.md`](fs/README.md)
- [`crypto/README.md`](crypto/README.md)
- [`auth/README.md`](auth/README.md)
- [`sim/README.md`](sim/README.md)
- [`ai/README.md`](ai/README.md)
- [`test/README.md`](test/README.md)
- [`async/README.md`](async/README.md)
- [`platform/README.md`](platform/README.md)
- [`scene/README.md`](scene/README.md)