# OMNISYS Performance Model

**Deliverable §14P.** The cost model that governs OMNISYS — bundle, startup,
build, and runtime.

---

## 1. Principles

- **Portable core is the default; escapes are opt-in.** The semantic layers
  (`ui`, `graphics`, `db`, `sim`, …) cost what the backend actually needs.
- **Lazy, dependency-gated loading.** The umbrella import never compiles the
  whole platform (spec §17.2).
- **Determinism over cleverness.** Fixed order, no hidden threads, predictable
  cost per operation.

## 2. Bundle / Startup / Build

| Concern | Rule |
|---------|------|
| **Binary size** | Emitter inlines only imported modules, in dependency order, deduplicated. Unused subsystems add zero bytes. |
| **Startup time** | No forced initialization of unimported modules. |
| **Build cost** | Compiler resolves imports against the registry once, at front-end time; no re-analysis per backend. |

## 3. Per-Backend Budgets (spec §20.4)

| Metric | Threshold |
|--------|-----------|
| `omni check` latency (100-line file) | < 200ms (M1 / Ryzen 5) |
| `omni run` cold startup | < 500ms |
| Emitted JS bundle (gzipped) | < 50 KB |

These are enforced by `scripts/check_performance.py` and
`scripts/check_bundle_size.py`.

## 4. Runtime Cost Model

- **UI**: one batched render per top-level block — no per-assignment flashes
  (spec §9.4a). Re-render cost ∝ changed slots, not whole-tree diff.
- **DB**: prepared statements + pooling; the semantic layer never string-builds
  SQL per call.
- **Sim**: data-oriented layouts (SoA) as the first-class model; parallelism
  only where the model proves no conflict (spec §13.5).
- **GPU**: portable core issues coarse ops; escapes expose fine control when
  the portable surface is not enough.

## 5. Latency & Jitter

- Async primitives are cooperative: no busy-wait, no hidden threads.
- `sim` scheduling is deterministic — same tick count, same state, stable
  frame pacing (per fixed backend).

## 6. Measuring

Per-package benchmarks ship with each module's `tests/`; the v6 quality gates
add branch coverage ≥ 95%, mutation ≥ 90%, and the perf/bundle scripts to the
CI pipeline. See [`19-quality-gates.md`](19-quality-gates.md).