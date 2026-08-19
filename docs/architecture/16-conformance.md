# OMNISYS Cross-Backend Conformance Model

**Deliverable §14Q.** How identical behavior across backends is defined,
tested, and guaranteed.

---

## 1. The Rule

The behavior of every feature — language and OMNISYS module — is defined by
the spec and MUST be identical across all engines. Any difference is a bug
(spec §14). The spec is the authority; engines are implementations.

Conformance is **tested**, not assumed (spec §5 of the history): the JS, C,
Rust, and WASM lanes all consume the same OMNI MIR, and the conformance suite
runs identical inputs through each backend and asserts identical observable
behavior.

## 2. What "Identical" Means

- **Front-end identical by construction**: one parser, one name resolution,
  one type/effect checker, one MIR producer. Any program that fails the
  front-end fails everywhere.
- **Observable behavior identical**: `show` output, return values, effect
  enforcement, diagnostic codes, symbol records.
- **Determinism per fixed backend**: same inputs + same tick count → same
  state. Not bit-identical across backends — float rounding may differ
  between C and JS (spec §13.5). The spec says this out loud.

## 3. The Conformance Suite

`tests/conformance/` holds cross-backend fixtures and tests:

- valid fixtures (basic, functions with effects, loops and lists, …),
- invalid fixtures for every error class (missing network declaration, pure
  with effects, …),
- cross-backend tests that compile the same `.omni` to JS/C/Rust/WASM and
  compare observable results.

The v1.0 conformance suite passed 100%; each v6 module adds a conformance
fixture to the suite.

## 4. Capability Gating as Conformance

Per-backend capability provision (spec §8.3) is part of conformance: a program
that declares `uses process` compiles for native and fails cleanly (with a fix)
for the browser — deterministically, at compile time, never at runtime.

## 5. The OMNISYS Layer

- The registry is the single contract all backends check against.
- Module READMEs document the portable surface; backend-specific escapes are
  declared capabilities, so portability decisions are explicit.
- Every package ships conformance tests that run the registry contract against
  its implementation.

## 6. Gates

- Cross-backend conformance suite green on every push (CI).
- Deterministic batching snapshot test (JS emitter).
- Effect soundness property tests (no pure function transitively calls an
  effectful one).

*See also:* [`03-backend-matrix.md`](03-backend-matrix.md),
[`19-quality-gates.md`](19-quality-gates.md).