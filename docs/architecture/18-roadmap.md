# OMNISYS Development Roadmap

**Deliverable §14S.** The phased plan for building OMNISYS, gated by quality
gates and sub-agent delegation.

---

## 1. Milestones

| Milestone | Units | Contents |
|-----------|-------|----------|
| **A** | 1 | Master Architecture docs (§14A–14U) — this directory |
| **B** | 7 parallel | Phase 1 Foundations: `core` (incl. collections/serde/error), `async`, `fs`, `test` |
| **C** | 4 parallel | Phase 2 App Foundations: `ui`, `db`, `net`, `http` |
| **D** | 4 parallel | Phase 3 Graphics/GPU/Sim: `graphics`, `gpu`, `scene`, `sim` |
| **E** | 4 parallel | Phase 4 Media/Platform: `audio`, `video`, `platform` |
| **F** | 7 parallel | Phase 5/6 Security + AI: `crypto`, `auth`, `observability`, `tool`, `ai`, `pkg`, advanced `async` |
| **G** | 1 | Ledger update in `TODO.md`, full gate verification |

## 2. Sequencing Rules (spec §17.7)

- Phases are dependency-ordered: Foundations → App Foundations →
  Graphics/GPU/Sim → Media/Platform → Security → AI/Advanced.
- Units **within** a phase run in parallel (independent packages).
- Milestone A precedes implementation; every module needs its research doc
  (spec §17.8) before or alongside implementation.

## 3. Per-Package Delivery

Each package (e.g. `omnisys-core`) delivers:

1. **Research doc** — capabilities, patterns, strengths/weaknesses,
   performance, ergonomics, type interaction, portability, lifecycle/error/
   concurrency models, AI usability, interop (spec §17.8).
2. **Implementation** — `src/` in the monorepo package, mirroring the JS
   runtime API in `omnisys/*.js` and the registry contract.
3. **Tests** — unit + property-based + conformance.
4. **Gates** — branch coverage ≥ 95%, mutation ≥ 90%, mypy `--strict`, ruff
   clean, docs verification green.

## 4. Sub-Agent Delegation

Per the TODO.md protocol: any phase marked `[SUB-AGENT]` MUST be delegated to
sub-agents running in parallel. The main agent verifies every sub-agent's
quality gates before check-off. Units are self-contained so a single sub-agent
can deliver one package independently.

## 5. Parallelism & Dependencies

- Phase 1 packages: `async`, `fs`, `test` depend on `core`; `test` also on
  `collections` → `core` ships first (or as the umbrella root).
- Phase 2: `http` depends on `net`; `ui`/`db` are independent.
- Phase 3: `gpu` depends on `graphics`; `scene` on `graphics`; `sim` is
  independent.
- Phase 4: `video` depends on `audio`; both on `platform` device access.
- Phase 5: `auth` depends on `crypto` (+ `db`); `observability`/`tool`
  independent.
- Phase 6: `pkg` depends on `core`/`serde`/`fs`; `ai` on `core` (+ `gpu`).

## 6. Completion Criterion

A phase is complete when every package passes its gates AND the docs
verification (`verify-docs.py`, generators) is green AND `TODO.md` is updated
with an honest status note. See [`19-quality-gates.md`](19-quality-gates.md).

## 7. Relationship to v7

The v7 ecosystem benchmark (31 projects across 7 phases) measures AI ×
OmniScript friction. `STATUS: BLOCKED` projects unlock as the corresponding v6
modules ship — the roadmap above is the unlock order.