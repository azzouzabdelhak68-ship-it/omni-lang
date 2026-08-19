# RESULTS — Project 2.1 GUI / Personal Finance Dashboard

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE`
Date: 2026-08-17
Model: deepseek-v4-flash-free (opencode/deepseek-v4-flash-free)
Compiler: `python -m omni_compiler.cli` v0.1.0 (no `omni` binary on PATH)

---

## MODEL_RESULT

### Task completion status

| Criterion | Status | Evidence |
|---|---|---|
| `omni check source/finance_dashboard.omni` exits 0 | **PASS** (exit 0) | `omni check: OK` — see BENCHMARK_REASONING.md Entry 006 |
| `omni build ... --target js` produces runnable HTML | **PASS** (exit 0) | `omni build: wrote source\finance_dashboard.html`; artifact loads in headless Chromium with zero page errors |
| State updates propagate to visible output without reload (live-link) | **PASS** | First physical click and every `batchUpdate` action re-render the DOM without reload. **Multi-click navigation works**: the emitted runtime wires click handling via event delegation on `#app` (single `addEventListener`, `e.target.closest("[click]")` → `batchUpdate(fn)`), so listeners survive `innerHTML` re-renders. Verified precisely; see `test_real_click_updates_visible_output_without_reload` and `test_second_click_updates_visible_output_without_reload`. |
| All tests in `tests/` pass | **PASS** | `36 passed in 12.78s` (run from repo root, `-p no:cacheprovider`) |

Functional requirements: data model (structs + accessor functions) ✓, three views with
click navigation ✓, transaction entry form (rendered; input capture impossible) ◐,
input validation (amount/category/date) ✓, table + category/date-range filtering ✓,
reactive state (module-scope reactive store + one batched re-render per block) ✓,
empty state ✓, error state ✓.

### Execution efficiency

- Investigation probes: 3 (counter, structs/views, OMNISYS.ui) + browser harnesses.
- Deliverable build: ~10 compile/check iterations to reach exit 0 (driven by 4 real
  language discoveries below).
- Test suite: 36 tests, in-process compile + real-browser execution, ~13 s total.

### Invalid assumptions encountered (my own)

1. **Assumed `and`/`or` were usable in expressions.** They are lexed but the parser has no
   production for them → SyntaxError. Replaced with nested `if`.
2. **Assumed a `<style>` block could be embedded in the `UI:` block.** Every `{...}` in the
   template is converted to a `${...}` JS slot (no escape mechanism) → CSS braces became
   invalid JS. Replaced with inline `style` attributes + live-linked `display:{var}`.
3. **Assumed `-1` was a valid number literal.** Negative literals don't exist; `x is -1` is a
   SyntaxError. Restructured with `list_contains` and `0 - N`.
4. **Assumed parameterless-function arrow could be omitted only when no params.** Actually any
   function WITH params requires an explicit `-> Type`. Added `-> None`.
5. **Assumed every assigned variable is auto-hoisted as a module `let`.** Only TOP-LEVEL
   assignments are hoisted; variables first assigned inside `if`/`for` produced runtime
   `ReferenceError`. Pre-initialized nested-only variables in `when app starts:`.
6. **Assumed for-loop variables could access struct fields.** Loop vars are typed `Number` by
   the checker → `t.amount` fails check. Solved with accessor functions taking a
   `Transaction` parameter (the only field-access path that survives the checker).
7. **Assumed validation would surface in the DOM automatically.** My first `add_transaction`
    error branch returned before `recompute()`, so the error banner never showed. Fixed (and
    the test suite caught it — a genuine state-propagation bug).
8. **Assumed the emitted artifact supports a normal multi-step GUI session.** During the
    original session it did not (click model was single-shot after the first re-render);
    the emitted runtime has since been fixed to use event delegation on `#app`, so multi-step
    click sessions now work. The original single-shot behavior was recorded as the headline
    ecosystem finding at the time; the fix is noted under Backend findings.

---

## ECOSYSTEM_RESULT

Structured telemetry from observable investigation (all claims verified by probes,
compiler source inspection, and the browser smoke tests).

### API findings

- `OMNISYS.ui` (omnisys/ui.js + registry) is a **serialization-only** library: `element`,
  `text`, `button`, `row`, `column`, `input`, `render`/`to_html` build JSON element trees and
  render them to HTML *strings*. There is no DOM wiring, no event system, no reconciler.
- `OMNISYS.ui.state`/`state_get`/`state_set` are **mutable containers, not reactive
  primitives**: `state_set` mutates `{tag:"state", value}` and returns it; it never triggers a
  render. A slot `{omnisys.ui.state_get(s)}` only "updates" because the language-level
  `batchUpdate` re-evaluates every slot on re-render. No subscription model exists.
- `OMNISYS.ui.bind(element, slot, value)` merely sets an attribute in the JSON tree — inert
  for live binding.
- `OMNISYS.collections` list ops (`list_push`, `list_get`, `list_set`, `list_contains`,
  `list_index_of`) and `OMNISYS.core` (`length`, `round`) are usable and inline into the
  emitted HTML in dependency order. `list_get` PANICS (throws) on out-of-range — drove the
  safe bounds-checked row/breakdown unrolling.
- The registry declares all `ui` functions `pure`, so no capability declarations are needed;
  `screen`/`input` effects promised by docs/architecture/05-ui.md are **not enforced**.

### Language findings

- **Live-binding model**: the only reactive mechanism is the language-level `UI:` block.
  Module-scope `let` variables are the reactive store; `{expr}` slots are re-evaluated by a
  single `renderUI()` per top-level block (spec §9.4a batching is honored: one render after
  the whole action function). Verified with a visible `render_count` counter (render #1→#2).
- **Slot converter has no escape**: every `{` … `}` in the `UI:` template (and in text
  literals) becomes a JS `${…}` slot. Literal braces are impossible → no `<style>` blocks.
  Inline styles + live-linked attribute slots (`style="display:{var}"`) are the workaround.
  A `$` before a slot (`${balance_display}`) renders as a literal `$` + interpolation
  (`_js_template` adds another `$`) — useful and verified.
- **`and`/`or`/`not`**: tokenized, but no parser production → unusable. Nested `if` required.
- **Negative number literals**: unsupported; `-` is always the MINUS operator.
- **Function typing**: functions with params must declare `-> Type`; parameterless functions
  default to `None`.
- **Field access is checker-gated**: only bases whose resolved type is a declared custom type
  may access fields. For-loop vars are hard-typed `Number`, `list_get(...)` results resolve to
  `unknown` → direct `t.amount` fails E-TYPE-002. The **accessor-function pattern**
  (`fn tx_amount(tx: Transaction) -> Number: return tx.amount`) is the workaround and is not
  documented anywhere in the spec.
- **`let` hoisting is shallow**: only top-level assignments (function body / entry block) are
  hoisted; nested assignments are missed by the emitter → runtime ReferenceError.
- **String capabilities are minimal**: equality, lexicographic `<`/`>`/`<=`/`>=` (ISO dates
  compare correctly), interpolation, `core.length`, and `core.round(s)` numeric coercion
  (`NaN > 0` → false) — this made a real YYYY-MM-DD validation achievable without any
  split/charAt/toNumber primitive.
- Structs, named-arg construction (`Transaction(date=...)`, all fields required), lists,
  `for … in`, if/else, interpolation in text literals all work and emit clean JS.

### Compiler findings

- `check` does **not** validate the `UI:` template: neither `click="fn"` targets (spec §9.3
  mandates a compile-time error) nor slot references (undefined slot vars are runtime
  ReferenceErrors in the browser). The template is opaque to the checker.
- `build --target js` emits a single self-contained HTML with the OMNISYS runtime inlined.
  Targets c/rust/wasm are rejected for programs importing OMNISYS (E-BACKEND-001, JS-only lane).
- `run` and `inspect <sym>` work (exit 0, `omni.symbol` JSON). CLI diagnostics follow the
  `omni.diagnostic` v1.0 schema with fixes.

### Diagnostic findings

- Errors are machine-readable JSON (`E-SYNTAX-001`, `E-TYPE-002`, `E-EFFECT-003`…) with
  `fixes[]`, but syntax errors report location `{line:1, column:1}` and `span {0,0}` even when
  the real fault is at line 298 — **diagnostics give no location for syntax errors**, hurting
  agent usability (I had to manually hunt lines).
- Name/semantic errors do point at causes in `details` but carry the same generic span.

### Capability / Effect findings

- `uses X` is enforced (E-EFFECT-003) and `pure` is enforced (E-EFFECT-001). During the
  original session `reads`/`writes` were parsed but **not enforced**; enforcement has since
  been added — E-EFFECT-004 now fires for module data accessed via `reads`/`writes` without
  declaration (this run's source declares `reads transactions filter_category filter_from
  filter_to view error_message notice` on `recompute` accordingly).
- Effect analysis inherits declared `uses` of called user functions, but because OMNISYS UI
  functions are all registered `pure`, a program that "renders a screen" needs **no**
  `uses screen` declaration — the `screen`/`input` capability vocabulary from
  docs/architecture/05-ui.md is entirely unenforced in the JS lane.

### Backend findings

- JS lane is the reference OMNISYS backend; native targets reject OMNISYS imports.
- The JS emitter's click wiring was **incompatible with its own re-render strategy** during
  the original session: `bindClicks()` ran once after the entry block; `renderUI()` set
  `#app.innerHTML`, destroying the bound `onclick` handlers, so after the first state-changing
  click all further clicks were inert. The emitted runtime now uses **event delegation on
  `#app`** (single `addEventListener`, `e.target.closest("[click]")` → `batchUpdate(fn)`),
  which survives re-renders — multi-click sessions work (verified by
  `test_second_click_updates_visible_output_without_reload`). This was the single most
  consequential GUI limitation and it is resolved.
- No DOM read path exists (no way to read typed `<input>` values into the reactive store), so
  form submission cannot capture user input; `OMNISYS.ui.input` is a serialized attribute only.

### Positive Discoveries

- **Live-link batching is real and observable**: a whole action function mutating many state
  variables produces exactly ONE DOM re-render (render_count), per spec §9.4a.
- **View switching works** through live-linked inline `display` styles — no `<style>` needed.
- **The accessor-function pattern** makes struct-typed lists fully usable despite the checker's
  loop-var typing.
- **Fixed-capacity tables + safe bounds-checked slots** render variable-length data in the
  static template without panics, with a distinct empty state.
- **`core.round(s)` coercion** (`NaN > 0` is false) yields numeric-digit validation with no
  string-splitting primitive; ISO strings + lexicographic comparison give correct date ranges.
- **A `$` before a slot** renders as literal currency `$` (double-`$` template behavior).

### Proposed Changes

1. ~~`bindClicks()` must be re-invoked after every `renderUI()` (or use event delegation on
   `#app`) so re-renders don't kill interactions.~~ **RESOLVED** — the emitted runtime now uses
   event delegation on `#app`; multi-click sessions are verified. **Highest priority for the
   GUI model (fixed).**
2. Add an escape for literal braces in the `UI:` template / text literals (e.g. `\{\}`) so
   `<style>` blocks and CSS are possible; or special-case `{` preceded by `$`.
3. Teach the checker to parse the `UI:` template: validate `click="fn"` targets and slot
   references at compile time (spec §9.3 already mandates this).
4. Parse and hoist `let` for nested-block assignments (or declare all module vars from the
   entry block, which is the current workaround).
5. Support `-` in number literals and add `and`/`or`/`not` parse productions.
6. Add a DOM read path (form widgets) so user input can reach the reactive store; wire
   `OMNISYS.ui`'s element tree to the reconciler, or document it as serialization-only.
7. Emit real source locations in syntax-error diagnostics.

### Verification summary (what was and wasn't verified)

- **Verified**: `check` exit 0; `build --target js` exit 0 + runnable HTML; live-link for the
  first interaction and for every `batchUpdate` action; **multi-step click navigation** in a
  headless Chromium session with zero page errors; all 36 pytest tests.
- **Not verified / impossible in the current model**: typed-input → state capture (no DOM read
  path exists; intrinsic to the current compiler, demonstrated and recorded rather than worked
  around). The multi-click limitation recorded in the original session has been fixed in the
  emitted runtime (event delegation) and re-verified.