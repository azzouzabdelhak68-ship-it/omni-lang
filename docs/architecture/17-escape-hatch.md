# OMNISYS Escape-Hatch / Native Interop Model

**Deliverable §14R.** Portable core plus powerful, explicit escapes.

---

## 1. The Principle (spec §17.4)

`OMNISYS.gpu` provides portable GPU concepts. But backend-specific capabilities
(CUDA, Metal, Vulkan, DirectX, WebGPU) MUST remain accessible. The capability
system makes platform differences **explicit**.

Portable default. Named escapes. Never the other way around.

## 2. When an Escape Is Needed

An escape exists when the portable semantic core cannot express the operation
without losing what the backend uniquely offers: a CUDA kernel, a Vulkan
pipeline, a hardware codec, a platform notification, an OS process.

The design questions (spec §17.3) are answered per ecosystem *before* the
escape is exposed:

- What belongs in the portable semantic layer?
- What must remain backend-specific?
- What is the escape hatch?

## 3. Escape Mechanisms

| Mechanism | What it exposes | Capability |
|-----------|-----------------|------------|
| **Backend module** | `platform` native APIs (OS, device, process) | `uses platform`, `uses process` |
| **GPU escape** | raw CUDA/Metal/Vulkan/DirectX/WebGPU objects | `uses GPU` |
| **Native interop** | FFI across the language boundary with type + safety checks | declared per operation |
| **Per-backend functions** | a backend-only API surface, unreachable elsewhere at compile time | capability-gated |

## 4. Safety & Boundaries

- **Types preserved across the boundary**: the FFI/escape never downgrades a
  typed value to an opaque blob silently.
- **Effects declared**: every escape names its capability; a `pure` function
  cannot escape.
- **Compile-time gating**: `omni build --target js` on a program using a native
  escape fails with a friendly diagnostic (e.g. `E-BACKEND-001` for OMNISYS on
  native targets; per-capability checks for escapes).

## 5. The Escape Hatch Rule

> Escapes are named, documented, capability-declared, and **never the default**.
> If a program compiles unchanged on two backends, it uses only the portable
> core. The moment it touches an escape, the capability system says so.

## 6. Examples

- CUDA kernel launch: portable `compute(...)` on WebGPU; `launch(cuda_kernel, …)`
  via the `gpu` escape on native.
- Filesystem watch: portable `watch(dir)` everywhere; native event loop only
  where the backend provides it.
- Process spawn: `platform` capability exists only on native (spec §13.3).

*See also:* [`03-backend-matrix.md`](03-backend-matrix.md),
[`02-capability-matrix.md`](02-capability-matrix.md).