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