# OMNISYS Graphics / GPU / Scene Architecture

**Deliverable §14H.** Rendering, GPU compute, and 3D scene graph — separated,
portable, with explicit backend escapes.

Module READMEs: [`../omnisys/graphics/README.md`](../omnisys/graphics/README.md),
[`../omnisys/gpu/README.md`](../omnisys/gpu/README.md),
[`../omnisys/scene/README.md`](../omnisys/scene/README.md).

---

## 1. The Separation (spec §17.6.3)

Study CUDA, Vulkan, DirectX, Metal, WebGPU, modern renderers, ECS, and
physics — then separate five concerns:

1. **Semantic rendering model** — what a scene *is* (portable).
2. **GPU abstraction** — device, buffers, compute (portable core).
3. **Renderer** — how the scene is drawn (per backend).
4. **Platform backend** — Vulkan / Metal / DX / WebGPU (escapes).
5. **Simulation / ECS** — see [`10-sim.md`](10-sim.md).

OMNISYS is **never** a frontend for one existing engine.

## 2. OMNISYS.graphics — Portable Rendering Abstraction

A semantic model over platform backends:

```omni
import OMNISYS.graphics

canvas(800, 600)                  # 2D drawing surface
rect(canvas, 10, 10, 100, 50, "#e11d48")
render(canvas)                    # → list of draw commands / backend ops
```

- `canvas`, `clear`, `line`, `rect`, `circle`, `polygon`, `text`, `fill`,
  `stroke` — pure, backend-agnostic.
- `render`/`to_json` — serializable output for any backend.

## 3. OMNISYS.gpu — GPU Compute

Portable GPU concepts with explicit backend-specific escapes:

```omni
import OMNISYS.gpu

a = buffer([1, 2, 3])
b = buffer([4, 5, 6])
add(a, b)          # element-wise
matmul(a, b)       # matrix multiply
parallel(work, [1, 2, 3, 4])
```

- `buffer`, `compute`, `parallel`, `add`, `scale`, `dot`, `matmul`,
  `normalize`, `device_info`.
- Memory model (unified vs. explicit) and kernel pipeline are design questions
  the portable core must answer before escape hatches leak upward.

## 4. OMNISYS.scene — 3D Scene Graph

A semantic 3D scene graph (spec §17.6.3, §10 for the language-level `scene:`
block):

```omni
import OMNISYS.scene

s    = new_scene()
node(s, "planet")
mesh(s, "sphere", "#ffffff")
camera(s, "main")
transform(s, "planet", {pos: "0,2,0", scale: "1.5"})
snapshot(s)
```

- `new_scene`, `node`, `mesh`, `camera`, `light`, `add`, `transform`,
  `remove`, `snapshot`, `update`, `to_json`.
- The scene graph is serializable and inspectable — the same model feeds
  native renderers, WebGPU, and the `scene:` language block.

## 5. Capabilities

- `graphics` → `uses GPU`
- `gpu` → `uses GPU` (compute ops additionally declare it on each function)
- `scene` → `uses GPU` (via the graphics backend)

The effect system keeps every backend difference explicit (spec §17.4).

## 6. Open Design Questions (carried from READMEs)

- Semantic rendering model scope
- Memory model (unified vs. explicit) for GPU compute
- Scene serialization/interchange format
- Editor tooling integration