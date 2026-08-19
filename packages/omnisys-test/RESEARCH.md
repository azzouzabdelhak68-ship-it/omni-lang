# OMNISYS.test — Research & Design Notes (v6 Phase 1)

Research gate for the Python reference implementation of `OMNISYS.test`
(§17.8 / `docs/architecture/19-quality-gates.md` §6), applied against
`docs/architecture/04-api-design-principles.md` §1 (the eleven §17.3
questions). The authoritative API contract is
`omni_compiler/omnisys_registry.py` (`OMNISYS_MODULES["test"]`); the semantic
reference is `omnisys/test.js`. This document studies the borrowed
ecosystems, answers the eleven questions, and records every concrete design
decision for the Python lane, including deviations from JS and why.

## 0. The module in one paragraph

`OMNISYS.test` is the test surface of the OMNISYS standard library. It is
the module a program imports when it wants to assert behaviour, run
deterministic property checks, and take micro-benchmarks — the three tools an
AI agent (or a human) needs to *verify a change without leaving the language*.
Unlike host testing frameworks, it is not a runner, not a discovery system,
and not a plugin host: it is six pure functions that emit structured
diagnostics (panics) on failure and numbers/booleans on success. Everything
else — test discovery, CI, reporting — belongs to the host harness that wraps
the compiled program.

Registry contract (`test` module, pure, deps `core` + `collections`):

| Function        | Type                          | Effect |
|-----------------|-------------------------------|--------|
| `assert_true`   | `fn(Boolean, Text) -> None`   | panic on falsy |
| `assert_eq`     | `fn(any, any) -> None`        | panic on canonical-JSON mismatch |
| `assert_throws` | `fn(fn) -> Boolean`           | true iff fn raises |
| `property`      | `fn(fn, Number) -> Boolean`   | deterministic LCG property run |
| `bench`         | `fn(fn, Number) -> Number`    | elapsed milliseconds |
| `fail`          | `fn(Text) -> None`            | unconditional panic |

## 1. The eleven questions (§17.3, §04-api-design-principles.md §1)

### 1.1 What problem is it solving?

Every backend needs the same minimal verification vocabulary: "this must
hold", "these two values must be equal", "this call must fail", "this
invariant must hold over a spread of inputs", "how fast is this". Host
languages have five different, mutually incompatible answers (pytest,
Jest, QuickCheck/proptest, Go `testing`, mutmut-style mutation). An Omni
program written once must be *verifiable once*, identically on every
backend. `OMNISYS.test` is the portable answer.

### 1.2 Which concepts survived because they're genuinely useful?

- **Truthy assertion with a message** (`assert_true`). The atomic building
  block; everything else reduces to it. Survives as-is.
- **Equality assertion** (`assert_eq`). Cross-language equality is
  treacherous (JS `===` vs Python `==` vs Go `DeepEqual`), so the module
  defines equality itself: canonical JSON text. This is the single most
  important survival decision — see §8.3.
- **"Calling this must throw"** (`assert_throws`). Exists in pytest
  (`pytest.raises`), Jest (`toThrow`), Go (`defer recover`). The concept is
  universal; the *host mechanism* is not. Survives as a function that takes
  a zero-arg callable and returns a boolean.
- **Property checking** (`property`). The QuickCheck idea — run a predicate
  over generated inputs, shrink, report the counterexample — survives, but
  *shrinking and generation strategy* do not (see §1.3, §9).
- **Benchmarking** (`bench`). Running a callable N times and returning wall
  time survives; statistical framing (median, p90, warmup, noise floors)
  does not — that belongs to the harness.

### 1.3 Which exist due to historical constraints?

- **Shrinking** (QuickCheck/proptest's signature feature). Shrinking exists
  because generators produce *arbitrary* inputs and you want the minimal
  counterexample. It couples the generator to a shrinking lattice and is
  the most complex part of proptest. For an AI-first language where the
  *caller supplies the predicate* and the sample space is a fixed 0–999 LCG,
  shrinking has nothing to shrink. Deferred — see Open Questions §10.1.
- **Test discovery / fixtures / parametrization** (pytest/Jest). These are
  runner concerns (filesystem walking, class hierarchies) that only make
  sense on a specific host. The registry deliberately keeps them out.
- **Mutation testing** (mutmut/stryker). Mutation testing is a *tooling*
  layer over a test suite, not an API surface. It survives only as a gate
  on the reference implementation itself (§19-quality-gates §2), never as an
  `OMNISYS.test` function.
- **`assert_throws` returning a *matched exception*** (pytest `raises` as a
  context manager; Jest matchers). The host idiom couples the assertion to a
  *type* matcher. The portable contract reduces it to a boolean — the
  compiler cannot carry host exception types across backends.

### 1.4 Which APIs are awkward due to host language?

- **`assert_true(cond, msg)`**. In pytest it is `assert cond, msg` (an
  *operator*, not a callable — impossible to call from a compiled program).
  In JS it is `if (!cond) throw`. The function form is the portable
  abstraction; the `msg` is second and optional, mirroring `assert_true`'s
  JS implementation.
- **`property(prop, samples)`**. In Rust proptest it is a *macro* +
  `ProptestConfig`; in JS it is a framework (`fast-check` with
  `fc.property(...).check()`); in Go it is `rapid.Check`. All three bake
  runner/config semantics into the call. The registry keeps only
  `(predicate, count)`.
- **`bench(fn, iterations)`**. JS `console.time`/`performance.now`,
  Python `timeit`, Go `testing.B` all differ in units and warmup. The module
  fixes the unit (ms) and the loop (N calls, no warmup).

### 1.5 Which abstractions are hard for AI agents?

- **Framework-specific assertion APIs**. An agent that writes `expect(x).toBe(y)`
  cannot run it on another backend. The agent needs *one* vocabulary that
  compiles everywhere; canonical-JSON equality is that vocabulary.
- **Shrinking feedback loops**. When a property fails, proptest's shrink
  trace is a rich *interactive* artifact. Agents cannot act on it unless it
  is a plain string. `property` therefore fails with a single flat panic
  containing the sample index and the value — directly actionable, greppable.
- **Test discovery and runners**. "Where do tests live? How do I run one?"
  is a harness question. The agent-facing contract is: *call the function,
  get a panic or a boolean/number*. This is the meta-benchmark surface for
  v7 project 1.5, so `property` and `bench` are deliberately callable from
  inside any Omni program.

### 1.6 Which concepts become first-class Omni concepts?

- **The panic as a test failure signal**. Omni already has `core.panic` for
  aborting a program; `OMNISYS.test` reuses it with a reserved message
  prefix (`test assertion failed: `). A test failure is a *panic* — the
  same structured, typed, checkable signal as any runtime abort. No new
  error concept is invented.
- **Canonical JSON as the equality oracle**. Equality is defined as
  "same canonical JSON text", making it backend-independent by construction
  (dict key order, tuple-vs-list, int-vs-float all collapse).
- **Determinism as a property of the runner**. `property` is *defined* to
  be reproducible: fixed seed, fixed sequence, shared with the JS lane.
- **Milliseconds as the time unit**. `bench` returns ms regardless of the
  host clock resolution available.

### 1.7 Which remain libraries?

- Test **runners** (pytest, Jest, Go `go test`), **fixtures**, **mock
  objects**, **coverage** (pytest-cov), **mutation** (mutmut). All stay as
  host tooling layered on top of compiled programs that use `OMNISYS.test`.
- **Property-generation strategies** (strategy libraries in hypothesis/
  fast-check/quickcheck). The predicate receives a plain integer sample;
  richer generators are a future *interop* concern (§10.1).

### 1.8 Which map to the effect/capability system?

- **None** — every `OMNISYS.test` function is declared `pure` in the
  registry. This is a deliberate and load-bearing choice: an assertion must
  be callable from a pure function, and the *test surface itself* must never
  silently do I/O. (Benchmarking is time-observation, not an effect; the
  declared capability vocabulary has no "clock" capability, so `bench`
  stays pure.) Consequence for the compiler: the effect checker must *not*
  flag `omnisys.test.bench` as `process`/`network`/etc.

### 1.9 What belongs in the portable semantic layer?

All six functions. They are pure, deterministic (except `bench`'s wall-clock
measurement), total over their documented inputs, and their failure mode is
a panic with a stable message prefix. They are the smallest surface that
makes a compiled program *self-verifying*.

### 1.10 What must remain backend-specific?

- **Clock source** for `bench`: JS `Date.now()` vs Python
  `time.perf_counter()`. The *unit* (ms) and the *loop* (N calls) are
  portable; the clock is not.
- **Exception/catch mechanism** for `assert_throws`: Python `try/except`,
  JS `try/catch`, Go `recover`. Each lane uses its native mechanism; the
  *boolean result* is portable.
- **Test discovery and reporting** for the harness (JUnit XML, TAP, CI
  integrations) — never part of the module.

### 1.11 What is the escape hatch?

`assert_throws(fn)` is the escape hatch: anything the six functions cannot
express — mock verification, complex stateful checks, comparing host-native
objects — can be wrapped in a callable that raises on failure, and the
module will report it as a passing/failing assertion. In addition,
`assert_true` accepts an arbitrary user message, so any predicate with a
human-readable failure note is expressible.

## 2. Studied ecosystems

### 2.1 Python pytest

- **Strengths**: mature; `assert` rewriting gives readable failures;
  `pytest.raises` as context manager; deep plugin ecosystem; fixtures.
- **Weaknesses (for Omni)**: assertions are Python *syntax*, not callables;
  discovery depends on filesystem conventions and `__init__.py` layout;
  framework is 100k+ lines — untransportable.
- **Relevant borrowed idea**: the diagnostic message format (expected vs
  got) feeds `assert_eq`'s panic text.
- **Error model**: `AssertionError` vs collected reports vs plugin hooks —
  three different failure channels. Omni collapses to one: panic.

### 2.2 Rust proptest (and QuickCheck lineage)

- **Strengths**: shrinking, strategy combinators, `proptest!` macro ergonomics,
  deterministic testcases with a configurable RNG seed.
- **Weaknesses**: macro/derive ceremony; shrinking adds a lattice that is
  only worthwhile for *generated* inputs; config structs pollute the call
  site.
- **Relevant borrowed idea**: *deterministic seeded RNG* so a failing run
  can be replayed byte-for-byte. This is the direct ancestor of the LCG
  decision in §8.4.

### 2.3 JavaScript Jest and fast-check (QuickCheck-style)

- **Strengths**: `expect(...).toThrow()` matcher readability; fast-check's
  `fc.property` composes generators with a `seed` for reproducibility.
- **Weaknesses**: matcher chaining is a *host DSL* (method chains, not
  functions); asynchronous test lifecycles (`done`, promises) leak into the
  API.
- **Relevant borrowed idea**: the `omnisys/test.js` reference itself, whose
  semantics we mirror exactly (see §8). JS `Date.now()` → ms is the bench
  unit source.

### 2.4 Go testing

- **Strengths**: `t.Error`/`t.Fail` separate *fail* from *abort*; `go test`
  runs parallel subtests; table-driven tests are idiomatic.
- **Weaknesses**: `testing.T` is an object threaded through every function —
  a host-shaped abstraction that cannot cross backends; `defer recover` is
  verbose.
- **Relevant borrowed idea**: the *boolean* `assert_throws` result mirrors
  Go's "did it panic?" recover pattern, stripped of the `T` receiver.

### 2.5 Coverage and mutation tooling (pytest-cov, coverage.py, mutmut)

- **Strengths**: branch coverage quantifies exercised paths; mutation
  testing (mutmut) estimates test-suite strength by seeding faults and
  counting killed mutants. Both are *gates* (§19-quality-gates §2).
- **Weaknesses**: they are tooling, not API; they need a runner and a
  codebase to mutate.
- **Relevant decision**: the reference implementation is held to ≥95%
  branch coverage and (per repo policy) mutmut ≥90% — but mutmut is **not
  run** in this phase (per task instructions); it applies to the *whole*
  package later. The module's design keeps branches minimal precisely so
  the mutation bar is achievable.

## 3. Strengths and weaknesses of the chosen design

### Strengths

- **Six functions, zero framework.** Discovery, fixtures, runners, and
  reporters are excluded; the surface is greppable and checkable by one
  command (`omni inspect`).
- **One failure channel.** Panic with a fixed prefix; harnesses can
  classify test failures by string prefix, no host exception types needed.
- **Backend-neutral equality.** Canonical JSON makes `assert_eq` correct
  across key orderings and representational differences.
- **Deterministic property testing.** Same seed, same sequence on every
  backend, so a failing property is a reproducible artifact.

### Weaknesses (accepted)

- **No shrinking** — counterexamples are reported raw (index + value), not
  minimized.
- **`assert_eq` uses stringification (`default=str`) for non-serializable
  values**, so two distinct non-serializable objects can compare equal if
  their `repr`s collide (in practice: same object → equal, different objects
  → unequal). This is a pragmatic escape, documented in §8.3.
- **`bench` is wall-clock and noisy**; it is a smoke benchmark, not a
  statistical profiler.
- **The property sample space is a fixed 0–999 integer domain.** Richer
  generators are out of scope (Open Questions §10.1).

## 4. Performance

- `assert_true`/`fail`: O(1), no allocation beyond the message string.
- `assert_eq`: O(n) in the serialized size (two `json.dumps` passes with
  `sort_keys=True`, so worst case O(n log n) in dict-key sorting). This is
  the *price of portability*; a backend-native deep-equal would be faster
  but not identical across hosts. Documented and accepted.
- `property`: O(n) calls, one LCG step (two multiplies/adds + mask) per
  sample; `rand() % 1000` per sample. Trivially fast.
- `bench`: `time.perf_counter()` on Python, `Date.now()` on JS. Two clock
  reads plus N calls. The LCG and dumps dominate nothing; the measured
  function dominates, as intended.
- Mutation/coverage tooling impact: small module + minimal branches ⇒ the
  ≥95% branch bar is reachable with a compact test suite (§19 gates §1).

## 5. Ergonomics

- **Call shape is uniform**: every function takes plain values and a
  callable, and returns a plain value (`None`/`bool`/`float`). No context
  managers, no matchers, no fixtures.
- **Failure text is a complete sentence** that names the failing function:
  `test assertion failed: assert_eq: expected ... got ...`,
  `test assertion failed: property failed at sample 3 with value 867`.
- **`assert_true`'s `msg` is optional** with a stable default
  (`expected true`), matching JS `msg || "expected true"`.
- **`property` shadows the builtin** within the module — intentional, per
  the contract, and the module never needs the builtin.

## 6. Type-system interaction

- The registry records explicit signatures (`fn(Boolean, Text) -> None`, …)
  that the compiler type-checks against call sites. The Python lane mirrors
  them with full annotations under `mypy --strict`.
- `any` in the registry maps to `Any`; `Boolean`/`Number`/`Text` map to
  `bool`/`int`/`str`. `property`'s sample is an `int` (JS truncates floats
  via `| 0`; Python `int(...)` truncates floats identically for the
  documented range).
- `fail` is typed `-> NoReturn` in Python (it can never return), matching
  the registry's `fn(Text) -> None` in the *portable* type while refining
  the *implementation* type so callers know code after `fail` is dead.
- No generic polymorphism is needed; `Callable[[], Any]` / `Callable[[int], Any]`
  is sufficient and keeps the door open for future generator integration.

## 7. Portability, lifecycle/error model, interop

- **Portability**: stdlib only (`json`, `time`) plus the `omnisys_core`
  dependency — the *only* out-of-package import is `panic`. All logic is
  host-independent; `omnisys_collections` is a declared registry dependency
  (`js_deps`) but unused at runtime.
- **Lifecycle**: stateless. No module-level mutable state; the LCG state is
  closed over per `property` call, so concurrent or repeated calls are
  isolated and re-entrant.
- **Error model**: failures are `PanicError` (raised by `panic`), never
  returned as values, never swallowed. `assert_throws` is the sole place an
  exception is caught, and it converts it to a boolean — the module does
  not leak host exception types anywhere else.
- **Interop**: canonical JSON is the interop boundary; anything
  `json.dumps(..., default=str)` can render can be compared. The seam
  (`tests/conftest.py`) lets the package run against the documented contract
  before `omnisys_core` lands (see §8.7).

## 8. Concrete design decisions for THIS Python implementation

### 8.1 Panic-based assertion failures (mirror JS)

Every failure funnels through `fail(msg)` →

```python
panic('test assertion failed: ' + str(msg))
```

matching `core.panic('test assertion failed: ' + msg)` in `omnisys/test.js`.
Tests assert with `pytest.raises(omnisys_core.PanicError)`. The prefix is
the machine-readable contract: a harness can distinguish test failures from
other panics by prefix.

### 8.2 `fail` is `NoReturn`

Python cannot express "returns `None` but never actually returns" as richly
as the registry's `fn(Text) -> None`; `NoReturn` is the honest refinement,
and an `assert`-style unreachable guard (`raise AssertionError('unreachable')`)
keeps `mypy --strict` satisfied that control never falls off the end.

### 8.3 Canonical-JSON `assert_eq`

```python
actual_str = json.dumps(actual, sort_keys=True, default=str)
expected_str = json.dumps(expected, sort_keys=True, default=str)
if actual_str != expected_str:
    fail('assert_eq: expected ' + expected_str + ' got ' + actual_str)
```

- `sort_keys=True` makes dict key order irrelevant (JS `JSON.stringify` on
  insertion order would NOT; this is a deliberate, documented deviation that
  *improves* determinism — see §9).
- `default=str` stringifies non-serializable values so `assert_eq` is total
  over any Python object (mirrors the task spec; JS silently omits such
  members — a semantic gap we close, §9).
- The failure message contains **both** canonical forms, exactly matching
  the JS message layout.

### 8.4 Deterministic LCG so property runs are reproducible

JS:

```js
function lcg(seed) { let s = seed >>> 0; return function () {
  s = (s * 1664525 + 1013904223) >>> 0; return s; }; }
```

Python (identical sequence — verified against Node v24, first samples
`868, 467, 374, 157, 0`):

```python
state = seed & 0xFFFFFFFF
# per call:
state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
```

`>>> 0` (unsigned truncate to 32 bits) equals `& 0xFFFFFFFF` for the
non-negative intermediates here; JS float64 arithmetic is exact below 2^53,
so both lanes compute the same integer stream. `n = max(1, int(samples))`
mirrors `Math.max(1, samples | 0)`. `property` panics with the sample index
and the exact value on the first falsy result, then returns `True`.

### 8.5 `bench` semantics

`n = max(1, int(iterations))`; `time.perf_counter()` before and after N
calls; return `(end - start) * 1000.0` — a float in milliseconds, matching
the JS `Date.now()` difference (JS returns an integer ms; Python returns a
float for sub-millisecond precision; §9).

### 8.6 `assert_throws` semantics

Python `try/except Exception` around `fn()`; return `True` on any exception,
`False` otherwise. Mirrors JS `try { fn(); } catch (e) { return true; }`.
`PanicError` subclasses `Exception`, so a panicking callable also counts as
"throwing" — consistent with JS `catch` swallowing panics.

### 8.7 Dependency seam: `omnisys_core` is a placeholder today

The registry contract requires `from omnisys_core import panic`, but
`packages/omnisys-core` currently ships only `VERSION`. The test bootstrap
(`tests/conftest.py`) installs a reference `panic`/`PanicError` onto the
imported `omnisys_core` **only when absent**, so:

- the package runs against the documented contract immediately;
- when `omnisys_core` lands, the seam is inert (guarded by `hasattr`);
- `mypy` needs `# type: ignore[attr-defined]` on the import until the
  sibling publishes the symbol (recorded here as a temporary, tracked
  deviation).

## 9. Deviations from JS and why

| # | JS (`omnisys/test.js`) | Python (this package) | Why |
|---|------------------------|------------------------|-----|
| 1 | `assert_eq` compares `JSON.stringify` (insertion order) | `json.dumps(sort_keys=True)` | dict order is load-bearing in JS strings but an accident in Python; sorted keys make equality backend-independent and stable |
| 2 | `JSON.stringify` silently drops non-serializable members / `undefined` | `default=str` stringifies anything | keeps `assert_eq` total; avoids silently-equal objects that differ in the dropped members |
| 3 | `JSON.stringify(NaN/Infinity)` → `null` | `json.dumps(float('nan'))` → `"NaN"` | Python's `json` renders them literally; values are compared consistently within one lane, and the canonical form is still deterministic — cross-lane NaN equality is out of scope |
| 4 | `bench` returns integer ms (`Date.now()` diff) | float ms (`perf_counter() * 1000.0`) | `perf_counter` has sub-ms resolution; float preserves it, and the type (`Number`) is unchanged |
| 5 | `assert_throws` catches everything (`catch (e)`) | catches `Exception` (not `BaseException`) | `KeyboardInterrupt`/`SystemExit` are process-level signals Python should not swallow; all normal and panic exceptions are caught |
| 6 | `msg` may be `undefined` (`msg || 'expected true'`) | `msg: str | None = None` | same behaviour, expressed with an explicit optional parameter |
| 7 | `fail` always throws via `core.panic` | `fail -> NoReturn`, raises `PanicError` via `panic` | same observable behaviour; `NoReturn` is the honest Python typing |
| 8 | LCG uses `>>> 0` on float64 | `& 0xFFFFFFFF` on Python int | provably identical output for all intermediate values (verified by golden sequence) |

There are no *semantic* deviations in observable results for the documented
input space; the differences are representational (float vs int ms, string
sorting, catch scope) and strictly better-typed.

## 10. Open questions

### 10.1 Property-generation strategy integration

The predicate today receives `LCG() % 1000`. Future versions may want:

- a strategy/combinator API (`property_with(gen, prop)`), where `gen` is an
  Omni-level generator object rather than a host strategy library;
- shrinking of counterexamples (requires a lattice over the value space);
- richer domains (floats, strings, lists) generated *portably*.

Decision deferred: the fixed domain keeps `property` pure, deterministic,
and identical across backends; adding generators is a separate API-design
exercise with the same eleven-question process.

### 10.2 Coverage-instrumentation model

The reference implementation is gated by *branch coverage* (pytest-cov,
≥95%) and eventually *mutation coverage* (mutmut, ≥90% per §19 §2). Open
questions: how the whole monorepo aggregates per-package coverage for v6
special gates; whether mutation testing runs per-package with shared
`paths_to_mutate`; and how `omnisys_core`'s placeholder state is handled by
CI coverage of this package (the seam's injected `panic` is test-only and
excluded from the measured source).

### 10.3 Cross-lane conformance

`tests/test_conformance.py` locks the registry contract to `__all__` and to
the six recorded signatures. A future gate should run the same conformance
file against the JS lane (via Node) to prove the two lanes emit the same
observable behaviour — especially the LCG sequence and the exact panic
message strings.

## 11. Files

- `src/omnisys_test/__init__.py` — implementation (stdlib only; imports
  `panic` from `omnisys_core`).
- `tests/conftest.py` — dependency seam (§8.7).
- `tests/test_test.py` — unit tests for every function, plus golden LCG
  values.
- `tests/test_properties.py` — hypothesis invariants (reflexive
  `assert_eq`, key-order independence, property determinism, bench sanity).
- `tests/test_conformance.py` — registry contract lock.
- `README.md` — package summary and dependency notes.