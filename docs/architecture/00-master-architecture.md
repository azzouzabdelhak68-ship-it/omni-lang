# OMNISYS Master Architecture

**Deliverable §14A.** The authoritative architectural overview of OMNISYS —
the Omni-native platform for OmniScript.

> The language core stays small. Capabilities belong in OMNISYS modules, not
> language keywords. — OMNI_SPEC.md §17.1

---

## 1. What OMNISYS Is

OmniScript is the language. **OMNISYS** is the platform: the official
application framework and standard ecosystem. Its mission is to consolidate
the maturity, capabilities, lessons, and engineering patterns of the best
existing software ecosystems into one coherent, Omni-native platform.

It is **not** a set of wrappers around existing libraries. Per the Golden Rule
(§17.9):

> Do not ask: "How do we put existing libraries into OmniScript?"
> Ask: "If we had all accumulated engineering knowledge today, and were
> designing a unified platform for OmniScript, AI agents, portability, safety,
> performance, and ergonomics — what would we build?"

---

## 2. Architectural Principles

### 2.1 The Language Core Stays Small

Simulation, UI, databases, networking, media, and AI are **standard library
modules**, not grammar. There are no `entity`, `system`, `component`, `table`,
`http`, or `tensor` keywords. Everything lives behind `import OMNISYS.<module>`.

### 2.2 Do Not Wrap — Design Native

For each major ecosystem (SwiftUI, WPF, Qt, SQL, Vulkan, CUDA, Node, Flecs,
…), we study it and answer the §17.3 eleven questions — what problem it solves,
which concepts survived, which are historical accidents, which APIs are awkward
because of the host language, and which concepts become first-class Omni
concepts. We then design the module **from first principles for OmniScript**.
Not "OmniSwiftUI" — `OMNISYS.ui`.

### 2.3 Portable Core + Powerful Escapes

Every module exposes a portable semantic API. Backend-specific capability
(CUDA, Metal, Vulkan, DirectX, WebGPU) remains reachable through the
capability/effect system, which makes platform differences **explicit at
compile time**, never guessed at runtime. See
[`../omnisys/README.md`](../omnisys/README.md) and
[`escape-hatch.md`](17-escape-hatch.md).

### 2.4 One Effect Model

There is exactly one capability vocabulary (network, filesystem, database,
camera, microphone, GPU, process, secrets, screen, input, audio, …), enforced
by the compiler front-end. No module has its own permission system. See
[`02-capability-matrix.md`](02-capability-matrix.md).

### 2.5 AI-Native by Design

Every OMNISYS API is designed for both humans AND AI coding agents: typed,
structurally inspectable, deterministic where appropriate, machine-readable,
easy to test and diagnose, with required capabilities, I/O types, side
effects, dependencies, lifecycle, and errors all explicit.

---

## 3. Compilation Pipeline

OMNISYS preserves the existing OmniScript compilation pipeline unchanged:

```
OmniScript source (with import OMNISYS[.module])
      ↓
   Frontend   (parse, name resolution, type check, effect check, import check)
      ↓
   OMNI MIR   (typed, effect-aware, versioned, serializable)
      ↓
 backend/runtime
      ↓
 native / JS / WASM / future targets
```

`import` statements are parsed into the AST, carried into the MIR, and resolved
by the compiler against the module registry (`omni_compiler/omnisys_registry.py`).
The chosen JS implementation files are inlined by the JS emitter in dependency
order; capability effects are enforced by the checker; native targets reject
OMNISYS imports at build time with `E-BACKEND-001` until those lanes land.

## 4. Module Tree (summary)

The canonical 17-module tree plus the implicit `core` root export:

| Layer | Modules |
|-------|---------|
| Phase 1 — Foundations | `core` (subsumes `collections`, `serde`, `error`), `async`, `fs`, `test` |
| Phase 2 — App Foundations | `ui`, `db`, `net`, `http` |
| Phase 3 — Graphics/GPU/Sim | `graphics`, `gpu`, `scene`, `sim` |
| Phase 4 — Media/Platform | `audio`, `video`, `platform` |
| Phase 5 — Security | `crypto`, `auth` |
| Phase 6 — AI/Advanced | `ai`, `pkg`, advanced `async` |

Full tree, dependency map, and per-module READMEs:
[`../omnisys/README.md`](../omnisys/README.md).
Detailed module-by-module breakdown: [`01-module-tree.md`](01-module-tree.md).

## 5. The Registry

The compiler-facing source of truth for OMNISYS is
`omni_compiler/omnisys_registry.py`. It records, per module:

- the JS implementation file that the emitter inlines,
- the `js_deps` dependency order for inlining,
- each function's **type signature** and **declared capability effects**.

The registry is what makes `import OMNISYS` checkable: unknown modules are
`E-IMPORT-002`, effect violations are `E-EFFECT-003`, and the per-backend gate
is `E-BACKEND-001`. See [`14-import-behavior.md`](14-import-behavior.md).

## 6. Backends

OMNISYS is not a frontend for one existing engine. The portable semantic model
is spec-defined; concrete runtimes are implementations behind adapters. The
capability matrix per backend is fixed at build time (`omni build --target …`).
See [`03-backend-matrix.md`](03-backend-matrix.md).

## 7. The Golden Rule

> If we had all accumulated engineering knowledge today, and were designing a
> unified platform for OmniScript, AI agents, portability, safety, performance,
> and ergonomics — what would we build?

That is OMNISYS.

---

*Source of truth: [`../../OMNI_SPEC.md`](../../OMNI_SPEC.md) §17.*