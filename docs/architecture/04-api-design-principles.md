# OMNISYS API Design Principles

**Deliverable §14E.** The principles every OMNISYS module API must follow.

These derive from OMNI_SPEC.md §17.3 (Do Not Wrap — Design Native), §17.4
(Portable Core + Powerful Escapes), and §17.6.4 (AI-Native Design). They apply
to every function in every module.

---

## 1. Design Native, Do Not Wrap

For each borrowed ecosystem, answer the §17.3 eleven questions **before**
designing the API:

1. What problem is it solving?
2. Which concepts survived because they're genuinely useful?
3. Which exist due to historical constraints?
4. Which APIs are awkward due to host language?
5. Which abstractions are hard for AI agents?
6. Which concepts become first-class Omni concepts?
7. Which remain libraries?
8. Which map to the effect/capability system?
9. What belongs in the portable semantic layer?
10. What must remain backend-specific?
11. What is the escape hatch?

The output is an Omni-native design, never a transliterated host API.

## 2. AI-Native Rules (spec §17.6.4)

Every OMNISYS API MUST be:

- **Discoverable** — `omni inspect` reports every function's type and declared
  effects from the registry.
- **Typed** — every signature is explicit; no `any` without a documented reason.
- **Structurally inspectable** — parameters, return types, effects,
  dependencies, and lifecycle are machine-readable.
- **Deterministic where appropriate** — same inputs, same results.
- **Easy to test and diagnose** — no undocumented conventions; failures are
  structured `omni.diagnostic` objects.
- **Explicit** — required capabilities, I/O types, side effects, dependencies,
  lifecycle, and errors are declared, never implied.

## 3. The Three-Audience Lens

Every design decision is weighed against three audiences (spec §7 history):

| Audience | The API must… |
|----------|---------------|
| **AI agents** | be greppable, local, explicit; one way to do each thing; checkable by one command |
| **Learners** | read like plain library calls; nothing new to memorize |
| **Devs** | feel familiar; offer escape hatches when the portable core is not enough |

## 4. Capability Honesty

- Functions that touch the world declare it: `uses network`, `reads filesystem`,
  `writes database`, `uses GPU`, `uses secrets`, `uses process`, …
- A `pure` function is guaranteed pure — the compiler enforces it.
- Platform differences are capabilities, not silent behavior.

## 5. Portable Core + Escapes

- The portable core is the default API surface, identical on every backend.
- Escapes are named, documented, capability-declared, and never the default.

## 6. Error Model

- Errors are values (`Result`/`Error` from `core`), never bare host exceptions.
- Structured context (message, code, context map) travels with the error.
- See `../omnisys/core/README.md` and the `error` submodule.

## 7. Registry as Contract

The registry (`omni_compiler/omnisys_registry.py`) is the compiled form of
these principles: every function's type and effects are recorded there, so the
principles are **enforced by the compiler**, not just documented.