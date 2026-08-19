# OMNISYS Module Tree

**Deliverable §14B.** The canonical OMNISYS module tree, its layers, and its
dependency map.

The authoritative module list lives in [`../../OMNI_SPEC.md`](../../OMNI_SPEC.md)
§17.1 and in the compiler registry `omni_compiler/omnisys_registry.py`. This
document is the architecture-level reading of that tree.

---

## 1. The Tree

```
OMNISYS (umbrella)                     ← import OMNISYS = core
├── core                               ← implicit root: prelude, Result/Option,
│   │                                     math, length/empty helpers, panic
│   ├── collections                    ← internal submodule (List/Map/Set/…)
│   ├── serde                          ← internal submodule (JSON/CSV/hex/b64)
│   └── error                          ← internal submodule (Error/context)
├── ui                                 ← cross-platform semantic UI
├── db                                 ← data platform (SQL, migrations, txns)
├── graphics                           ← portable rendering abstraction
├── gpu                                ← GPU compute (CUDA/Metal/Vulkan/WebGPU)
├── net                                ← TCP/UDP/WebSockets
├── http                               ← high-level HTTP client/server
├── audio                              ← audio I/O, synthesis, processing
├── video                              ← video decode/encode/streaming
├── fs                                 ← filesystem
├── crypto                             ← hashing, encryption, signatures, KDF, TLS
├── auth                               ← AuthN/AuthZ, OAuth, JWT, sessions
├── sim                                ← ECS, physics, simulation
├── ai                                 ← tensors, autograd, inference, tool use
├── test                               ← assertions, property testing, mocking, bench
├── async                              ← Task/Future/Stream/Channel/Select/Timeout
├── platform                           ← native platform APIs (OS, device access)
└── scene                              ← 3D scene graph
```

`collections`, `serde`, and `error` are **internal submodules of `core`**, not
separate top-level imports. This reconciles §17.7's Phase 1 list with the
18-document module count.

## 2. Layers & Development Phases

| Phase | Modules | Focus |
|-------|---------|-------|
| 1. Foundations | `core` (incl. collections/serde/error), `async`, `fs`, `test` | Core utilities, collections, async, filesystem, serialization, errors, testing |
| 2. App Foundations | `ui`, `db`, `net`, `http` | UI, database, networking, HTTP |
| 3. Graphics/GPU/Sim | `graphics`, `gpu`, `scene`, `sim` | Rendering, GPU compute, 3D scene, ECS/physics |
| 4. Media/Platform | `audio`, `video`, `platform` | Media, device access, native APIs |
| 5. Security | `crypto`, `auth` | Security, auth |
| 6. AI/Advanced | `ai`, `pkg`, advanced `async` | Tensors, autograd, distributed actors, package manager |

## 3. Dependency Map

Dependencies are recorded twice: as `js_deps` in the registry (for JS emitter
inlining order) and in each module README (for humans).

- `collections`, `serde`, `error` → `core`
- `async`, `fs`, `test` → `core`; `test` also → `collections`
- `ui` → `core`, `collections`
- `db` → `core`, `collections`
- `net` → `core`, `collections`; `http` → `core`, `net`
- `graphics`, `gpu`, `scene`, `sim` → `core` (+ `graphics` for `gpu`; `gpu` for `ai`)
- `audio`, `video` → `core` (+ `platform` for `audio`; `audio` for `video`)
- `crypto` → `core`, `error`; `auth` → `core`, `crypto`
- `platform` → `core`
- `ai` → `core` (GPU acceleration via `gpu` when available)
- `pkg` → `core`, `serde`, `fs`

The umbrella import `import OMNISYS` **must not force compilation of all
subsystems** — implementations use dependency analysis and lazy loading so
unused subsystems do not increase binary size, startup time, or build cost.

## 4. Module READMEs

Every module has a `README.md` under
[`../omnisys/`](../omnisys/README.md) with the six-field convention set
(`docs/DOC_CONVENTIONS.md` §3): Purpose, Public API surface, Dependencies,
Effects/capabilities used, Status, Open Questions.

## 5. Guarantees

- Every module in the tree is resolvable by the compiler registry.
- Every module has a documented public API and declared capabilities.
- No capability or API shape leaks between modules except through the declared
  dependency edges above.