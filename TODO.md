
# OmniScript v1.0 → v7 — Master Execution Ledger & Session Handoff

> **Session Continuity Protocol**: Every agent starting a new session MUST read this file first. When finishing a session, the agent MUST update the phase checkboxes, write a brief summary in the "Last Session Status Note", and ensure all Quality Gates pass.

## 🛑 The Anti-Shortcut & Zero-Mock Constitution (Enforced Rules)
> **MANDATORY**: All checkboxes below have been reset to `[ ]` to enforce strict re-verification. No feature or module may be marked complete without meeting production-grade reality checks.
1. **Zero-Mock Infrastructure Rule**: Any OMNISYS module claiming infrastructure (`db`, `net`, `http`, `crypto`) is banned from using in-memory Python dicts or `inproc://` mocks as its production implementation. Must use real SQLite (`better-sqlite3` / C bindings) and real TCP/TLS sockets.
2. **Cross-Backend Conformance**: Features must pass black-box integration tests on JS, Native (C/Rust), and WASM.
3. **Registry Consistency**: `omnisys_registry.py` and runtime implementations (`omnisys/*.js`, C/Rust adapters) must have automated signature validation to prevent silent drift.
4. **No Opaque Cast Loopholes**: Deserialized data (`serde.json_decode`) must map cleanly into typed structs without manual `unknown` casting workarounds.
5. **Real Source Maps & Debugging**: Emitters must generate source maps (`.map`, DWARF) mapping compiled artifacts back to `.omni` lines.

### Constitution Compliance Audit (code-verified)
> Every rule above was audited against the actual codebase. Findings below are binding: any phase whose scope touches a FAILED rule may not be checked off until the violation is fixed.

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Zero-Mock Infrastructure | ❌ **FAILED** | `omnisys/net.js` — no TCP/TLS; `net.request` dispatches to an in-process handler. `omnisys/http.js` — production path is the banned `inproc://` scheme (lines 22–64); rejects without a registered transport. `omnisys/db.js` — uses sql.js (WASM SQLite), not the mandated `better-sqlite3`/C bindings. |
| 2 | Cross-Backend Conformance | ⚠️ PARTIAL | `tests/conformance/test_cross_backend.py` proves one MIR emits to JS/C/Rust/WASM, but asserts only non-empty output — no black-box execution comparing runtime behavior across backends. |
| 3 | Registry Consistency | ⚠️ PARTIAL | Only one signature contract test exists (`packages/omnisys-test/tests/test_conformance.py:26`). No automated drift validation across all 24 modules vs their `omnisys/*.js` runtimes. |
| 4 | No Opaque Cast Loopholes | ❌ **FAILED** | Registry types `serde.json_decode` as `fn(Text) -> any` (`omnisys_registry.py:163`); checker infers `unknown` (`checker.py:1100`) — the banned manual-cast workaround. |
| 5 | Real Source Maps & Debugging | ❌ **FAILED** | No source-map generation anywhere in `omni_compiler/` (no `.map`, sourceMappingURL, or DWARF in any emitter). |

**Phases invalidated by this audit** (claims of completion withdrawn):
- **v6 Phase 8** (Platform Parity & Backend Conformance) — Rule 2 partial: no cross-backend behavioral conformance.
- **v6 Phase 10** (OMNISYS API & Runtime Completion) — Rule 1 failed: `net`/`http` are in-process mocks; Rule 4 failed: `serde.json_decode` returns `any`.
- Any future phase claiming emitter completion — Rule 5 failed: no source maps.

---

## Current Phase
- **⚠️ Constitution Compliance Audit FAILED Rules 1, 4, 5** (see audit table above): `net`/`http` are in-process mocks, `serde.json_decode` returns `any`, and no emitter generates source maps. Accordingly the **v6 Phase 8 and v6 Phase 10 completion claims are WITHDRAWN**, and the prior **v7 Phase 5 COMPLETE claim is contested** (re-run found 26 failing tests: 5.4 runtime bug + 5.5 checker regression on optional `Text?` params in `_param_types_of`, checker.py:185). Still verified: core gates green (pytest 622 passed / 3 skipped, ruff/mypy/bandit clean) and v7 Phase 6 (55/55). Next: fix Rule 1 (`net`/`http` real transports), Rule 4 (typed decode), Rule 5 (source maps), the `_param_types_of` regression, then rerun gates before any checkoff.
- Previous status: v6 Phases 6–7 and 9 verified implemented (commit `ed41978`; pytest/ruff/mypy/bandit green); v6 Phase 6 runtime bug fix (JS map literals emit plain objects so `m["k"]` reads work); v7 Phase 6 COMPLETE (AI/Advanced, all 3 projects, 55/55 tests).

## Sub-Agent Delegation Protocol

> **MANDATORY**: For any phase with `[SUB-AGENT]` marker, the main agent MUST spawn a sub-agent to execute the task. Sub-agents run in parallel where phases are independent. The main agent MUST wait for all sub-agents to complete and verify their quality gates before proceeding.

**Delegation Rules:**
1. Phases within same version can run in parallel if their dependencies are met
2. v2.1 → v2.2, v2.2 → v2.3 (sequential within v2)
3. v2 complete → v3.1, v3.2, v3.3 can run in parallel (v3.4 depends on all)
3. v3 complete → v4 (SMT + AI tooling can parallelize)
4. v4 complete → v5
5. Sub-agents MUST run quality gates locally and report pass/fail
6. Main agent verifies all sub-agent results before phase checkoff

---

## Last Session Status Note
- **Last Action (this session)**: Reconciled **v6 Phase 6: Language Completion** (all 14 items), completed **v7 Phase 5: Security/Tooling** (all 5 projects), and completed **v7 Phase 6: AI/Advanced** (all 3 projects).
  1. **v6 Phase 6 verified already implemented** in commit `ed41978` "v6 Phase 6: Language Completion" (HEAD). `tests/test_phase6.py` = **136/136 pass**; full suite **622 passed, 3 skipped**. Checkboxes were never reconciled; ledger now corrected.
  2. **End-to-end probe** (real `.omni` → `omni check` → `omni build` → Node DOM-stub run) confirmed: `while`, `x[i]` indexing, `%` modulo, map literal + `m["k"]` read, try/catch emission, `global`, `OMNISYS.core.split`/`length`, call-site arity/type diagnostics with real line/col.
  3. **Fixed a real runtime bug found during probing**: JS emitter emitted map literals as `new Map([[k, v], ...])`, but the runtime (`omnisys/collections.js`, "Map (plain object)") and `m["k"]` index reads expect plain objects — so `m["k"]` returned `undefined` at runtime. `emitter.py` `op == 'map'` now emits a plain JS object `{"k": v}`; updated `test_js_emitter_map`. Map index **write** (`m["k"] = v`) remains unsupported (E-SYNTAX-001) — noted, not in Phase 6 scope.
  4. **v7 Phase 5 run** — all 5 projects under `OMNISCRIPT_AI_BENCHMARK/PHASE_5_SECURITY_TOOLING/` complete (`RUN_001_DEEPSEEK_V4_FLASH_FREE` for 5.1–5.4, `RUN_001_CLAUDE_3_5` for 5.5). 81 tests for 5.1–5.4 (18/27/19/17) + all source `omni check`/`build`/`verify` green. TASK.md `BLOCKED` statuses were stale. See the Phase 5 status note below for findings.
  5. **v7 Phase 6 run** — all 3 projects under `OMNISCRIPT_AI_BENCHMARK/PHASE_6_AI_ADVANCED/` complete (`RUN_001_DEEPSEEK_V4_FLASH_FREE` for 6.1–6.3). 55 tests (18/19/18) + all source `omni check`/`build`/`verify`/`run` green. Fixed source friction (ternary, reserved `result`, struct trailing comma) and **3 real OMNISYS.pkg runtime bugs in `omnisys/pkg.js`** (registry_add signature drift, async compute_checksum, exact-key resolve). See the Phase 6 status note below for findings.
- **Verification**: `pytest tests/` → **622 passed, 3 skipped** (23.9s). Ruff clean. MyPy `--strict` clean (15 files). Benchmark pytest suites green (Phase 5: 81, Phase 6: 55). All quality gates pass.
- **Previous**: Completed **v6 Phase 10: OMNISYS API & Runtime Completion** (all 9 items), **v6 Phase 9** (all 3), **v6 Phase 8** (all 5), **v6 Phase 7** (all 6).
- **Next**: v7 Phase 7, or any remaining [HARD] future roadmap item (Phase 0/1 runs and v1.0 gates already pass; v3 native gates deferred).

---

## Quality Gates (Mandatory for Every Phase)

| Version | Coverage | Mutation | Mypy | Ruff | Special Gates |
|---------|----------|----------|------|------|---------------|
| **v1.0** | ≥90% branch | ≥80% (Phase 4+) | `--strict` | clean | Parser round-trip, effect soundness, live-link batching |
| **v2** | ≥95% branch | ≥90% | `--strict` | clean | Loop property tests, 3D snapshot tests, custom type checking |
| **v3** | ≥95% branch | ≥90% | `--strict` | clean | Native/WASM perf budgets, Flecs/Bevy adapter conformance |
| **v4** | ≥95% branch | ≥90% | `--strict` | clean | SMT verification gate, AI tooling adversarial tests |
| **v5** | ≥95% branch | ≥90% | `--strict` | clean | Self-hosting compiler compiles itself, visual editor E2E, chaos testing |
| **v6** | ≥95% branch | ≥90% | `--strict` | clean | Monorepo packages, capability matrix, research gate, doc verification |
| **v7** | N/A (Benchmark) | N/A | N/A | clean | 31 benchmark projects, capability gating, run isolation, dual output |

---

## Sub-Agent Delegation Protocol

> **MANDATORY**: For any phase with `[SUB-AGENT]` marker, the main agent MUST spawn a sub-agent to execute the task. Sub-agents run in parallel where phases are independent.

**Delegation Rules:**
1. Within same version: independent sub-phases run in parallel (v2.1→v2.2→v2.3 sequential; v3.1/v3.2/v3.3 parallel; v3.4 after all)
2. v2 complete → v3.1, v3.2, v3.3 parallel → v3.4
3. v3 complete → v4.1 + v4.2 parallel
4. v4 complete → v5.1, v5.2, v5.3 parallel
5. Sub-agents MUST run quality gates locally and report pass/fail
6. Main agent verifies all sub-agent results before phase checkoff

---

## Conformance Suite Progress
- [x] Valid fixtures: 01_basic, 02_function_with_effects, 03_loops_and_lists
- [x] Invalid fixtures: 01_missing_network, 02_pure_with_effects
- [ ] Expand to 10+ valid fixtures covering all language features
- [ ] Add invalid fixtures for every error code in spec

---

## v6 — OMNISYS: The Omni-Native Platform (Post-v5)

### v6 — OMNISYS Master Architecture
- [x] **OMNISYS Master Architecture** (§14A) — `docs/architecture/00-master-architecture.md`
- [x] **Module Tree** (§14B) — `docs/architecture/01-module-tree.md`
- [x] **Capability Matrix** (§14C) — `docs/architecture/02-capability-matrix.md`
- [x] **Backend Matrix** (§14D) — `docs/architecture/03-backend-matrix.md`
- [x] **API Design Principles** (§14E) — `docs/architecture/04-api-design-principles.md`
- [x] **UI Architecture** (§14F) — `docs/architecture/05-ui.md`
- [x] **Database Architecture** (§14G) — `docs/architecture/06-database.md`
- [x] **Graphics/GPU Architecture** (§14H) — `docs/architecture/07-graphics-gpu-scene.md`
- [x] **Networking Architecture** (§14I) — `docs/architecture/08-networking.md`
- [x] **Media Architecture** (§14J) — `docs/architecture/09-media-platform.md`
- [x] **Simulation/ECS Architecture** (§14K) — `docs/architecture/10-sim.md`
- [x] **Security Architecture** (§14L) — `docs/architecture/11-security.md`
- [x] **AI-Native Tooling Architecture** (§14M) — `docs/architecture/12-ai-tooling.md`
- [x] **Package/Module System** (§14N) — `docs/architecture/13-package-system.md`
- [x] `import OMNISYS` Behavior (§14O) — `docs/architecture/14-import-behavior.md`
- [x] **Performance Model** (§14P) — `docs/architecture/15-performance.md`
- [x] **Cross-Backend Conformance Model** (§14Q) — `docs/architecture/16-conformance.md`
- [x] **Escape-Hatch / Native Interop Model** (§14R) — `docs/architecture/17-escape-hatch.md`
- [x] **Development Roadmap** (§14S) — `docs/architecture/18-roadmap.md`
- [x] **Testing/Quality Gates** (§14T) — `docs/architecture/19-quality-gates.md`
- [x] **Example Applications** (§14U) — `docs/architecture/20-example-applications.md`
*Status Note*: Milestone A complete. 21 design docs under `docs/architecture/` (one per §14A–14U), grounded in the registry contract (`omnisys_registry.py`), the JS runtime (`omnisys/*.js`), and the module READMEs. `docs/architecture/README.md` updated as directory index; `scripts/gen-index.py` extended to list architecture docs under the Architecture section (orphan rule satisfied). Gates: `verify-docs.py` ✅, `gen-index.py --check` ✅, `gen-capability-matrix.py --check` ✅. Next: v6 Phase 1 Foundations (7 parallel packages).

### v6.0 — Documentation Layer
- [x] **Spec repair**: Deduplicated §17.1 module tree in `OMNI_SPEC.md` (17 modules, `scene` at line 17, `core` implicit root export = 18 documented)
- [x] **Spec repair**: Fixed §17.7 duplicate "4." phase numbering → 1–6
- [x] **`docs/DOC_CONVENTIONS.md`**: Six-field header set (Purpose, Public API surface, Dependencies, Effects/capabilities used, Status, Open Questions) + link/status/orphan rules
- [x] **Scaffold**: `docs/language/`, `docs/architecture/`, `docs/decisions/` (ADR numbering convention only), `docs/omnisys/` parent + dependency map
- [x] **18 module READMEs**: `docs/omnisys/<module>/README.md` with `Status: planned` + `<!-- CAPABILITIES -->` tags (core subsumes collections/serde/error)
- [x] **Scripts**: `scripts/gen-index.py`, `scripts/gen-capability-matrix.py` (with `--check`), `scripts/verify-docs.py` (6 rules, no ADR rule yet)
- [x] **CI**: `.github/workflows/docs.yml` (verify-docs + both `--check` generators)
- [x] **Gate**: `verify-docs.py`, `gen-index.py --check`, `gen-capability-matrix.py --check` — all pass

## v6 Extra: Future Roadmap (Pillars 1–6)

> **Why this roadmap?** Phases 6–11 make the language *correct, expressive, and honest*. These six pillars turn the benchmarked prototype into a production-grade agentic platform. Grouped by difficulty: **[EASY]** items are independent, low-risk, and safe for parallel sub-agents; **[MEDIUM]** items need focused single-session work; **[HARD]** items require a stronger model or dedicated independent sessions (no parallel delegation).

### Pillar 1: AI-First & Agent Experience

**Easy (parallel sub-agents):**
- [x] **[EASY] Short-Form Agent Syntax (`#lang agent`)** — compact, token-efficient shorthand (symbols, implied returns) that expands to canonical `.omni`; LLM context savings + faster generation
- [x] **[EASY] Native formatter (`omni fmt`)** — canonical whitespace/layout so agent output is uniform and diffable

**Hard (strong model / independent sessions):**
- [ ] **[HARD] Bidirectional AST-to-Source Synthesizer API** — first-class compiler API that renders format-clean `.omni` from a JSON AST; syntax becomes a rendering, not storage
- [ ] **[HARD] Direct JSON-AST compilation** — `omni build/run` accept a `.json` AST input, bypass lexer/parser, still run checker + emit; agents program structurally
- [ ] **[HARD] Incremental / streaming LSP diagnostics** — mid-generation token-level analysis reports effect/type violations before the file is complete
- [ ] **[HARD] CLI sandbox (`omni run --sandbox`)** — mock/restrict filesystem + network under secure boundaries; agent-produced programs cannot damage the host

### Pillar 2: Checked Effects & Capability Soundness

**Easy (parallel sub-agents):**
- [x] **[EASY] Memory & allocation effects** — `allocates`, `mutates heap` effect tokens so WASM/embedded targets can statically bound memory
- [x] **[EASY] Value-parameterized effects** — `reads file("/etc/config.json")`, `uses network("api.com")` instead of blanket host-wide permissions

**Hard (strong model / independent sessions):**
- [x] **[HARD] Capability delegation / borrowing** — pass restricted capability tokens to callbacks for the duration of a call (Rust-lifetime style, for effects)
- [ ] **[HARD] Static analysis of escape hatches** — verify inline JS/raw C blocks cannot run blacklisted ops unless the wrapping block declares the capability; `pure` stays truthful

### Pillar 3: SMT Static Contract Verification (Z3)

**Easy (parallel sub-agents):**
- [x] **[EASY] Text/string solver integration** — model `Text` as SMT sequences in `smt.py`; prove sanitization and length-bound safety

**Hard (strong model / independent sessions):**
- [ ] **[HARD] Hybrid static-to-runtime verification** — unprovable contracts (`unsupported`/`failed`) auto-compile into runtime asserts; proved contracts compile away to zero cost
- [ ] **[HARD] Z3 Array Theory for lists** — model push/pop/index in `smt.py`; prove `list_get(list, 0)` safe under `length > 0`
- [ ] **[HARD] ADT / heap modeling** — model custom types and field access in `smt.py` so structs verify in contracts

### Pillar 4: Multi-Backend Conformance (The Frankenstein Iron Law)

**Easy (parallel sub-agents):**
- [x] **[EASY] Floating-point conformance** — unify division-by-zero, NaN, infinity, rounding across JS/C/Rust/SMT; multi-target results must not diverge

**Hard (strong model / independent sessions):**
- [ ] **[HARD] Unified memory management** — refcounting/region allocator for C/Rust targets to match JS GC semantics; identical memory safety
- [ ] **[HARD] Automated differential testing engine** — CI runner executes every `.omni` on all 5 backends with identical inputs and fails on any output/heap divergence

### Pillar 5: Real-World Runtime & Ecosystem

**Easy (parallel sub-agents):**
- [x] **[EASY] Event loop & timer API** — native grammar for ticks, intervals, async delays (beyond `when app starts`)
- [x] **[EASY] SQLite persistence** — real SQLite/SQLite-WASM storage replacing in-memory `db` tables

**Hard (strong model / independent sessions):**
- [ ] **[HARD] Real wire networking** — actual TCP/TLS sockets and HTTP server bindings on JS/C/Rust (beyond in-process mocks)
- [ ] **[HARD] Native graphics rendering** — GLFW/raylib (C) and Wgpu/Bevy (Rust) native window rendering for compiled binaries

### Pillar 6: Packaging & Distribution

**Easy (parallel sub-agents):**
- [x] **[EASY] Version constraints & lockfiles** — semver parsing, checksum lockfile, deterministic resolution metadata

**Hard (strong model / independent sessions):**
- [ ] **[HARD] Secure dependency resolver (`omni pkg`)** — Cargo/npm-style resolver with content-addressable local cache and integrity verification
- [ ] **[HARD] Self-hosted package registry** — federated registry server for publish, resolve, and audit

---

## OMNISYS Architecture Mandates
- [ ] **Single umbrella import**: `import OMNISYS` + modular `import OMNISYS.ui`
- [ ] **Capability integration**: Every module uses OmniScript effect system
- [ ] **Portable core + escapes**: Common API + backend-specific escapes
- [ ] **AI-native design**: All APIs inspectable, typed, machine-readable
- [ ] **Escape hatches**: Native interop for CUDA/Metal/Vulkan/DirectX/WebGPU
- [ ] **Package system**: Monorepo `packages/omnisys-*`, registry + git deps, `omni pkg` CLI
- [ ] **Testing**: Per-module comprehensive (unit, property, conformance, mutation ≥90%)
- [ ] **Sub-agent**: 1 per module, max parallel, quality gates mandatory
- [ ] **Research gate**: Research doc before implementation (parallel with impl)

---

## v7 — OMNISYS AI Ecosystem Benchmark & Language Feedback Loop

### The v7 Constitution
> **The benchmark must never teach the model the mechanism being measured. It may state the desired behavior, constraints, deliverables, and acceptance criteria, but the language construct, library API, compiler behavior, capability model, and implementation strategy must remain discoverable.**

### Mission & Core Philosophy
The v7 benchmark is an empirical feedback loop for continuous ecosystem evaluation. By forcing AI agents to solve real-world programming missions without pre-baked hints or pre-populated answers, we measure the interaction between AI agents and OmniScript/OMNISYS to convert observable friction into concrete language, API, compiler, diagnostic, and documentation improvements.

```text
                  v6 OMNISYS
                      │
                      ▼
              AI receives TASK.md
                      │
                      ▼
            AI investigates ecosystem
                      │
                      ▼
            BENCHMARK_REASONING.md
                      │
              ┌───────┴───────┐
              ▼               ▼
        Model succeeds    Model struggles
              │               │
              └───────┬───────┘
                      ▼
                RESULTS.md
                 /         \
                ▼           ▼
        MODEL_RESULT   ECOSYSTEM_RESULT
                            │
                            ▼
                 Language/API/compiler
                     improvements
                            │
                            ▼
                           v6
                            │
                            └──────► rerun
```

### Architecture & Rules
1. **Dual Output Mandate**: Every benchmark run produces:
   - `MODEL_RESULT`: Did the agent solve the task? How efficiently? What did it misunderstand?
   - `ECOSYSTEM_RESULT`: What did the agent teach us about OmniScript/OMNISYS? (API findings, Language findings, Compiler findings, Diagnostic findings, Documentation findings, Capability/Effect findings, Backend findings, Positive discoveries, Proposed changes).
2. **Observable Research Ledger (`BENCHMARK_REASONING.md`)**:
   - Maintained in real-time by the subject agent during execution.
   - Records explicit, observable investigation steps: questions investigated, files/docs/compiler code inspected, hypotheses formulated, probes/experiments run, compiler errors encountered, decisions made, failed approaches preserved, corrections, and verification results.
   - **Does NOT** request or rely on private chain-of-thought or internal monologue.
3. **Capability Gating System**:
   - `STATUS: READY` — Core compiler capabilities fully implemented.
   - `STATUS: PARTIAL` — Features partially supported; explicit implemented vs missing list prevents hallucination or powerpoint workarounds.
   - `STATUS: BLOCKED` — Unlocks as corresponding v6 ecosystem modules ship.
4. **Run Isolation & Immutable Conditions**:
   - Base project directories contain **only** `TASK.md` (and immutable test fixtures like `invalid_effect.omni`).
   - Base directories **never** contain `BENCHMARK_REASONING.md`, `source/`, `tests/`, or `RESULTS.md`.
   - All run outputs live exclusively inside `RUN_xxx_<MODEL_NAME>/` subfolders created at runtime.

---

## Phase: Project Benchmarks (Consolidated Project Phases)

*All project phases (v1.0 → v7 benchmarks) consolidated here. Every task is reset to [ ] and must be re-verified against the Anti-Shortcut Constitution above before being checked.*

---

### v1.0 — Core MVP
- [ ] Phase 0: Specification & Harness Setup
- [ ] Phase 1: Lexer & Tokenizer (universal `:` token, no fused `UI:`/`scene:`)
- [ ] Phase 2: Parser & AST (universal block rule, AST)
- [ ] Phase 3: Semantic Analysis & Symbol Table (name resolution, scopes)
- [ ] Phase 4: Static Type Checker & Effect Enforcement (uses/reads/writes/pure, require/ensure)
- [ ] Phase 5: OMNI MIR Generator (serializable, typed, effect-aware)
- [ ] Phase 6: JS Emitter & Runtime (ES6, live-link batching, HTML wrapper)
- [ ] Phase 7: CLI Tool (`omni`) & Conformance Suite



## v2 — Loops, 3D, Custom Types


### v2.1 — Loops + `join` [SUB-AGENT: depends on v1.0]
- [ ] Write failing unit test `tests/test_loops.py` (TDD)
- [ ] Lexer: `for` `in` `break` `continue` keywords
- [ ] Parser: `for x in List:` `break` `continue` `end`
- [ ] Checker: loop variable scoping, `break`/`continue` validity
- [ ] MIR: loop lowering with labels/jumps
- [ ] Emitter: ES6 `for...of` + `break`/`continue` labels
- [ ] Builtin: `join(list: List, sep: Text) -> Text`
- [ ] Property tests: `hypothesis` for loop iteration equivalence
- [ ] **Quality Gates**: `pytest` (18 tests green), new test files ruff-clean
- [ ] **Property Tests**: Loop iteration equivalence, `join` correctness


### v2.2 — 3D Primitives [SUB-AGENT: depends on v2.1]
- [ ] Lexer: `scene:` keyword, shape keywords (`box`, `sphere`, `cylinder`, `plane`, `light`, `camera`)
- [ ] Parser: `scene:` block with attributes (`size`, `color`, `pos`, `rotation`, `scale`, `texture`, `click`)
- [ ] Checker: 3D attribute type validation
- [ ] MIR: 3D scene graph lowering
- [ ] Emitter: Three.js scene generation (scene, camera, renderer, mesh, light)
- [ ] 3D Snapshot tests: rendered output comparison
- [ ] **Quality Gates**: `pytest` (19 tests green), new test files ruff-clean
- [ ] **3D Snapshot Tests**: Rendered output comparison


### v2.3 — Custom Types [SUB-AGENT: depends on v2.2]
- [ ] Lexer: `type` keyword, `{ field: Type, ... }` syntax
- [ ] Parser: `type Name = { field: Type, ... }` with nested types
- [ ] Checker: struct type validation, field access checking, nested type resolution
- [ ] Emitter: TypeScript-like `interface` emission for JS target
- [ ] Checker: field access validation (dot notation)
- [ ] **Quality Gates**: `pytest` (17 tests green), new test files ruff-clean
- [ ] **Type Tests**: Struct field access, nested types, type compatibility



## v3 — Native Lanes + WASM (4 Sub-Phases)


### v3.1 — C Emitter + Flecs Adapter [SUB-AGENT: depends on v2 complete]
- [ ] C emitter: MIR → C99 code (functions, structs, effects as annotations)
- [ ] Flecs C API adapter: component registration, query iteration, system scheduling
- [ ] CMake build integration (clang/gcc/msvc)
- [ ] Native binary output (x86_64, arm64) — requires clang/gcc on target host
- [ ] **Quality Gates**: Same strict gates (95% cov, 90% mutmut), native perf budget
- [ ] **Flecs Adapter Conformance**: Query iteration, system scheduling, component storage


### v3.2 — Rust Emitter + Bevy Adapter [SUB-AGENT: depends on v2 complete, parallel with v3.1]
- [ ] Rust emitter: MIR → Rust (owned types, lifetimes, async effects)
- [ ] Bevy ECS adapter: `World`, `Query`, `System`, `Schedule` integration
- [ ] Cargo build integration
- [ ] **Quality Gates**: Same strict gates, `cargo test`, `cargo clippy -D warnings` — cargo not installed locally; skipped


### v3.3 — WASM Target [SUB-AGENT: depends on v3.1]
- [ ] `clang --target=wasm32` for browser (WebGL canvas)
- [ ] `clang --target=wasm32-wasi` for server/edge
- [ ] WASM runtime boilerplate (imports, memory, JS glue)


### v3.4 — Integration + v3 Gates [SUB-AGENT: depends on v3.1, v3.2, v3.3]
- [ ] Cross-backend conformance: same `.omni` runs identically on JS, native, WASM
- [ ] **Quality Gates**: 95% coverage, 90% mutation, native/WASM perf budgets — coverage 90.44% (gate 90%); mutation/perf budgets not yet run
- [ ] **Flecs/Bevy Adapter Conformance**: same Omni semantic model, different backends



## v4 — SMT Verification + AI Tooling


### v4.1 — SMT Verification [SUB-AGENT: depends on v3]
- [ ] SMT backend (Z3) integration for contract verification — `omni_compiler/smt.py` (z3-solver 5.1.0.0)
- [ ] `omni verify contract` proves `require`/`ensure` statically — `omni verify <file>` CLI command
- [ ] Counterexample generation for failed proofs — concrete param values + result from Z3 model
- [ ] **Quality Gate**: SMT verification passes for all contracts in test suite (21 tests in test_smt.py)


### v4.2 — AI Tooling [SUB-AGENT: depends on v4.1, parallel with v4.1]
- [ ] `omni suggest fix`: adversarial test suite, ranked fixes — `omni_compiler/ai_tools.py::suggest_fix` (automatic@0.95 first, suggested@0.7), `apply_fix`/`apply_automatic_fixes` span edits
- [ ] `omni generate test`: property-based test generation from contracts — hypothesis `@given` + sample + contract-present tests
- [ ] `omni trace execution`: step-through debugger API — ordered events with env snapshots, per-iteration loop tracing
- [ ] LSP server compliance tests — `omni_compiler/lsp.py` stdio JSON-RPC (initialize/didOpen→publishDiagnostics/hover/shutdown/exit)


### v4 Quality Gates (Complete)
- [ ] `pytest` → **256 passed, 3 skipped** (skips: gcc/cargo not installed)
- [ ] Coverage → **90.20% ≥ 90%** branch gate
- [ ] Ruff → all new/edited files clean (legacy checker/parser/lexer debt remains, documented)
- [ ] Mypy --strict → new files (smt.py, ai_tools.py, lsp.py) zero errors; only legacy imports surface debt
- [ ] CLI wiring: `verify`, `suggest`, `generate`, `trace`, `lsp` added to `cli.py` + 13 in-process CLI tests



## v5 — Distributed + Self-hosting + Visual


### v5.1 — Self-Hosting Compiler [SUB-AGENT: depends on v4]
- [ ] OmniScript compiler written in OmniScript
- [ ] Compiler compiles itself (bootstrap)
- [ ] **Quality Gate**: Self-hosted compiler passes all test suites


### v5.2 — Visual Editor [SUB-AGENT: depends on v4]
- [ ] Block-based visual editor (drag-drop → OmniScript)
- [ ] E2E tests: drag-drop → generate `.omni` → compile → run


### v5.3 — Distributed Systems [SUB-AGENT: depends on v4]
- [ ] Actor model: `actor`, `send`, `receive`, `spawn`
- [ ] Message passing, clustering, fault tolerance
- [ ] Chaos testing: network partition, node failure simulation



## v1.0 Quality Gate Status (Pre-Checkoff)
- [ ] `ruff check omni_compiler/ tests/` — zero warnings
- [ ] `mypy --strict omni_compiler/` — zero errors
- [ ] `pytest --cov=omni_compiler --cov-fail-under=90 --cov-branch` ≥ 90%
- [ ] `mutmut run --paths-to-mutate omni_compiler --tests-dir tests` — score ≥ 80%



### v6 Phase 1: Foundations
- [ ] `omnisys-core` — core types, errors, result/option, prelude
- [ ] `omnisys-collections` — List, Map, Set, Deque, Heap, RingBuffer
- [ ] `omnisys-async` — Task, Future, Stream, Channel, Select, Timeout
- [ ] `omnisys-fs` — Path, File, Dir, Watch, Temp, Atomic write
- [ ] `omnisys-serde` — JSON, TOML, YAML, MsgPack, CBOR, Schema
- [ ] `omnisys-error` — Error types, Context, StackTrace, ErrorId
- [ ] `omnisys-test` — Assertions, Property testing, Mocking, Bench
- [ ] **Quality Gates**: pytest green (329 package tests, all also green under `-W error`), coverage ≥95% branch (all 7 packages 100% branch), mypy `--strict` clean (7 src files), ruff clean (check + format)
- [ ] **Research Gate**: Research doc per module (7 × `RESEARCH.md` with JS-reference grounding + deviation tables)


### v6 Phase 2: App Foundations
- [ ] `omnisys-ui` — Cross-platform UI (SwiftUI/WPF/Qt/web principles)
- [ ] `omnisys-db` — Data platform (SQL, query builder, migrations, transactions)
- [ ] `omnisys-net` — HTTP/WS/RPC, client/server, middleware
- [ ] `omnisys-http` — High-level HTTP client/server
- [ ] **Quality Gates**: Same strict gates
- [ ] **Research Gate**: Research doc per module


### v6 Phase 3: Graphics/GPU/Simulation
- [ ] `omnisys-graphics` — Rendering abstraction (Vulkan/Metal/DX/WebGPU)
- [ ] `omnisys-gpu` — GPU compute (CUDA/Metal/Vulkan/WebGPU)
- [ ] `omnisys-scene` — 3D scene graph (Vulkan/Metal/DX/WebGPU)
- [ ] `omnisys-sim` — ECS, physics, simulation (Flecs/Bevy/Custom)
- [ ] **Quality Gates**: Same strict gates
- [ ] **Research Gate**: Per-module research doc


### v6 Phase 4: Media/Platform [SUB-AGENT: parallel] ✅ COMPLETE
- [ ] `omnisys-audio` — Audio I/O, synthesis, processing
- [ ] `omnisys-video` — Video decode/encode, streaming
- [ ] `omnisys-camera` / `omnisys-microphone` — Device access (NOT registry modules — device access is an escape surfaced via `omnisys-platform.capabilities()`; folded into platform per OMNI_HISTORY.md)
- [ ] `omnisys-platform` — Native platform APIs (Windows/Linux/macOS/mobile)


### v6 Phase 5: Security/Observability/Tooling [SUB-AGENT: parallel] ✅ COMPLETE
- [ ] `omnisys-crypto` — Hash, encrypt, sign, KDF, TLS (portable lane: hashlib/hmac/secrets; real AES-256 an escape)
- [ ] `omnisys-auth` — AuthZ/AuthN, OAuth, JWT, sessions (compact signed tokens; real JWT/OAuth2 escapes)
- [ ] `omnisys-observability` — Logging, metrics, tracing, profiling
- [ ] `omnisys-tool` — LSP, formatter, debugger, docgen, migration tools (bridges to `omni_compiler.cli` for check/explain)


### v6 Phase 5: AI/Advanced [SUB-AGENT: parallel] ✅ COMPLETE
- [ ] `omnisys-ai` — Tensors, autograd, inference, tool use (pure dense-tensor core; GPU/autograd escapes)
- [ ] `omnisys-async` (advanced) — Distributed actors, clustering (escapes on existing `omnisys-async` package; `omnisys_async.actor` submodule, v5.3 `sim.actor` port) ✅ COMPLETE
- [ ] `omnisys-pkg` — Package manager, registry, resolver
- [ ] **Quality Gates**: Package manager self-hosting, registry security audit


### v6 Phase 6: Language Completion

- [ ] **Real diagnostic locations** — parser.py: track line/col in every AST node; cli.py/ai_tools.py _diagnostic_from_exception: extract location from SyntaxError/token instead of hardcoding {1,1}; DiagnosticError.to_dict() emits real span/location
- [ ] **try/catch + on error clause** — lexer.py: TRY/CATCH/FINALLY tokens; parser.py: TryStmt with try/else/finally blocks; checker.py: effect tracking across handlers; emitter.py/mir.py: TryStmt lowering to try/catch/finally in JS, setjmp/longjmp in C, Result in Rust
- [ ] **await / async integration for uses network** — parser.py: AWAIT token + AwaitExpr; checker.py: functions with uses network return Promise; await unwraps Promise; effect validation ensures await only on network/async calls; emitter: await → JS await, C callback, Rust .await
- [ ] **while loop** — lexer.py: WHILE token; parser.py: WhileStmt(cond, body); checker.py: condition must be Boolean, body scope, break/continue validity; emitter.py: while lowering to JS while, C while, Rust loop
- [ ] **Typed loop variables (for item: Type in list)** — parser.py: extend ForStmt with optional type annotation on loop var; checker.py: use annotated type instead of hardcoded Number for element access; fixes E-TYPE-002 on field access
- [ ] **x[i] indexing, % modulo, range()** — parser.py: IndexExpr(op='index') + BinaryExpr(op='%') + RangeExpr; checker.py: index requires List/Array + Number index; % requires Number operands; range() builtin returns List; emitter: JS arr[i], % operator, Array.from({length: n}, (_, i) => i)
- [ ] **String ops: split, charAt, substring, toNumber** — omnisys_registry.py: add to core module; omnisys/core.js: implement split(sep), charAt(i), substring(start, end?), toNumber(); checker.py: builtin signatures; emitter: direct calls
- [ ] **global / explicit module-state keyword** — lexer.py: GLOBAL token; parser.py: GlobalDecl at module level or global qualifier in assign; checker.py: module_vars includes global names; emitter: module-scope var not function-local; lifts writes wall (MEDIUM-10)
- [ ] **Static call-site arity + type checking** — checker.py: in check_identifier/FunctionCall, validate arg count matches declared params; validate arg types against param types (subtype); emit DiagnosticError on mismatch
- [ ] **Map/dict literal {k: v}** — lexer.py: support {...} as MapLiteral in expression context (distinguish from struct); parser.py: MapLiteralExpr; checker.py: infer Map type from key/value types; emitter: plain JS object {"k": v} (matches omnisys.collections "Map (plain object)" runtime; JS `Map` objects do not support `m["k"]` reads), C struct map, Rust HashMap
- [ ] **Escape braces \{ in text interpolation** — lexer.py: in TEXT token, treat \{ and \} as literal braces not interpolation; parser: Literal preserves escaped braces; emitter: outputs literal { } in template strings
- [ ] **UI template validation in check** — checker.py: parse UI block template at check time; validate click="fn" targets exist in scope; validate slot names match declared slots; emit E-UI-001/002 for missing targets/slots per §9.3
- [ ] **DOM read path for form input capture** — omnisys_registry.js: ui.getValue(selector) / ui.getFormData(form); omnisys/ui.js: implement querySelector + value extraction; checker.py: capability 'dom' for read; emitter: wire to DOM APIs
- [ ] **Native keywords: ar / en / fr / es (lexer tables + diagnostics i18n)** — lexer.py: KEYWORDS_BY_LANG = {lang: {TokenType: "localized"}}; on file start `# lang: ar` sets active table; tokenizer matches localized keywords → same TokenType; cli.py/ai_tools.py: diagnostic messages localized per active language; RTL-aware token positions for ar



### v6 Phase 7: Emitter Correctness & Codegen

- [ ] **Parenthesized expressions preserved in all emitters** (`group` node, HIGH-3) — fixed; previously `(a+b+c)/5` emitted `a+b+c/5` (3.3, 3.4 C-05)
- [ ] **`and`/`or`/`not` logical operators in parser** (`parse_or`/`parse_and`/`parse_not`) — fixed; previously lexed + spec §6.3 but no parser production (2.3)
- [ ] **Negative number literals** (`UnaryExpr` `neg`) — fixed; previously `x is -1` was a syntax error (2.1)
- [ ] **`_js_template` CSS mangling** — `_js_template` now treats every brace inside `<style>` blocks as literal CSS; `{{`/`}}` escapes remain everywhere; `checker.validate_ui_template` is style-aware (2.1). `.panel { padding: 8px; }` survives verbatim
- [ ] **Scene `pos="{var}"` slots preserved at build** — `_js_scene_pos_set` keeps slot-valued `pos` as a runtime expression (split on commas at runtime) so `position.set` is emitted; `camera pos={var}` too (3.4 C-04)
- [ ] **`let`-hoisting for names assigned inside nested `if`/`for`** — `_assigned_names` recurses into nested blocks; module-scope + function-local declarations cover nested first-assigns (2.1)
- [ ] **Module-scope `let` excluded when name collides with any function param** — per-function `let` locals are emitted inside each function (subtracting only that function's params), so `res`/`payload`/`elapsed` no longer disappear (2.3)
- [ ] **Scene JS artifact self-contained** — top-level Three.js loader is DOM-guarded; auto-inits when `THREE` already present; `renderUI`/`bindClicks` guard missing DOM; runs under a bare 2-field stub (3.4 C-06)
- [ ] **`sim.*` lowering parity** — C now lowers `sim.run` (world tick loop) and `sim.query` (compilable empty-list stub, in source order); Rust lowers `sim.run`/`sim.query` to Bevy scaffolding comments + compilable stubs; no raw `sim.*` identifiers leak into C/Rust output (3.4 C-08)



### v6 Phase 8: Platform Parity & Backend Conformance

- [ ] **`import OMNISYS.scene` reachable** — parser now accepts SCENE keyword token in import path; previously E-SYNTAX-001 while registry advertised the module (3.4 C-03) — fixed
- [ ] **E-BACKEND-001: OMNISYS imports block C/Rust** — cli.py now gates **per-capability** (§8.3): an import-only program (no `omnisys.*` call) builds on native targets; only programs actually invoking `omnisys.*` are rejected with E-BACKEND-001, offering a `--target js` auto-fix (3.4 C-01) — fixed
- [ ] **JS lane ECS runtime for `sim.*`** — `simulation_engine/runtime.js` now ships `createEcs()` wired into the flat `sim` object: `sim.entity/component/get/system/run/query/remove_entity/entities/snapshot`; `sim.run(steps)` arg-type-dispatches (number → ECS, no-arg → actor drain), so v5.3 flat API and actor API coexist; `scripts/run-omnisys.js` binds `global.sim` (3.4 C-02) — fixed
- [ ] **`gpu.buffer` requires GPU capability** — registry now tags `gpu.buffer` with `GPU` (3.4 C-07) — fixed
- [ ] **serde capability modeling** — `serde.json_decode` and `serde.base64_decode` now carry the `panic` capability (fallible decoders may abort); pure serialization fns stay pure (2.3) — fixed
- [ ] **`throw_error` declared `pure` but throws at runtime** — registry now tags `error.throw_error` with the new `panic` capability (added to the spec §8.2 vocabulary + capability matrix); checker enforces `uses panic` at every boundary (1.4) — fixed



### v6 Phase 9: SMT Verification Expansion

- [ ] **Struct construction/access in contracts** — smt.py now models struct `TypeDecl`s as Z3 algebraic datatypes (`_build_struct_sorts`: topological dependency order, recursive struct → `unsupported`); `StructConstruct` translates to the datatype constructor (field order preserved) and `FieldAccess` to the datatype accessor; struct params become Z3 `Const`s and are unsupported cleanly elsewhere. Nested structs verified.
- [ ] **Function calls in contracts** — user functions called from `require`/`ensure` are inlined (`_inline_call`): fresh prefixed param consts, callee `require`s assumed, body symbolically executed, fresh result const constrained by `Implies(And(path_conds), result == ret.expr)` + `Or(And(conds))`; recursion → `unsupported`. Ensure-side translation guards are now *assumed*, not negated (`_verify` `assumed` list), so inlining constraints are definitional.
- [ ] **Loops in verified functions** — `for`/`while` verified by sound bounded unrolling (`_LOOP_BOUND = 3`): `for i in range(n)` / bare Number (values `0..n-1`), `for x in [lit, ...]`, `break`/`continue` dispositions; trip counts provably within the bound (via `require`s, checked against `self._pre`) are fully verified; loops that may exceed the bound report `unsupported` (never an unsound "verified"). Escaped `break`/`continue` → `unsupported`.



### v6 Phase 10: OMNISYS API & Runtime Completion

- [ ] **`net` module: deterministic request/response model** — `server/start/request/get/post/middleware/response` shipped; previously README documented phantom `listen/connect/send` (2.4) — fixed
- [ ] **`http` module shipped** — `client/send/get/post/put/delete/json_get/register/response` exist; previously docs said "planned" (2.3) — fixed
- [ ] **`async` module surfaced** — `task/delay/all/race/any/timeout/channel` registered + reachable from `.omni`; previously 1.6 was BLOCKED (checker whitelisted only `sim.*`) — fixed
- [ ] **UI click delegation survives re-render** — event delegation on container; previously re-render destroyed bound handlers (2.1, HIGH-4) — fixed
- [ ] **`platform.env()` graceful fallback** — added optional default param `env(key, default?)`; returns default instead of empty string (4.4) — fixed
- [ ] **HTTP timeout parameter** — http functions now return Tasks (Promises); `async.with_timeout` registered for timeout composition (2.3) — fixed
- [ ] **UI reactivity: `state_set` triggers re-render** — `state_set` now calls global `_notifyStateChange` wired to `batchUpdate` in emitter (2.1) — fixed
- [ ] **`OMNISYS.error` stack trace capture** — `captureStack()` implemented, errors include stack trace (1.4) — fixed
- [ ] **`net` README synced with real registry API** — docs match actual `net.js` API (2.4) — fixed
- [ ] **`http` README synced** — docs updated to show Task return types and `async` dependency — fixed
- [ ] **`platform` README synced** — docs updated to show actual API (`now`, `os`, `arch`, `env`, `info`, `sleep_ms`, `capabilities`) — fixed
- [ ] **`ui` README synced** — docs updated to show stable status, `dom` capability, reactive state — fixed


### v6 Phase 11: Checker Soundness

- [ ] **`reads`/`writes` enforcement live** — E-EFFECT-004 with auto `declare-reads-<resource>` fix; previously parsed but unenforced (2.4) — fixed
- [ ] **Close assignment blind spot** — checker.py:599 `local_names = _assigned_names_ast(fn.body)` exempted any name a function assigns from `writes` checks; a function ASSIGNING a module resource escaped E-EFFECT-004 (2.4). Fixed by:
  - Added `_loop_vars_ast` helper (line 161) collecting only for-loop variables (block-scoped in emitter).
  - Changed `local_names = _loop_vars_ast(fn.body)` in `enforce_function_effects` (line 1259) so plain-assigned module names are no longer exempt from reads/writes checks.
  - Removed local-names exemption from writes check (Assignment branch now only exempts params).
  - Updated fixture `03_loops_and_lists.omni` to declare `reads total` + `writes total` for `process` function.
  - Added 3 regression tests in `test_checker.py`: assigned module resource flagged, declared OK, loop-var shadowing not flagged.
  - Fixed 4 benchmark sources (`particle_sim`, `finance_dashboard`, `inventory`, `voice_recorder`) to declare their reads/writes per the reference pattern.



### v7 Benchmark Suite (31 Projects Across 7 Phases)

#### Phase 0: OmniScript Language Discovery (5 Projects) — `STATUS: READY`
- [ ] **0.1 Unit Converter**: Multi-unit conversion engine with boundary validation, precision constraints, and error reporting.
- [ ] **0.2 Todo Engine**: Data structure, state manager, and task list operations (filtering, completion, sorting).
- [ ] **0.3 RPG Action Engine**: Character action and ability manager requiring explicit side-effect and capability management, plus a secondary malformed source file test case. *(Includes immutable fixture `invalid_effect.omni`)*.
- [ ] **0.4 Particle Motion Engine**: High-performance data-oriented particle simulation supporting multi-target compilation.
- [ ] **0.5 State-Machine Adventure**: Interactive story engine with state transitions, inventory tracking, and multi-backend build validation (JS + C + WASM).

#### Phase 1: Foundations (6 Projects)
- [ ] **1.1 Collections / Log Analyzer**: Log file parsing, filtering, aggregation, and statistical summary reporting.
- [ ] **1.2 Filesystem / File Organizer**: Directory tree synchronization and file structure management under capability policy enforcement.
- [ ] **1.3 Serialization / Config Exporter**: Structured configuration format parser, schema validator, and multi-format exporter.
- [ ] **1.4 Error Handling / Recovery**: Multi-step data processing pipeline with error classification, context enrichment, and graceful recovery.
- [ ] **1.5 Testing / Self-Test Suite**: **Meta-benchmark** — Authoring a complete test suite (unit, property-based, mocking, performance) for a prior project.
- [ ] **1.6 Async / Job Processor**: Concurrent job queue processing with cancellation, timeouts, streams, and task synchronization.

#### Phase 2: Application Foundations (4 Projects) — COMPLETE ✅ (RUN_001_DEEPSEEK_V4_FLASH_FREE)
- [ ] **2.1 GUI / Personal Finance Dashboard**: Rich interactive graphical application featuring navigation, forms, tables, reactive state, and live data bindings.
- [ ] **2.2 Database / Inventory System**: Relational inventory management system with schema definition, transactional data updates, and query composition.
- [ ] **2.3 HTTP / REST Client**: External API integration client with request formatting, response deserialization, timeouts, and network capability declarations.
- [ ] **2.4 Networking / Chat Server**: Multi-client real-time messaging server supporting connection lifecycles, broadcasting, and protocol handling.

#### Phase 3: Graphics / GPU / Simulation (4 Projects) — COMPLETE ✅ (RUN_001_DEEPSEEK_V4_FLASH_FREE)
- [ ] **3.1 2D Graphics / Canvas App**: Interactive vector graphics drawing canvas with geometric shapes, transforms, colors, and user input events.
- [ ] **3.2 3D Scene / Solar System**: Interactive 3D scene visualization with hierarchical transforms, camera positioning, lighting, and orbital motion.
- [ ] **3.3 GPU / Image Filter**: High-performance image matrix processing utilizing hardware GPU compute pipelines.
- [ ] **3.4 ECS / Particle Sim Coexistence**: Integrated application proving data-oriented entity-component simulation coexists seamlessly with 3D scene rendering and graphics pipelines.

#### Phase 4: Media / Platform (4 Projects) — COMPLETE ✅ (RUN_001_CLAUDE_3_5)
- [ ] **4.1 Audio / Voice Recorder**: Audio input capture, waveform signal processing, and playback management.
- [ ] **4.2 Video / Video Player**: Video media stream decoder, timeline seeking, metadata extraction, and frame display.
- [ ] **4.3 Media / Camera Capture**: Real-time camera video and audio stream device capture under capability enforcement.
- [ ] **4.4 Platform / System Utility**: System utility leveraging platform-native OS features with portable fallback abstractions.

#### Phase 5: Security / Tooling (5 Projects)
- [ ] **5.1 Crypto / Secure File Vault**: Encrypted file storage utility with hashing, key derivation, and file access policies.
- [ ] **5.2 Auth / Authenticated Web Service**: User authentication service combining network endpoints, crypto primitives, and persistent storage.
- [ ] **5.3 Observability / App Diagnostics**: Diagnostic tool that inspects, profiles, and isolates failure points in a malfunctioning application.
- [ ] **5.4 Tooling / Project Inspection**: Static analysis tool leveraging compiler inspection APIs to analyze and explain an unfamiliar project.
- [ ] **5.5 Native Interop / Escape Hatch**: Utility requiring functionality unavailable in standard APIs, utilizing supported native interop / FFI mechanisms while preserving type and safety boundaries.


#### Phase 6: AI / Advanced (3 Projects)
- [ ] **6.1 AI / AI Assistant**: Local AI model inference, tensor operations, and structured output formatting.
- [ ] **6.2 Advanced Concurrency / Distributed Actors**: Distributed message-passing actor cluster with node membership, clustering, and failover.
- [ ] **6.3 Package System / Multi-Package App**: Multi-module application validating package imports, dependency resolution, and dead-code elimination.



---
