# AI-Native Tooling Architecture

**Deliverable §14M.** How OMNISYS — and the `omni` compiler API — serve AI
coding agents as first-class users.

OMNI_SPEC.md §12 defines the stable `omni` compiler API. OMNISYS extends that
philosophy to every module: inspectable, typed, machine-readable, and
deterministic.

---

## 1. The Interrogable Compiler

The `omni` CLI is the AI's co-developer (spec §12):

| Command | What an agent gets |
|---------|--------------------|
| `omni inspect symbol` | typed symbol record (name, kind, type, declared effects, span, deps, exported) |
| `omni explain error` | plain-language explanation of a failing error |
| `omni find dependency` | what a symbol depends on; what depends on it |
| `omni generate test` | a draft test for a function |
| `omni verify contract` | that `require`/`ensure` assertions are present and well-typed |
| `omni trace execution` | step-through execution with environment snapshots |
| `omni suggest fix` | ranked, machine-applicable fixes |
| `omni summarize module` | what a file does, in short |

Outputs are versioned, stable JSON (`omni.diagnostic`, `omni.symbol`) that
agents assert on by code, never by message text.

## 2. Diagnostics as Keys

Every error is an `omni.diagnostic` with a stable code (e.g. `E-EFFECT-003`,
`E-IMPORT-002`, `E-BACKEND-001`), absolute character spans, and ranked
structured fixes (`insert`/`replace`/`delete` with spans) marked
`automatic` or `suggested`. An agent applies fix number one, re-checks, moves
on.

## 3. OMNISYS Is AI-Native at Every Layer

- **Registry as contract** — `omnisys_registry.py` exposes every module's
  functions with type + effects; agents query it without reading source.
- **Typed APIs** — no untyped surface; every signature is inspectable.
- **Deterministic** — same program, same MIR, same diagnostics, same trace.
- **One way to do each thing** — the three-audience lens (§14E) keeps the
  surface greppable.
- **Tool use** — the `omni` API reports against the Omni semantic model, so
  entities/systems/queries are first-class concepts for agents.

## 4. AI Tooling Modules (spec §12 / v4)

The compiler ships LSP, `suggest fix`, `generate test`, and `trace` built on
the locked contracts. OMNISYS consumes them: a module's README documents its
API so `omni generate test` can produce meaningful tests, and `omni inspect`
resolves OMNISYS calls to their registry types.

## 5. The Feedback Loop

The v7 benchmark (OMNI_SPEC / TODO v7) measures agent × ecosystem friction and
converts it into concrete language, API, compiler, diagnostic, and
documentation improvements that feed back into v6. See
[`18-roadmap.md`](18-roadmap.md).

*See also:* [`04-api-design-principles.md`](04-api-design-principles.md).