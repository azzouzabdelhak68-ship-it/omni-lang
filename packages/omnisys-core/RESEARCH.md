# OMNISYS.core — Research & Design Notes (v6 Phase 1)

Research gate for the **core** module (spec §17.8, `docs/architecture/19-quality-gates.md` §6).
This document studies the relevant ecosystems and records the design decisions for the
Python reference implementation before it was written.

---

## 1. Purpose of the module

`core` is the implicit root namespace exported by `import OMNISYS` (no separate sub-import).
It is the vocabulary every other OMNISYS module builds on: Option/Result wrappers,
math helpers, length helpers, `type_of`, and the `panic` abort. Per `OMNI_SPEC.md` §17.1,
`core` subsumes `collections`, `serde`, and `error` as *internal* submodules — they are
shipped as separate packages in this monorepo but are never separate top-level imports.

---

## 2. Studied ecosystems

| Ecosystem | What it contributes |
|-----------|---------------------|
| Rust `Option<T>` / `Result<T, E>` | The tagged-union wrapper pattern (`Some`/`None`, `Ok`/`Err`) that became the Omni `Option`/`Result` API. |
| Haskell `Maybe` / `Either` | The pure-functional roots: constructors, pattern matching, total functions. |
| JS `typeof` + `undefined`/`null` | The historical source of `type_of` and of `length` returning 0 for missing values. |
| Python `math` / builtins | The host semantics we must adapt from (e.g. `round`'s banker's rounding vs JS `Math.round`). |

---

## 3. The §17.3 eleven questions

1. **What problem is it solving?** A tiny, dependency-free, portable vocabulary every
   OMNISYS module needs, available everywhere without ceremony.
2. **Which concepts survived?** Tagged Option/Result (JSON-friendly unions), panic
   (abort), identity, scalar math, length.
3. **Which exist due to historical constraints?** `typeof`'s inconsistent answers
   ("object" for null, "object" for arrays) — replaced by a clean vocabulary.
4. **Which APIs are awkward due to the host language?** JS `Math.round` differs from
   Python `round`; Python `bool` is an `int` subclass; JS arrays vs Python lists.
5. **Which abstractions are hard for AI agents?** None at this layer; the whole point is
   greppable, inspectable, total functions with one obvious behavior.
6. **Which concepts become first-class Omni concepts?** Option/Result/Error as tagged
   values, `panic` as a capability-free abort.
7. **Which remain libraries?** Everything else (math beyond the 7 helpers, random, etc.).
8. **Which map to the effect/capability system?** None — `core` is pure by construction.
9. **What belongs in the portable semantic layer?** The entire module.
10. **What must remain backend-specific?** Nothing in `core`; even panic is portable.
11. **What is the escape hatch?** `PanicError` (Python) / `Error` (JS) is catchable by
    host code; backends may map it to their native abort.

---

## 4. Strengths / weaknesses of the ecosystems studied

- **Rust**: `Option`/`Result` are excellent and total. But they live in `std`, are
  monadic, and require match — heavier than Omni needs.
- **Haskell**: purity is the gold standard but the syntax is not AI-greppable.
- **JS**: universal but `typeof` is a trap (`typeof null === 'object'`), `Math.round`
  is half-away-from-zero, and errors are values only by convention.
- **Python**: expressive and introspectable, but `round` (banker's), `bool ⊂ int`,
  and bare exceptions everywhere need a portable wrapper.

---

## 5. Performance model

All functions are O(1) (option/result wrap, math, length). `length` is O(n) for
str/list/dict. No allocation beyond the tagged dicts. This module is hot-path trivial.

## 6. Ergonomics

One function per operation, no methods, no classes required by callers. Named
`option`/`ok` (not `Some`/`Ok`) to match the registry and the JS lane exactly.

## 7. Type-system interaction

Registry signatures are `fn(...) -> ...`; the Python lane types everything explicitly
(mypy `--strict`). Tagged dicts are `dict[str, Any]` — deliberately un-precise at the
type level so JSON round-trips and cross-backend conformance stay trivial. A future
`TypedDict` refinement is possible but would complicate the generic value model.

## 8. Portability

`core` is pure Python stdlib and identical on every target. The tagged shapes are
JSON-serializable, so Option/Result flow through MIR/JSON without adapters.

## 9. Lifecycle / error model

No lifecycle. Two error channels: `panic` (programmer error, raises `PanicError`) and
the absence of Results-as-exceptions — `core` never throws for ordinary use.

## 10. AI usability

The whole module is 21 named functions, each with one behavior, fully discoverable via
`omni inspect` and this repo's registry. Deterministic and total (only `panic` aborts).

## 11. Interop requirements

Dict-tagged values interop with the JS lane (identical shapes), JSON serialization,
and any host that speaks the tagged-value contract.

---

## 12. Concrete design decisions for this Python implementation

1. **Tagged dicts, not dataclasses** — `{"tag":"some","value":v}` mirrors
   `omnisys/core.js` exactly, keeps JSON round-trips free, and makes cross-backend
   conformance tests mechanical.
2. **`round` is half-away-from-zero** — `math.floor(x + 0.5)` reproduces `Math.round`
   for all real inputs, including negatives (`round(-1.5) == -1`). Python's builtin
   `round` (banker's) is intentionally not used.
3. **`type_of` vocabulary** — `none`/`list`/`string`/`number`/`boolean`/`object`
   fixes JS `typeof`'s traps (`typeof null`), and `bool` is checked before `int`
   because `isinstance(True, int)` is True in Python.
4. **`min`/`max` are 2-ary** — the registry says `fn(Number, Number) -> Number`;
   the builtins' arbitrary-arity is not exposed.
5. **`sqrt` returns NaN for negatives** — mirrors `Math.sqrt(-1) === NaN` instead of
   raising `ValueError`, keeping total behavior.
6. **`panic` raises `PanicError`** (an `Exception` with `.message`) — a dedicated,
   catchable type that sibling packages import (`from omnisys_core import panic`).
7. **`length` returns 0 for non-collections** — mirrors JS `core.length`, including
   `length(None) == 0` (JS `null` → 0).
8. **`abs` returns float** — `math.fabs`; `abs(3) == 3.0`. Numeric equality with ints
   holds under `==`, so tests are unaffected.

### Deviations from the JS reference

| # | JS (`omnisys/core.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `core.some = core.option` alias | `some = option` alias, same object | Identical to JS (`core.some is core.option`) |
| 2 | `core.type_of` returns JS `typeof` strings | returns the portable vocabulary above | `typeof`'s "object" trap is a host artifact |
| 3 | `Math.abs` | `math.fabs` (float) | Python-native; `==`-equal for ints |
| 4 | `core.length` uses `Object.keys` | uses `len()` for str/list/dict | Same observable results |

---

## 13. Open questions

- Which prelude symbols are exported at the top level vs. behind `OMNISYS.core`?
  (The umbrella `import OMNISYS` currently exposes everything via `core`.)
- Should Option/Result become `TypedDict`s for stronger mypy checking at the cost of
  value-model generality?
- Should `PanicError` carry an error code for consistency with `omnisys_error`?