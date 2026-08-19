# OMNISYS Backend Matrix

**Deliverable §14D.** Which OMNISYS runtime exists on which backend, and which
capabilities each backend provides.

A target backend is fixed at build time (`omni build --target <name>`), and
capability provision is checked against this matrix at compile time
(OMNI_SPEC.md §13.3). This is never guessed at runtime.

---

## 1. Backend Capability Matrix (spec §13.3)

| Capability | Native | WASM/WASI | JS | Python |
|-----------|:------:|:---------:|:--:|:------:|
| `network` | yes | yes (WASI) | yes | yes |
| `filesystem` | yes | WASI yes / browser no | yes (Node) | yes |
| `database` | yes | WASI yes / browser no | yes | yes |
| `camera` | yes | no | no | browser only |
| `microphone` | yes | no | yes (browser) | browser only |
| `GPU` | yes | yes (WebGPU) | yes (WebGPU) | no |
| `process` | yes | no | no | no |
| `secrets` | yes | WASI yes / browser no | yes | yes |

## 2. OMNISYS Runtime Availability

The OMNISYS runtime is a set of JS implementation files under `omnisys/*.js`
(`omnisys/core.js`, `omnisys/fs.js`, …), inlined by the JS emitter in
dependency order. Their availability per target:

| Target | OMNISYS status |
|--------|----------------|
| **JS** (`--target js`) | ✅ Shipping — emitter inlines the runtime, gated per module/function |
| **C / Rust / WASM** | ⛔ `E-BACKEND-001` — rejected until the runtime lands on those lanes |
| **Python** | 📋 spec-only — Python lane not yet implemented (spec §13.4) |

`omni check` still validates an OMNISYS program on any target; only `build`
enforces the backend gate.

## 3. Design Rule: Portable Core + Escapes

- The **portable core** of each module (e.g. `OMNISYS.gpu` buffer/compute
  primitives) is backend-agnostic.
- Backend-specific capabilities (CUDA, Metal, Vulkan, DirectX, WebGPU) remain
  reachable and are declared through the capability system, so portability
  decisions are explicit at compile time.
- The browser is a **feature**, not the definition: the same module compiles
  for Node/Bun/Deno (web + server), native, and WASI (server/edge).

## 4. Conformance

Behavior must be identical per backend; determinism is guaranteed **per fixed
backend**, not bit-identical across backends (float rounding may differ).
See [`16-conformance.md`](16-conformance.md).

*See also:* [`02-capability-matrix.md`](02-capability-matrix.md),
[`17-escape-hatch.md`](17-escape-hatch.md).