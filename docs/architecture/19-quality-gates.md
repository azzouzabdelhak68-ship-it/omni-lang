# OMNISYS Testing & Quality Gates

**Deliverable §14T.** The mandatory gates every OMNISYS package and phase must
pass.

---

## 1. Per-Version Gates (TODO.md)

| Version | Coverage | Mutation | Mypy | Ruff |
|---------|----------|----------|------|------|
| v1.0 | ≥90% branch | ≥80% (Phase 4+) | `--strict` | clean |
| v2–v5 | ≥95% branch | ≥90% | `--strict` | clean |
| **v6** | **≥95% branch** | **≥90%** | **`--strict`** | **clean** |

v6 special gates: **monorepo packages**, **capability matrix**, **research
gate**, **doc verification**.

## 2. Per-Package Test Suite

Every package (`packages/omnisys-*`) ships:

- **Unit tests** — each function in the registry contract.
- **Property-based tests** — hypothesis for parser round-trips, type
  soundness, and pure-function invariants.
- **Conformance tests** — the registry contract against the implementation;
  cross-backend where the module touches backends.
- **Mutation tests** — mutmut score ≥ 90% on the package.

## 3. Tooling Gates

| Gate | Tool / Threshold |
|------|------------------|
| Type checking | `mypy --strict --no-implicit-optional`, zero errors |
| Linting | `ruff --select=ALL`, zero warnings; `ruff format` clean |
| Cyclomatic complexity | `radon cc --min B` — no function > 15, file avg < 10 |
| Security scan | `bandit -r omni_compiler` — zero HIGH/MEDIUM |
| Coverage | `pytest --cov=… --cov-branch --cov-fail-under=95` (v6) |

## 4. Correctness & Property Gates

- **Parser round-trip**: every valid `.omni` file parsed → MIR → emitted JS →
  re-lexed preserves semantics (hypothesis).
- **Effect soundness**: no `pure` function transitively calls an effectful one.
- **Deterministic batching**: JS emitter batches DOM updates once per
  top-level block (snapshot test).
- **Import contract** (`tests/test_imports.py`): registry count matches the
  spec, every module has a JS file, `js_deps` are known modules, resolution
  rules, diagnostics (`E-IMPORT-001/002/003`, `E-EFFECT-001/003`,
  `E-BACKEND-001`), MIR round-trip, emitter inlining.

## 5. Documentation Gates

`scripts/verify-docs.py` (CI: `.github/workflows/docs.yml`):

- no broken internal links,
- no orphans (every `.md` under `docs/` referenced by `INDEX.md`),
- all 18 modules have READMEs with the six-field header set,
- status ∈ {stable, experimental, planned},
- `CAPABILITY_MATRIX.md` in sync.

Plus `gen-index.py --check` and `gen-capability-matrix.py --check`.

## 6. Research Gate (spec §17.8)

Every module needs a research document before implementation, covering:
capabilities and architectural patterns of the studied ecosystems, strengths/
weaknesses, performance, ergonomics, type-system interaction, portability,
lifecycle/error/concurrency models, AI usability, interop requirements.

## 7. No Manual Override

No phase checkbox in `TODO.md` is ticked unless every gate passes (spec §20.5).
The CI pipeline enforces the gates on every push.

*See also:* [`16-conformance.md`](16-conformance.md),
[`18-roadmap.md`](18-roadmap.md).