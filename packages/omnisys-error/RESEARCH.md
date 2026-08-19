# OMNISYS.error — Research & Design Notes (v6 Phase 1)

Status: research gate for the Python reference implementation of `OMNISYS.error`
(`packages/omnisys-error`). Companion to the authoritative API contract in
`omni_compiler/omnisys_registry.py` (module `error`) and the JS reference
`omnisys/error.js`, whose semantics this package mirrors exactly.

---

## 1. What problem is it solving?

OmniScript programs need a way to represent *failures* that is:

- **Portable** — identical behavior on every backend (JS, Rust, C, WASM, Python
  lane). No backend-specific exception shapes leak into programs.
- **Structured** — a failure is not just a string; it has a *code* (stable,
  matchable identity), a *message* (human text), and a *context map* (arbitrary
  key/value diagnostics). AI agents and tools can consume these three channels
  separately.
- **Composable** — failures can be built, annotated with context as they
  propagate up a call stack, converted to plain data, and finally turned into a
  host exception only at a language boundary.
- **Distinguishable from normal values** — via an explicit `tag: "error"` so
  pattern matching and `is_error` are cheap and unambiguous.

The design question that drives everything: **should an error be a *value* you
pass around, or a *control-flow mechanism* you unwind through?** OmniScript's
answer, following spec §17.3 ("Do Not Wrap — Design Native") and §6 (Error
Model: "Errors are values (`Result`/`Error` from `core`), never bare host
exceptions"), is that the primary representation is an error **value**, with an
explicit, opt-in escape (`throw_error`) that converts a value into a host
exception for boundary crossing.

---

## 2. The eleven questions (spec §17.3)

Asked *before* the API was designed; answers for the `error` module.

1. **What problem is it solving?** Representing runtime failures as
   structured, portable, composable values, with codes + context, plus a
   deliberate escape hatch to host exceptions.

2. **Which concepts survived because they're genuinely useful?**
   - *Message* — universal, survives every ecosystem.
   - *Code / error kind* — survives because matching on strings is fragile;
     a stable machine identity is needed (Rust `Error::kind`, HTTP status
     analogs, `errno`).
   - *Context / structured payload* — survives (Rust `anyhow` context
     strings, Go error wrapping, Python exception `__context__`/`__cause__`,
     JS `cause`).
   - *Throwing at a boundary* — survives because sometimes you genuinely
     must abort control flow (top-level handlers, host interop).

3. **Which exist due to historical constraints?**
   - *Stack traces* — host-specific, expensive, non-portable; belongs to the
     *panic* path (`PanicError`), not the value path.
   - *Checked exceptions* (Java) — a compiler-enforced, fine-grained
     exception taxonomy that programs end up routing through catch-all
     handlers anyway; adds taxonomy friction without adding recoverable
     structure.
   - *Exception class hierarchies* (Python) — hundreds of `Exception`
     subclasses encode *where* an error happened, not *what to do*; a code +
     context map captures the actionable essence with one type.

4. **Which APIs are awkward due to host language?**
   - Python's `raise X(...)` — the only way to make a structured exception
     carry custom data is per-class attributes; we collapse this into one
     `OmniError` with `message`/`code`/`context`.
   - Go's `errors.New` returns a bare string-error with no identity; we
     always produce a tagged dict instead.
   - JS's `Error` — properties are tacked on by `Object.assign`; we make the
     fields first-class keys of a plain object.

5. **Which abstractions are hard for AI agents?**
   - Deep exception class taxonomies (what is `InterruptedError` vs
     `ConnectionResetError` for? and should an agent pick the "right" one?).
   - Stack-trace-dominant error handling (a trace tells *where*, not *what*).
   - Implicit error channels (unwrapped panics, silent `None`/`-1` sentinels,
     C `errno`). Agents cannot grep for failures that aren't values.

6. **Which concepts become first-class Omni concepts?**
   - `Error` is a first-class value type with shape
     `{tag: "error", message, code, context}`.
   - `throw_error` is a first-class *boundary* function — the one place a
     value becomes control flow.
   - `core.err` / `core.ok` (`Result`) composes on top: a `Result` *contains*
     an `Error` value. `OMNISYS.error` defines the payload that
     `Result::err` carries.

7. **Which remain libraries?**
   - `thiserror`-style derive macros, `anyhow`-style blanket `Error`
     impls — those are Rust host conveniences and stay out of the portable
     layer.
   - Python's exception hierarchy and traceback machinery remain available to
     backend implementers, never to OmniScript programs.

8. **Which map to the effect/capability system?**
   - Creating, inspecting, and transforming errors is `pure` (no effects —
     the registry declares zero effects for all nine functions).
   - Raising at a boundary (`throw_error`) is *still* declared `pure`: the
     effect system tracks I/O capabilities, not control flow. Raising an
     exception is deterministic and does not touch the world.
   - Error *recording* (logging, telemetry) would be effectful — that lives
     in `OMNISYS.observability`, not here.

9. **What belongs in the portable semantic layer?**
   - All nine functions: `error`, `error_code`, `error_message`,
     `error_code_of`, `error_with_context`, `error_has_context`,
     `error_to_dict`, `throw_error`, `is_error`. Each is expressible in every
     backend language with the same dict-shaped data.

10. **What must remain backend-specific?**
    - The *exception object* used by `throw_error` differs per backend (JS
      `Error` subclass with copied properties; Python `OmniError`). Its shape
      is backend-host, but its *fields* (`message`, `code`, `context`) are
      portable and match the value shape.
    - Stack traces, panic capture, debugger integration.

11. **What is the escape hatch?**
    - `throw_error` → an `OmniError`/host exception with the same
      `message`/`code`/`context` fields; `omnisys_core.panic` → `PanicError`
      for unrecoverable programmer errors. Both are explicit, named, and
      never the default way to handle a recoverable failure.

---

## 3. Ecosystem study

### 3.1 Rust — `thiserror` and `anyhow`

- **`thiserror`**: derive-macro error enums; each variant is a typed error
  with fields and a `#[error("...")]` format string. Errors are *values*
  (`Result<T, E>`), compiler-enforced at every call site.
- **`anyhow`**: `anyhow::Error` erases the concrete type; `Context` trait adds
  `context(...)`/`with_context(...)` — annotations are attached as the error
  bubbles up. `anyhow!` macros build ad-hoc errors.
- **Strengths**: exhaustive match on error kinds (thiserror); ergonomic
  annotation (anyhow); no hidden control flow — `?` is explicit.
- **Weaknesses**: two competing libraries (typed vs erased); `anyhow`
  discards structure unless strings are embedded; both are host-Rust-only and
  have no portable data form.
- **What we borrow**: the *context-annotation* idea (`error_with_context`) and
  the *value not control-flow* philosophy. We reject the enum taxonomy — a
  single tagged dict with a `code` string gives the same matching power with
  one portable type.

### 3.2 Go — `fmt.Errorf` with `%w`

- Go 1.13 `fmt.Errorf("wrap: %w", err)` creates a *chain*; `errors.Is` and
  `errors.As` unwrap it. Every wrapped layer is still just an `error`
  interface value.
- **Strengths**: errors are values; wrapping preserves the root cause;
  `Is`/`As` recover structure.
- **Weaknesses**: no code/kind field (sentinel vars are a workaround);
  message building is string formatting; no context map; unwrapping is O(n)
  and hand-rolled; no JSON data form.
- **What we borrow**: the *do not destroy the cause* principle — context is
  added by *copying* the error value forward, never mutating it in place, so
  the original stays intact. We reject string-only composition.

### 3.3 Python — exceptions

- `BaseException` hierarchy; every failure is a raised object; `try/except`
  is the only control flow; `raise X from Y` builds `__cause__` chains.
- **Strengths**: simple, mature, pervasive; tracebacks are useful in
  REPL/human debugging; exception chaining preserves causality.
- **Weaknesses**: raising is *control flow*, not a value — you cannot pass an
  exception as data without re-raising; the hierarchy over-models taxonomy;
  matching by class is coarse (need `except` clauses per class); a raised
  exception aborts the current frame (no `Result`); `BaseException` subclasses
  like `KeyboardInterrupt` mix control-flow signals into error space.
- **What we borrow**: `OmniError(Exception)` — Python programs still need a
  real exception at boundaries; `OmniError` carries `message`/`code`/`context`
  attributes so `except OmniError as e: e.code` works.

### 3.4 JavaScript — `Error`

- `new Error(msg)`; properties attached by hand or via `Object.assign`;
  `cause` option (ES2022) for chaining.
- **Strengths**: minimal; throwing is cheap to write; `Error` is just an
  object so it can carry arbitrary properties.
- **Weaknesses**: no structure by default; code identity is ad-hoc; the thrown
  shape is host-object, not JSON (stack, internal fields); catching by type
  requires subclassing.
- **What we borrow**: the *error is a plain object* insight (JS reference
  implementation literally returns `{tag, message, code, context}`) and
  `throw_error`'s `Object.assign(new Error(...), to_dict(...))` pattern —
  our `OmniError.__init__` does the same field-copying in Python.

### 3.5 Java — checked exceptions

- `throws` clauses force callers to handle or re-declare; taxonomy via class
  hierarchy.
- **Strengths**: the *compiler reminds you* an operation can fail — good
  hygiene for recoverable I/O errors.
- **Weaknesses**: the burden is on the taxonomy (which exception to throw?);
  checked exceptions push callers to catch-and-swallow; they do not compose
  as values; wrapper-exception spaghetti (`cause` chains of generic
  `RuntimeException`s).
- **What we reject**: compiler-enforced per-call-site exception routing. In
  OmniScript an error is just a value flowing through normal typing; the
  effect system (not an exception lattice) is what makes failure modes
  visible.

### 3.6 Result / error union types

- `Result<T, E>` (Rust, Haskell), `Either` (many MLs), TS discriminated
  unions (`{tag: "err", error}` | `{tag: "ok", value}`), Swift `throws`,
  Kotlin no-result.
- **Strengths**: exhaustiveness, no hidden control flow, composition via
  combinators (`map`, `and_then`); the tagged-dict union is JSON-serializable.
- **Weaknesses**: forced handling at every level can be verbose; mixing
  `Result` with exceptions requires a policy.
- **What we borrow**: `core.ok`/`core.err` build exactly such tagged unions;
  the *discriminated tag* idea — `"error"` tag is the discriminator, so
  `is_error` is a single field check.

---

## 4. Strengths and weaknesses of the chosen design

**Strengths**
- One portable data shape across all backends; JSON-ready by construction.
- `code` gives stable machine identity; `message` gives human text; `context`
  carries arbitrary diagnostics — three channels, one dict.
- Immutable-style composition: `error_with_context` copies, so values can be
  shared without aliasing bugs (the property tests lock this).
- The only "throwing" is a named, explicit function; everything else is a
  value.
- `OmniError` is a plain `Exception` subclass: standard `try/except`,
  `logging.exception`, and traceback tooling all work unchanged.

**Weaknesses**
- Structural typing (a dict) is not *nominally* enforced — a hand-rolled
  dict can masquerade as an error; `error_to_dict` normalization is the
  cure, and `is_error` is the guard.
- No stack trace on the *value* path (by design — traces belong to panic).
  Debugging a propagated value requires the context map to carry the
  breadcrumbs.
- `any` context values are untyped — deliberately, to stay portable; the
  trade-off is that a bad context value is only caught at use time.

---

## 5. Performance

- Value construction is two to four dict allocations; copying context on
  `error_with_context` is one dict copy per annotation. O(1) amortized.
- `is_error` is a single `dict.get` + comparison; no allocation.
- `error_message`/`error_code_of` are direct dict reads.
- `throw_error` allocates one exception object plus a context copy; the
  Python exception machinery is the only "heavy" path, and it is opt-in.
- Compared with exceptions thrown for *expected* failures, the value path is
  dramatically cheaper (no traceback capture, no unwinding). Compared with
  Rust `anyhow` (Box, vtable) it is comparable or cheaper (no allocation
  indirection).
- Hypothesis-generated workloads in `tests/test_properties.py` exercise the
  composition paths; no hot-path allocations beyond the documented copies.

---

## 6. Ergonomics

- Creating: `error("file not found")` and `error_code("file not found", "E-FS-404")`.
- Inspecting: `error_message(e)`, `error_code_of(e)`, `error_has_context(e, "path")`.
- Extending: `error_with_context(e, "path", "/tmp/x")` returns a new value —
  read as "error with this extra fact".
- Normalizing: `error_to_dict(e)` guarantees the canonical shape even for
  hand-built dicts.
- Boundaries: `throw_error(e)` — one call turns a value into a catchable
  `OmniError`.
- Tests read like the spec: unit tests map 1:1 to the registry contract,
  property tests lock invariants, conformance tests lock the public surface.

---

## 7. Type-system interaction (error-as-value vs exceptions)

- **Error-as-value** is the primary model: functions return (or compose with)
  `Error` values; typing flows normally; `core.err` wraps them into `Result`.
  No hidden control flow; the checker's `pure` guarantees hold.
- **Exceptions** are the *boundary* model only: `throw_error` is the single
  function that converts a value into control flow. The checker does not
  model Java-style checked exceptions; instead the *effect system* makes
  failure-prone capabilities explicit (`uses filesystem`, `uses network`), so
  failure *possibility* is visible at the capability level, not at the
  per-call exception level.
- `OmniError` is typed as an `Exception`; its fields are typed
  (`message: str`, `code: str`, `context: dict[str, Any]`). `is_error`
  accepts `object` and narrows via `isinstance`, matching JS truthiness
  without forcing callers to over-constrain.

---

## 8. Portability

- The value shape `{tag, message, code, context}` is expressible in JS
  (plain object), Rust (struct/enum + `serde`), C (struct), Python (dict),
  WASM (passable as data). The same nine-function API compiles everywhere.
- `throw_error` is the only backend-specific seam, and it is intentionally
  thin: field-for-field copy into a host exception.
- No use of host-only features (Python `traceback`, JS stack capture) on the
  value path.

---

## 9. Lifecycle / error model

An error's lifecycle in OmniScript:

1. **Born**: `error(...)` or `error_code(...)` — a fresh tagged dict.
2. **Grows**: `error_with_context(...)` adds diagnostics as it propagates
   (the `anyhow` / `fmt.Errorf %w` role, but copying, never mutating).
3. **Inspected**: `error_message` / `error_code_of` / `error_has_context`.
4. **Serialized**: `error_to_dict` yields the canonical JSON-friendly map
   (for logs, `observability`, AI tooling, cross-process).
5. **Terminates as a value**: composed into `core.err` → `Result`, matched on
   by pattern matching, returned, stored.
6. **Terminates as control flow**: `throw_error` → `OmniError`, caught by the
   host.

`PanicError` (`omnisys_core.panic`) is deliberately *outside* this lifecycle:
it represents a programmer error (invariant violation) that should never be
caught and has no code/context contract — only a message. Runtime errors get
the structured lifecycle; programmer errors get the loud abort.

---

## 10. AI usability

- **Structured and machine-readable**: an error is a dict with three
  well-defined fields. An agent can `error_code_of`, branch on code, read
  `context["file"]`, and pass the whole thing to `observability.log` without
  parsing prose.
- **Greppable and discoverable**: `omni inspect` reports all nine functions
  with signatures and `pure` effects from the registry; `is_error` and
  `error_to_dict` give agents one-command verification hooks.
- **One way to do it**: there is exactly one constructor, one accessor set,
  one way to throw. No taxonomy to memorize (unlike Python's exception
  hierarchy or Java's checked exceptions).
- **Deterministic**: pure functions, same input → same output; property tests
  prove round-trips and idempotence, so an agent can rely on the invariants
  (e.g., `error_to_dict(error_to_dict(e)) == error_to_dict(e)`).
- **Testable by one command**: `pytest packages/omnisys-error/tests` covers
  unit, property, and conformance suites.

---

## 11. Interop

- With `omnisys_core`: `core.err(error_value)` wraps an error into a `Result`;
  `core.panic` provides the unrecoverable sibling. `error` module depends on
  `core` per the registry (`js_deps = ("core",)`).
- With `omnisys_serde`: `error_to_dict` produces a value `json_encode` can
  serialize directly.
- With `omnisys_observability`: log/metric functions accept the map form.
- With the JS lane: the Python dict *is* the JS object — same keys, same
  values, same defaults (`"E-OMNI"`), so cross-backend error payloads are
  byte-identical after JSON round-trip.
- With host Python: `OmniError` is a normal `Exception`; third-party code can
  `except OmniError` and read `.code`.

---

## 12. Concrete design decisions for THIS Python implementation

1. **Dict-tagged error values for parity.** Errors are `dict[str, Any]` with
   `"tag": "error"`. Rationale: exact semantic parity with the JS reference
   (which returns plain objects), JSON-ready, no dataclass overhead, and
   `is_error` stays a single field check. A `Error` type alias documents the
   shape for static analysis.

2. **`OmniError` for `throw_error`.** One exception class carrying
   `message`, `code`, and `context` attributes; `__str__` returns `message`.
   This mirrors JS `Object.assign(new Error(msg), error_to_dict(err))` — the
   thrown object has the same three fields. Default `code` is `"E-OMNI"` for
   consistency with `error()`. `context` defaults to `{}` (never `None`).

3. **Context is a dict.** `error_with_context` copies the incoming error
   shallowly, copies (or replaces) `context` with a fresh dict, then sets
   `context[key] = value`. The input is never mutated; prior context is
   preserved; an existing key is overwritten. Non-dict `context` values are
   defensively replaced with `{}` so accessors never crash.

4. **Accessors are defensive.** `error_message` and `error_code_of` accept
   `object`, not only `Error`, because the JS reference handles arbitrary
   inputs (`err && err.message !== undefined ? ... : String(err)`). A
   non-dict falls back to `str(err)` (message) or `""` (code); a dict *with*
   a `"message"`/`"code"` key uses it, coerced with `str()` to guarantee the
   `Text` return type.

5. **`error_to_dict` normalizes through the accessors.** `message` and `code`
   go through `error_message`/`error_code_of` so even malformed inputs
   produce a canonical dict; `context` falls back to `{}`.

6. **`PanicError` vs `OmniError`.** Separate concerns: `PanicError` (from
   `omnisys_core`, a future sibling of this package) is for programmer
   errors — unrecoverable, message-only, not to be caught. `OmniError` is for
   recoverable, structured runtime errors with `code` + `context`.

7. **Pure, stdlib-only, fully typed.** No third-party imports; `typing.Any`
   is the only import. All functions are typed for `mypy --strict`; every
   public function has a docstring; no comments beyond docstrings.

8. **Test strategy.** Unit tests (every function), Hypothesis property tests
   (idempotence, additivity, round-trips, non-mutation), and conformance tests
   that lock the public surface to the registry contract and assert the
   `("core",)` dependency and zero declared effects.

---

## 13. Deviations from the JS reference and why

| JS reference | Python implementation | Why |
|---|---|---|
| `err && err.message !== undefined ? err.message : String(err)` | `str(err["message"])` when a dict has `"message"`, else `str(err)` | Same observable behavior for well-formed values; Python `str()` on non-dicts; coerces to `str` to honor the `Text` return type. |
| `err && err.code !== undefined ? err.code : ""` | `str(err.get("code"))` when present, else `""` | Same fallback; `None` code treated as absent (JS `null !== undefined` would keep it); coercion guarantees `Text`. |
| `Object.assign({}, err)` then rebuild `context` | `dict(err)`, copy/replace `context` | Same shallow-copy semantics; explicit `dict` calls make the copy obvious. |
| `Object.assign(new Error(msg), error_to_dict(err))` | `raise OmniError(message=..., code=..., context=...)` | Field-for-field equivalent; Python classes use `__init__` instead of property-copy. `OmniError` also gains `code="E-OMNI"` default, matching `error()`. |
| Keys coerced with `String(key)` | keys used as-is | Registry types the key as `Text`; Python string keys are used directly. |
| `!!(x && x.tag === "error")` | `isinstance(x, dict) and x.get("tag") == "error"` | Equivalent; Python `isinstance` replaces JS truthiness on non-objects. |
| Everything tolerates `null`/`undefined` inputs | `object`-typed accessors fall back safely | Kept; the JS functions are total, and Python mirrors that. |

Net effect: for any *well-formed* error value the two implementations agree
exactly; for malformed or foreign inputs they agree on the same fallback
policy (`""`, `str(...)`, `{}`) with only cosmetic `str()` coercions.

---

## 14. Open questions

1. Should `OmniError` also expose a `tag = "error"` attribute so a caught
   exception can be re-serialized through `error_to_dict`? Currently out of
   scope; `error_to_dict` accepts dicts only. A future
   `error_from_exception` helper may want it.
2. Should `error_with_context` deep-copy context values, or is shallow copy
   (current) acceptable? Shallow matches JS and keeps `any` values as
   references; deep copy would break identity for objects passed in context.
3. Should context keys be coerced via `str()` for strict JS parity even
   though the registry types them as `Text`? Left as-is; revisit if a backend
   ever passes non-string keys.
4. Should a `PanicError` class be added to `omnisys_core` alongside
   `panic()`? The `error` module only documents the distinction; the core
   package decides when to implement it.
5. Is `error_to_dict` on a non-dict input (currently `str()` fallback for
   message) the right normalization? It matches the JS total-function spirit;
   a stricter design could raise. Documented decision: be total.
6. Should the default code `"E-OMNI"` be configurable per-backend? Kept as a
   constant for cross-backend parity; an `OMNISYS.error` customization point
   would break the "one way to do it" rule.

---

## 15. References

- `omni_compiler/omnisys_registry.py` — `OMNISYS_MODULES["error"]`, the
  authoritative API contract.
- `omnisys/error.js` — the JS reference implementation whose semantics this
  package mirrors.
- `docs/architecture/04-api-design-principles.md` — §1 (eleven questions),
  §6 (error model: errors are values).
- `docs/architecture/19-quality-gates.md` — §6 (research gate), §2 (test
  suites), §3 (tooling gates: mypy strict, ruff, ≥95% branch coverage).
- `README.md` — package overview and the `PanicError`/`OmniError`
  distinction.