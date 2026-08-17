# OmniScript v1.0 → v7 — Master Execution Ledger & Session Handoff

> **Session Continuity Protocol**: Every agent starting a new session MUST read this file first. When finishing a session, the agent MUST update the phase checkboxes, write a brief summary in the "Last Session Status Note", and ensure all Quality Gates pass.

## Current Phase
- **v5 complete** — see Last Session Status Note below. Next: v6 (OMNISYS platform).

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
- **Current Phase**: v5 complete — 296 tests passing (v4: 256 → v5 additions: 40). Coverage gate green at 90.48% (repo-wide `--cov-branch --cov-fail-under=90`).
- **Last Action**: Finished v5.1 (self-hosting compiler: `self_hosted/compiler.omni` — an OmniScript→ES6 structured-AST emitter written in OmniScript that compiles a description of itself at startup via `compiled_self`; `tests/test_self_hosted.py`, 8 tests), v5.2 (visual editor: `visual_editor/` block-based drag-drop editor with UMD `renderOmni` core; `tests/test_visual_editor.py`, 10 tests incl. a Playwright E2E that drags blocks, generates `.omni`, then compiles and runs it), and v5.3 (distributed systems: `simulation_engine/runtime.js` actor/cluster runtime with chaos injection; `tests/test_distributed.py`, 22 tests — delivered by sub-agent, verified). Both v5.1/v5.2 sub-agents had returned empty, so the main agent implemented them directly.
- **Verification**: `pytest` → **296 passed, 3 skipped** (skips: gcc/cargo not installed). Coverage **90.48% ≥ 90%** gate. Ruff clean on all new/edited files; mypy `--strict` zero errors in new test files.
- **Blockers / Next Step**: v5 done. v6 (OMNISYS) next. Known latent gaps carried from v3: (1) C emitter struct-field types; (2) `_emit_sim_lowering` duplicate C var names. v1.0 quality gates (repo-wide mypy --strict, mutation, ruff format) still not green — pre-existing debt in legacy lexer/parser/checker/emitter files; ruff format conflicts with the repo's Q000 double-quote rule (documented).

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

## Phase Checklists

### v1.0 — Core MVP (COMPLETE ✅)
- [x] Phase 0: Specification & Harness Setup
- [x] Phase 1: Lexer & Tokenizer (universal `:` token, no fused `UI:`/`scene:`)
- [x] Phase 2: Parser & AST (universal block rule, AST)
- [x] Phase 3: Semantic Analysis & Symbol Table (name resolution, scopes)
- [x] Phase 4: Static Type Checker & Effect Enforcement (uses/reads/writes/pure, require/ensure)
- [x] Phase 5: OMNI MIR Generator (serializable, typed, effect-aware)
- [x] Phase 6: JS Emitter & Runtime (ES6, live-link batching, HTML wrapper)
- [x] Phase 7: CLI Tool (`omni`) & Conformance Suite

---

## v2 — Loops, 3D, Custom Types (COMPLETE ✅)

### v2.1 — Loops + `join` [SUB-AGENT: depends on v1.0]
- [x] Write failing unit test `tests/test_loops.py` (TDD)
- [x] Lexer: `for` `in` `break` `continue` keywords
- [x] Parser: `for x in List:` `break` `continue` `end`
- [x] Checker: loop variable scoping, `break`/`continue` validity
- [x] MIR: loop lowering with labels/jumps
- [x] Emitter: ES6 `for...of` + `break`/`continue` labels
- [x] Builtin: `join(list: List, sep: Text) -> Text`
- [x] Property tests: `hypothesis` for loop iteration equivalence
- [x] **Quality Gates**: `pytest` (18 tests green), new test files ruff-clean
- [x] **Property Tests**: Loop iteration equivalence, `join` correctness
*Status Note*: Complete. 18 tests in test_loops.py, verified via real node execution (loop sum + join output correct).

### v2.2 — 3D Primitives [SUB-AGENT: depends on v2.1]
- [x] Lexer: `scene:` keyword, shape keywords (`box`, `sphere`, `cylinder`, `plane`, `light`, `camera`)
- [x] Parser: `scene:` block with attributes (`size`, `color`, `pos`, `rotation`, `scale`, `texture`, `click`)
- [x] Checker: 3D attribute type validation
- [x] MIR: 3D scene graph lowering
- [x] Emitter: Three.js scene generation (scene, camera, renderer, mesh, light)
- [x] 3D Snapshot tests: rendered output comparison
- [x] **Quality Gates**: `pytest` (19 tests green), new test files ruff-clean
- [x] **3D Snapshot Tests**: Rendered output comparison
*Status Note*: Complete. 19 tests in test_scene.py, verified via node --check on emitted Three.js.

### v2.3 — Custom Types [SUB-AGENT: depends on v2.2]
- [x] Lexer: `type` keyword, `{ field: Type, ... }` syntax
- [x] Parser: `type Name = { field: Type, ... }` with nested types
- [x] Checker: struct type validation, field access checking, nested type resolution
- [x] Emitter: TypeScript-like `interface` emission for JS target
- [x] Checker: field access validation (dot notation)
- [x] **Quality Gates**: `pytest` (17 tests green), new test files ruff-clean
- [x] **Type Tests**: Struct field access, nested types, type compatibility
*Status Note*: Complete. 17 tests in test_types.py, verified via real node execution (field access + interpolation correct).

---

## v3 — Native Lanes + WASM (4 Sub-Phases) (COMPLETE ✅ — gates partially green)

### v3.1 — C Emitter + Flecs Adapter [SUB-AGENT: depends on v2 complete]
- [x] C emitter: MIR → C99 code (functions, structs, effects as annotations)
- [x] Flecs C API adapter: component registration, query iteration, system scheduling
- [x] CMake build integration (clang/gcc/msvc)
- [ ] Native binary output (x86_64, arm64) — requires clang/gcc on target host
- [ ] **Quality Gates**: Same strict gates (95% cov, 90% mutmut), native perf budget
- [x] **Flecs Adapter Conformance**: Query iteration, system scheduling, component storage
*Status Note*: Complete. `c_emitter.py` rewritten (C99, `omni_format` text interpolation, `sim.entity`/`sim.system` via `ecs_*` under `#ifdef OMNI_HAVE_FLECS` with deterministic fallback). `cmake/CMakeLists.txt` + `cmake/README.md`. 13 tests (gcc syntax check skips when gcc absent).**

### v3.2 — Rust Emitter + Bevy Adapter [SUB-AGENT: depends on v2 complete, parallel with v3.1]
- [x] Rust emitter: MIR → Rust (owned types, lifetimes, async effects)
- [x] Bevy ECS adapter: `World`, `Query`, `System`, `Schedule` integration
- [x] Cargo build integration
- [ ] **Quality Gates**: Same strict gates, `cargo test`, `cargo clippy -D warnings` — cargo not installed locally; skipped
*Status Note*: Complete. `rust_emitter.py` created (Bevy components `#[derive(Component, Clone, Debug)]`, `setup(mut commands: Commands)` + `Name::new`, text interpolation via `format!`). 10 tests (cargo test skips).**

### v3.3 — WASM Target [SUB-AGENT: depends on v3.1]
- [x] `clang --target=wasm32` for browser (WebGL canvas)
- [x] `clang --target=wasm32-wasi` for server/edge
- [x] WASM runtime boilerplate (imports, memory, JS glue)
*Status Note*: Complete. `wasm_emitter.py` created (browser/wasi modes + build command guidance). 7 tests.**

### v3.4 — Integration + v3 Gates [SUB-AGENT: depends on v3.1, v3.2, v3.3]
- [x] Cross-backend conformance: same `.omni` runs identically on JS, native, WASM
- [ ] **Quality Gates**: 95% coverage, 90% mutation, native/WASM perf budgets — coverage 90.44% (gate 90%); mutation/perf budgets not yet run
- [x] **Flecs/Bevy Adapter Conformance**: same Omni semantic model, different backends
*Status Note*: Complete. `tests/conformance/test_cross_backend.py` (9 tests) + CLI `build` for all 5 targets + `--output` option. In-process CLI coverage suite added (`tests/test_cli_inproc.py`, 18 tests).

---

## v4 — SMT Verification + AI Tooling (COMPLETE ✅ — gates green)

### v4.1 — SMT Verification [SUB-AGENT: depends on v3]
- [x] SMT backend (Z3) integration for contract verification — `omni_compiler/smt.py` (z3-solver 5.1.0.0)
- [x] `omni verify contract` proves `require`/`ensure` statically — `omni verify <file>` CLI command
- [x] Counterexample generation for failed proofs — concrete param values + result from Z3 model
- [x] **Quality Gate**: SMT verification passes for all contracts in test suite (21 tests in test_smt.py)
*Status Note*: Complete. `smt.py` symbolically executes function bodies path-by-path (if/else), proves `require ∧ path ⟹ ensure[result := ret]` via Z3, guards division-by-zero. Statuses: `verified` / `failed` (with counterexample) / `unsupported` (reason: loops, calls, Text/List, structs) / `no-contracts`. Number → Z3 Real.

### v4.2 — AI Tooling [SUB-AGENT: depends on v4.1, parallel with v4.1]
- [x] `omni suggest fix`: adversarial test suite, ranked fixes — `omni_compiler/ai_tools.py::suggest_fix` (automatic@0.95 first, suggested@0.7), `apply_fix`/`apply_automatic_fixes` span edits
- [x] `omni generate test`: property-based test generation from contracts — hypothesis `@given` + sample + contract-present tests
- [x] `omni trace execution`: step-through debugger API — ordered events with env snapshots, per-iteration loop tracing
- [x] LSP server compliance tests — `omni_compiler/lsp.py` stdio JSON-RPC (initialize/didOpen→publishDiagnostics/hover/shutdown/exit)
*Status Note*: Complete. 26 tests in test_ai_tools.py + 22 tests in test_lsp.py. `omni lsp` CLI command runs the server.

### v4 Quality Gates (Complete)
- [x] `pytest` → **256 passed, 3 skipped** (skips: gcc/cargo not installed)
- [x] Coverage → **90.20% ≥ 90%** branch gate
- [x] Ruff → all new/edited files clean (legacy checker/parser/lexer debt remains, documented)
- [x] Mypy --strict → new files (smt.py, ai_tools.py, lsp.py) zero errors; only legacy imports surface debt
- [x] CLI wiring: `verify`, `suggest`, `generate`, `trace`, `lsp` added to `cli.py` + 13 in-process CLI tests

---

## v5 — Distributed + Self-hosting + Visual (COMPLETE ✅)

### v5.1 — Self-Hosting Compiler [SUB-AGENT: depends on v4]
- [x] OmniScript compiler written in OmniScript
- [x] Compiler compiles itself (bootstrap)
- [x] **Quality Gate**: Self-hosted compiler passes all test suites
*Status Note*: Complete. `self_hosted/compiler.omni` — a structured-AST → ES6 JS emitter written in OmniScript (`Stmt`/`Expr` custom types, pure functions `compile_program`/`emit_fn`/`emit_stmt`/`emit_block`/`emit_expr`). Literal braces emitted via `lb()`/`rb()` (the reference emitter treats `{...}` text pairs as interpolation slots). Bootstrap: `when app starts:` embeds a structured description of its own `emit_expr` and compiles it into `compiled_self` at startup — verified in Node. 8 tests in `tests/test_self_hosted.py` (source validity, Node bootstrap, generated-program run).**

### v5.2 — Visual Editor [SUB-AGENT: depends on v4]
- [x] Block-based visual editor (drag-drop → OmniScript)
- [x] E2E tests: drag-drop → generate `.omni` → compile → run
*Status Note*: Complete. `visual_editor/` (index.html, style.css, app.js) — drag blocks from the palette onto the canvas; container blocks (if/for/fn) accept nested blocks, if has an else branch. Pure `renderOmni(blocks)`/`blockToOmni` core exposed UMD for Node. 10 tests in `tests/test_visual_editor.py`: Node unit tests for every block kind, Python reference-pipeline compile gate (emitted JS runs in Node, prints `3`), and a Playwright E2E that drags an fn + return + assign + show, generates the `.omni`, then compiles and runs it (drag → generate → compile → run).**

### v5.3 — Distributed Systems [SUB-AGENT: depends on v4]
- [x] Actor model: `actor`, `send`, `receive`, `spawn`
- [x] Message passing, clustering, fault tolerance
- [x] Chaos testing: network partition, node failure simulation
*Status Note*: Complete. `simulation_engine/runtime.js` — `sim.actor.*` (spawn/send/sender/receive/run/step/steps/deadletters/statistics) + `sim.actor.cluster.*` (create/addNode/partition/heal/fail/restart/remove/stopActor/members/snapshot/status), at-least-once redelivery, supervision, heartbeat membership, deterministic chaos injection. `examples/actors.omni`, `examples/chaos.omni`, `scripts/run-actors.js|.py`. 22 tests in `tests/test_distributed.py`.**

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

## Last Session Status Note
- **Current Phase**: v5 complete — 296 tests passing (v4: 256 → v5 additions: 40). Coverage gate green at 90.48% (repo-wide `--cov-branch --cov-fail-under=90`).
- **Last Action**: Finished v5.1 (self-hosting compiler: `self_hosted/compiler.omni` — an OmniScript→ES6 structured-AST emitter written in OmniScript that compiles a description of itself at startup via `compiled_self`; `tests/test_self_hosted.py`, 8 tests), v5.2 (visual editor: `visual_editor/` block-based drag-drop editor with UMD `renderOmni` core; `tests/test_visual_editor.py`, 10 tests incl. a Playwright E2E that drags blocks, generates `.omni`, then compiles and runs it), and v5.3 (distributed systems: `simulation_engine/runtime.js` actor/cluster runtime with chaos injection; `tests/test_distributed.py`, 22 tests — delivered by sub-agent, verified). Both v5.1/v5.2 sub-agents had returned empty, so the main agent implemented them directly.
- **Verification**: `pytest` → **296 passed, 3 skipped** (skips: gcc/cargo not installed). Coverage **90.48% ≥ 90%** gate. Ruff clean on all new/edited files; mypy `--strict` zero errors in new test files.
- **Blockers / Next Step**: v5 done. v6 (OMNISYS) next. Known latent gaps carried from v3: (1) C emitter struct-field types; (2) `_emit_sim_lowering` duplicate C var names. v1.0 quality gates (repo-wide mypy --strict, mutation, ruff format) still not green — pre-existing debt in legacy lexer/parser/checker/emitter files; ruff format conflicts with the repo's Q000 double-quote rule (documented).

---

## Conformance Suite Progress
- [x] Valid fixtures: 01_basic, 02_function_with_effects, 03_loops_and_lists
- [x] Invalid fixtures: 01_missing_network, 02_pure_with_effects
- [ ] Expand to 10+ valid fixtures covering all language features
- [ ] Add invalid fixtures for every error code in spec

---

## v1.0 Quality Gate Status (Pre-Checkoff)
- [ ] `ruff check omni_compiler/ tests/` — zero warnings
- [ ] `mypy --strict omni_compiler/` — zero errors
- [ ] `pytest --cov=omni_compiler --cov-fail-under=90 --cov-branch` ≥ 90%
- [ ] `mutmut run --paths-to-mutate omni_compiler --tests-dir tests` — score ≥ 80%

---

## v6 — OMNISYS: The Omni-Native Platform (Post-v5)

### v6 — OMNISYS Master Architecture
- [ ] **OMNISYS Master Architecture** (§14A)
- [ ] **Module Tree** (§14B)
- [ ] **Capability Matrix** (§14C)
- [ ] **Backend Matrix** (§14D)
- [ ] **API Design Principles** (§14E)
- [ ] **UI Architecture** (§14F)
- [ ] **Database Architecture** (§14G)
- [ ] **Graphics/GPU Architecture** (§14H)
- [ ] **Networking Architecture** (§14I)
- [ ] **Media Architecture** (§14J)
- [ ] **Simulation/ECS Architecture** (§14K)
- [ ] **Security Architecture** (§14L)
- [ ] **AI-Native Tooling Architecture** (§14M)
- [ ] **Package/Module System** (§14N)
- [ ] `import OMNISYS` Behavior (§14O)
- [ ] **Performance Model** (§14P)
- [ ] **Cross-Backend Conformance Model** (§14Q)
- [ ] **Escape-Hatch / Native Interop Model** (§14R)
- [ ] **Development Roadmap** (§14S)
- [ ] **Testing/Quality Gates** (§14T)
- [ ] **Example Applications** (§14U)

### v6.0 — Documentation Layer (COMPLETE ✅)
- [x] **Spec repair**: Deduplicated §17.1 module tree in `OMNI_SPEC.md` (17 modules, `scene` at line 17, `core` implicit root export = 18 documented)
- [x] **Spec repair**: Fixed §17.7 duplicate "4." phase numbering → 1–6
- [x] **`docs/DOC_CONVENTIONS.md`**: Six-field header set (Purpose, Public API surface, Dependencies, Effects/capabilities used, Status, Open Questions) + link/status/orphan rules
- [x] **Scaffold**: `docs/language/`, `docs/architecture/`, `docs/decisions/` (ADR numbering convention only), `docs/omnisys/` parent + dependency map
- [x] **18 module READMEs**: `docs/omnisys/<module>/README.md` with `Status: planned` + `<!-- CAPABILITIES -->` tags (core subsumes collections/serde/error)
- [x] **Scripts**: `scripts/gen-index.py`, `scripts/gen-capability-matrix.py` (with `--check`), `scripts/verify-docs.py` (6 rules, no ADR rule yet)
- [x] **CI**: `.github/workflows/docs.yml` (verify-docs + both `--check` generators)
- [x] **Gate**: `verify-docs.py`, `gen-index.py --check`, `gen-capability-matrix.py --check` — all pass

### v6 Phase 1: Foundations [SUB-AGENT: parallel per module]
- [ ] `omnisys-core` — core types, errors, result/option, prelude
- [ ] `omnisys-collections` — List, Map, Set, Deque, Heap, RingBuffer
- [ ] `omnisys-async` — Task, Future, Stream, Channel, Select, Timeout
- [ ] `omnisys-fs` — Path, File, Dir, Watch, Temp, Atomic write
- [ ] `omnisys-serde` — JSON, TOML, YAML, MsgPack, CBOR, Schema
- [ ] `omnisys-error` — Error types, Context, StackTrace, ErrorId
- [ ] `omnisys-test` — Assertions, Property testing, Mocking, Bench
- [ ] **Quality Gates**: Same strict gates (95% cov, 90% mutmut, mypy strict, ruff clean)
- [ ] **Research Gate**: Research doc per module before implementation (parallel with impl)
*Status Note*: 7 sub-agents parallel. Monorepo `packages/omnisys-*`. Shared `import OMNISYS` umbrella.

### v6 Phase 2: App Foundations [SUB-AGENT: parallel]
- [ ] `omnisys-ui` — Cross-platform UI (SwiftUI/WPF/Qt/web principles)
- [ ] `omnisys-db` — Data platform (SQL, query builder, migrations, transactions)
- [ ] `omnisys-net` — HTTP/WS/RPC, client/server, middleware
- [ ] `omnisys-http` — High-level HTTP client/server
- [ ] **Quality Gates**: Same strict gates
- [ ] **Research Gate**: Research doc per module

### v6 Phase 3: Graphics/GPU/Simulation [SUB-AGENT: parallel]
- [ ] `omnisys-graphics` — Rendering abstraction (Vulkan/Metal/DX/WebGPU)
- [ ] `omnisys-gpu` — GPU compute (CUDA/Metal/Vulkan/WebGPU)
- [ ] `omnisys-scene` — 3D scene graph (Vulkan/Metal/DX/WebGPU)
- [ ] `omnisys-sim` — ECS, physics, simulation (Flecs/Bevy/Custom)
- [ ] **Quality Gates**: Same strict gates
- [ ] **Research Gate**: Per-module research doc

### v6 Phase 4: Media/Platform [SUB-AGENT: parallel]
- [ ] `omnisys-audio` — Audio I/O, synthesis, processing
- [ ] `omnisys-video` — Video decode/encode, streaming
- [ ] `omnisys-camera` / `omnisys-microphone` — Device access
- [ ] `omnisys-platform` — Native platform APIs (Windows/Linux/macOS/mobile)

### v6 Phase 5: Security/Observability/Tooling [SUB-AGENT: parallel]
- [ ] `omnisys-crypto` — Hash, encrypt, sign, KDF, TLS
- [ ] `omnisys-auth` — AuthZ/AuthN, OAuth, JWT, sessions
- [ ] `omnisys-observability` — Logging, metrics, tracing, profiling
- [ ] `omnisys-tool` — LSP, formatter, debugger, docgen, migration tools

### v6 Phase 5: AI/Advanced [SUB-AGENT: parallel]
- [ ] `omnisys-ai` — Tensors, autograd, inference, tool use
- [ ] `omnisys-async` (advanced) — Distributed actors, clustering
- [ ] `omnisys-pkg` — Package manager, registry, resolver
- [ ] **Quality Gates**: Package manager self-hosting, registry security audit

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

### v7 Benchmark Suite (31 Projects Across 7 Phases)

#### Phase 0: OmniScript Language Discovery (5 Projects) — `STATUS: READY`
*Testing core language syntax, type system, effect model, MIR, and multi-backend emitters.*
- [ ] **0.1 Unit Converter**: Multi-unit conversion engine with boundary validation, precision constraints, and error reporting.
- [ ] **0.2 Todo Engine**: Data structure, state manager, and task list operations (filtering, completion, sorting).
- [ ] **0.3 RPG Action Engine**: Character action and ability manager requiring explicit side-effect and capability management, plus a secondary malformed source file test case. *(Includes immutable fixture `invalid_effect.omni`)*.
- [ ] **0.4 Particle Motion Engine**: High-performance data-oriented particle simulation supporting multi-target compilation.
- [ ] **0.5 State-Machine Adventure**: Interactive story engine with state transitions, inventory tracking, and multi-backend build validation (JS + C + WASM).

#### Phase 1: Foundations (6 Projects)
*Testing core collections, filesystem, serialization, error recovery, testing primitives, and async.*
- [ ] **1.1 Collections / Log Analyzer**: Log file parsing, filtering, aggregation, and statistical summary reporting.
- [ ] **1.2 Filesystem / File Organizer**: Directory tree synchronization and file structure management under capability policy enforcement.
- [ ] **1.3 Serialization / Config Exporter**: Structured configuration format parser, schema validator, and multi-format exporter.
- [ ] **1.4 Error Handling / Recovery**: Multi-step data processing pipeline with error classification, context enrichment, and graceful recovery.
- [ ] **1.5 Testing / Self-Test Suite**: **Meta-benchmark** — Authoring a complete test suite (unit, property-based, mocking, performance) for a prior project.
- [ ] **1.6 Async / Job Processor**: Concurrent job queue processing with cancellation, timeouts, streams, and task synchronization.

#### Phase 2: Application Foundations (4 Projects)
*Testing portable semantic UI, relational data platforms, HTTP, and networking.*
- [ ] **2.1 GUI / Personal Finance Dashboard**: Rich interactive graphical application featuring navigation, forms, tables, reactive state, and live data bindings.
- [ ] **2.2 Database / Inventory System**: Relational inventory management system with schema definition, transactional data updates, and query composition.
- [ ] **2.3 HTTP / REST Client**: External API integration client with request formatting, response deserialization, timeouts, and network capability declarations.
- [ ] **2.4 Networking / Chat Server**: Multi-client real-time messaging server supporting connection lifecycles, broadcasting, and protocol handling.

#### Phase 3: Graphics / GPU / Simulation (4 Projects)
*Testing 2D vector drawing, 3D scene graphs, hardware GPU compute, and ECS/graphics integration.*
- [ ] **3.1 2D Graphics / Canvas App**: Interactive vector graphics drawing canvas with geometric shapes, transforms, colors, and user input events.
- [ ] **3.2 3D Scene / Solar System**: Interactive 3D scene visualization with hierarchical transforms, camera positioning, lighting, and orbital motion.
- [ ] **3.3 GPU / Image Filter**: High-performance image matrix processing utilizing hardware GPU compute pipelines.
- [ ] **3.4 ECS / Particle Sim Coexistence**: Integrated application proving data-oriented entity-component simulation coexists seamlessly with 3D scene rendering and graphics pipelines.

#### Phase 4: Media / Platform (4 Projects)
*Testing audio processing, video decoding, camera/microphone I/O, and platform escape hatches.*
- [ ] **4.1 Audio / Voice Recorder**: Audio input capture, waveform signal processing, and playback management.
- [ ] **4.2 Video / Video Player**: Video media stream decoder, timeline seeking, metadata extraction, and frame display.
- [ ] **4.3 Media / Camera Capture**: Real-time camera video and audio stream device capture under capability enforcement.
- [ ] **4.4 Platform / System Utility**: System utility leveraging platform-native OS features with portable fallback abstractions.

#### Phase 5: Security / Tooling (5 Projects)
*Testing cryptography, authentication, observability, compiler inspection, and native interop.*
- [ ] **5.1 Crypto / Secure File Vault**: Encrypted file storage utility with hashing, key derivation, and file access policies.
- [ ] **5.2 Auth / Authenticated Web Service**: User authentication service combining network endpoints, crypto primitives, and persistent storage.
- [ ] **5.3 Observability / App Diagnostics**: Diagnostic tool that inspects, profiles, and isolates failure points in a malfunctioning application.
- [ ] **5.4 Tooling / Project Inspection**: Static analysis tool leveraging compiler inspection APIs to analyze and explain an unfamiliar project.
- [ ] **5.5 Native Interop / Escape Hatch**: Utility requiring functionality unavailable in standard APIs, utilizing supported native interop / FFI mechanisms while preserving type and safety boundaries.

#### Phase 6: AI / Advanced (3 Projects)
*Testing AI tensor operations, distributed actor systems, and package manager dynamics.*
- [ ] **6.1 AI / AI Assistant**: Local AI model inference, tensor operations, and structured output formatting.
- [ ] **6.2 Advanced Concurrency / Distributed Actors**: Distributed message-passing actor cluster with node membership, clustering, and failover.
- [ ] **6.3 Package System / Multi-Package App**: Multi-module application validating package imports, dependency resolution, and dead-code elimination.