# Architecture

High-level overview of the OmniScript compilation pipeline and the OMNISYS
platform architecture.

## Compilation Pipeline

```
OmniScript source
      ↓
   Frontend
      ↓
   OMNI MIR
      ↓
 backend/runtime
      ↓
 native / JS / WASM / future targets
```

## OMNISYS

The language core remains small; capabilities live in OMNISYS modules.
See [`../omnisys/README.md`](../omnisys/README.md) for the module tree and
dependency map.

## OMNISYS Master Architecture Documents (§14A–14U)

The authoritative OMNISYS design docs. Each maps to a §17.9 deliverable.

| Doc | Deliverable |
|-----|-------------|
| [`00-master-architecture.md`](00-master-architecture.md) | §14A — OMNISYS Master Architecture |
| [`01-module-tree.md`](01-module-tree.md) | §14B — Module Tree |
| [`02-capability-matrix.md`](02-capability-matrix.md) | §14C — Capability Matrix |
| [`03-backend-matrix.md`](03-backend-matrix.md) | §14D — Backend Matrix |
| [`04-api-design-principles.md`](04-api-design-principles.md) | §14E — API Design Principles |
| [`05-ui.md`](05-ui.md) | §14F — UI Architecture |
| [`06-database.md`](06-database.md) | §14G — Database Architecture |
| [`07-graphics-gpu-scene.md`](07-graphics-gpu-scene.md) | §14H — Graphics/GPU Architecture |
| [`08-networking.md`](08-networking.md) | §14I — Networking Architecture |
| [`09-media-platform.md`](09-media-platform.md) | §14J — Media Architecture |
| [`10-sim.md`](10-sim.md) | §14K — Simulation/ECS Architecture |
| [`11-security.md`](11-security.md) | §14L — Security Architecture |
| [`12-ai-tooling.md`](12-ai-tooling.md) | §14M — AI-Native Tooling Architecture |
| [`13-package-system.md`](13-package-system.md) | §14N — Package/Module System |
| [`14-import-behavior.md`](14-import-behavior.md) | §14O — `import OMNISYS` Behavior |
| [`15-performance.md`](15-performance.md) | §14P — Performance Model |
| [`16-conformance.md`](16-conformance.md) | §14Q — Cross-Backend Conformance Model |
| [`17-escape-hatch.md`](17-escape-hatch.md) | §14R — Escape-Hatch / Native Interop Model |
| [`18-roadmap.md`](18-roadmap.md) | §14S — Development Roadmap |
| [`19-quality-gates.md`](19-quality-gates.md) | §14T — Testing/Quality Gates |
| [`20-example-applications.md`](20-example-applications.md) | §14U — Example Applications |