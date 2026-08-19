# BENCHMARK_REASONING — Project 2.1 GUI / Personal Finance Dashboard

Run: RUN_001_DEEPSEEK_V4_FLASH_FREE
Date: 2026-08-17
Model: deepseek-v4-flash-free (opencode/deepseek-v4-flash-free)
Compiler: `python -m omni_compiler.cli` (no `omni` binary on PATH)

This file is a LIVE ledger. Entries are appended in real time as I investigate.
No retrospective polishing.

---

## Entry 001 — Initial setup & survey

Task: implement a personal finance dashboard in OmniScript per TASK.md.

Plan:
1. Survey repo: omnisys_registry.py, omnisys/ui.js, docs (language + omnisys), OMNI_SPEC.md.
2. Establish CLI behavior: check, run, build --target js, inspect, explain.
3. Probe minimal UI program with `UI:` block, live slots `{...}`, `click="..."`.
4. Build dashboard: data model (transactions), views (overview/list/breakdown), form validation,
   filtering, reactive live-links, empty/error states.
5. Write pytest suite (Python) that parses/executes/inspects the .omni source + emitted HTML.
6. Verify: check exit 0, build --target js produces runnable HTML, live-link behavior, pytest passes.

Initial hypotheses (to be VERIFIED, not assumed):
- H1: UI programs use `import OMNISYS.ui` plus a `UI:` block with `{expr}` live slots.
- H2: `click="handler"` wires DOM clicks to OmniScript handlers, and live slots update without reload.
- H3: OMNISYS.ui provides widgets: forms, inputs, tables, nav — or maybe NOT (TASK.md says "Missing: ... form widgets, tables, charts, reactive state primitives (unlocks with OMNISYS.ui)").
  Note: TASK.md is PARTIAL — the UI model may be limited. Discovery/limitation testing is the point.
- H4: Amounts/dates are plain numbers/strings; validation is hand-written.

Created:
- run dir: E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_2_APP_FOUNDATIONS\PROJECT_21_GUI_FINANCE_DASHBOARD\RUN_001_DEEPSEEK_V4_FLASH_FREE\
- subdirs: source/, tests/, probes/

---

## Entry 002 — Ecosystem survey findings

Inspected: omnisys_registry.py, omnisys/ui.js, omnisys/core.js, omnisys/collections.js,
docs/omnisys/ui/README.md, docs/architecture/05-ui.md, OMNI_SPEC.md §9/§4/§5/§6/Appendix A,
omni_compiler/{lexer,parser,mir,emitter,checker,cli}.py.

Discovered (documented facts):
1. OMNISYS.ui is a SERIALIZATION library only: element()/text()/button()/row()/column()/input()/
   bind()/state()/state_get()/state_set()/render() build JSON trees and render them to an HTML
   string. It has NO DOM wiring, NO event system, NO reactivity. `state_set` merely mutates a
   JSON value; nothing triggers re-render. The registry marks all ui fns `pure`.
2. The language-level `UI:` block is the ONLY live-binding mechanism: lexer captures raw HTML from
   `UI:` to a line containing `end` (regex `\n\s*end\b`); parser stores it as prog.ui_template;
   emitter turns it into a JS template literal where `{expr}` slots become `${expr}`.
3. JS emission model: `renderUI()` sets `#app`.innerHTML = template. `batchUpdate(fn)` = fn();
   renderUI(); = live-link batching per top-level block (spec §9.4a). The entry point
   (`when app starts:`) runs inside batchUpdate. Module-scope variables assigned in functions and
   the entry block are hoisted as `let name;` at module scope (they ARE the reactive store).
4. Click model: `click="fn"` attribute; `bindClicks()` wires `el.onclick = () => batchUpdate(window[fn])`.
   Functions MUST be module-scope (window). bindClicks is called ONCE after the entry point.
5. **CRITICAL: re-render destroys click handlers.** renderUI() replaces #app.innerHTML, so the
   first state-changing click works (0→1), but after the re-render the button has a `click`
   attribute with NO bound onclick, so all subsequent clicks are dead. Verified by probe1:
   initial h1=0; after 1st click h1=1; after 2nd click h1=1; after 3rd click h1=1 (no page errors).
   Spec §9.3/§9.4 promise this, the JS emitter does not deliver it.
6. `check` does NOT validate UI template `click="fn"` targets (spec §9.3 says MUST be a compile-time
   error). Also does not validate slots reference defined variables — a bad slot is a runtime
   ReferenceError in the browser.
7. Logical operators `and`/`or`/`not` ARE lexed as keywords but the parser has NO handling for them
   (parse_comparison only handles is/>/</>=/<=). Using them in an expression → SyntaxError.
8. String ops are minimal: equality, length (OMNISYS.core.length works on strings), interpolation.
   No split, no charAt, no substring, no to-number. This constrains date validation.
9. `import OMNISYS` alone resolves to core module (registry resolve_import). Module deps are inlined
   in dependency order by the JS emitter (js_files_for).
10. Effect system: `uses X` clauses enforced; `reads`/`writes` accepted but NOT enforced; `pure`
    checked (E-EFFECT-001/003). UI functions are all pure so no capability declarations needed.
11. Builtin `join(list, sep)` special-cased by emitter to `(list).join(sep)`.
12. Structs: `type Name = { f: T, ... }`; construct with `Name(f=..., ...)` (named args, all fields
    required); field access `x.f`. MIR struct op → JS object literal.
13. Text literals support `{expr}` interpolation; emitter concatenates with +. Beware: a slot in a
    string literal is a JS expression, so it must be a defined identifier or call.
14. Environment: node v24.17.0, python 3.11.9, pytest 9.1.1, playwright with chromium browsers
    available. Headless browser smoke tests ARE possible.

PROBE 1 (probes/probe1_counter.omni) + smoke (probes/smoke1.py):
- check exit 0, build exit 0, emitted HTML matches the model above.
- Playwright: initial h1=0, click→1, click→1, click→1. Confirms finding #5.

---

## Entry 003 — Struct/loop probes and a CSS-mangling discovery

PROBE 2 (probes/probe2_structs.omni): included a `<style>` block. `check` FAILED first on
`and` usage (E-SYNTAX-001 "Expected ... got TokenType.AND ('and')") confirming `and` is lexed
but not parseable (finding #7). After replacing `and` with nested ifs, `check` passed.

BUT the emitted renderUI mangled the CSS: `.panel { padding: 8px; }` became
`.panel ${ padding: 8px; }` — `_js_template` greedily converts EVERY `{...}` into `${...}`,
including CSS blocks, producing invalid JS inside the template literal (script would not parse).
There is NO escape mechanism for literal `{` in the UI template OR in text literals (`_js_text`
does the same). CONCLUSION: `<style>` blocks and any CSS with braces are IMPOSSIBLE in the UI
block. Workaround: inline `style="..."` attributes (no braces) and live-linked display values
(`style="display:{var}"`).

PROBE 2b (probes/probe2b_structs.omni): same program without `<style>`, using live-linked
inline `display:` styles. check exit 0, build exit 0.
- Playwright smoke (smoke2.py): INITIAL shows Overview visible (display:block, balance=812.5),
  other panels display:none. Click 1 'Go to Transactions' → Overview hides, Transactions shows
  (display:block) — LIVE-LINK VIEW SWITCH WITHOUT RELOAD WORKS. Click 2 'Filter this month'
  → NO CHANGE. Confirms single-shot click model (finding #5) in a multi-button app.
- Verified: accessor-fn pattern `tx_amount(tx: Transaction)` allows field access on for-loop
  items (loop vars are typed Number by the checker, so direct `t.amount` would fail E-TYPE-002).
- Verified: `>=`/`<=` on ISO date strings works (lexicographic JS comparison).
- Verified: `when app starts:` may call functions defined later (functions defined before app
  block in the checker; JS function declarations hoist).

PROBE 3 (probes/probe3_omnisys_ui.omni): OMNISYS.ui state/bind/render inertness.
- check exit 0, build exit 0, run exit 0.
- Emitted JS confirms: slot `{omnisys.ui.state_get(s)}` → `${omnisys.ui.state_get(s)}`, and
  `state_set(s,42)` only mutates the JSON container. Click 'Bump' → slot showed 42 — but ONLY
  because the click wrapper batchUpdate() re-rendered; state_set itself never triggers a render.
- Confirms: OMNISYS.ui provides an inert serialization tree (no DOM wiring, no events) + state
  containers that act as mutable boxes read at render time. NO subscription/auto-render.

CLI notes: `run` (exit 0), `inspect <sym>` (exit 0, emits omni.symbol JSON).

---

## Entry 004 — Dashboard construction: three more compiler rules discovered

Writing source/finance_dashboard.omni surfaced additional language rules (all verified
by `omni check`/runtime):

1. **Negative number literals do not exist.** `-1` lexes as MINUS + NUMBER; `x is -1` is a
   SyntaxError. Workaround: `0 - 10.0`, or restructure (`list_contains` instead of
   `list_index_of(...) is -1`).
2. **Functions WITH parameters require an explicit `-> ReturnType`.** `fn f(x: Text):` is a
   SyntaxError; must be `fn f(x: Text) -> None:`. Parameterless functions default to None.
3. **`let` hoisting only covers TOP-LEVEL assignments.** The JS emitter collects `let name;`
   only from assignments at the top level of function bodies / the entry block. A variable
   first assigned inside a nested `if`/`for` (e.g. `matches = true` inside a loop) is NOT
   hoisted → runtime `ReferenceError: matches is not defined`. Workaround: pre-initialize
   every nested-only variable in `when app starts:` (entry assignments ARE collected).
   Verified: `let` list lacked `matches`/`ci`; adding them to the entry fixed the app.
4. `omni check` on the dashboard: after fixes → `omni check: OK` exit 0. Build → exit 0.

Browser smoke (smoke2.py on the built dashboard artifact):
- INITIAL render: Overview visible, balance=$3481.7, 5 rows in the table (6th empty),
  breakdown Food 86.7 / Rent 800 / Utilities 95 / Income 2500, error+notice banners hidden,
  empty-state banner hidden, render #1. All correct.
- Click[0] (any nav button) → render #2 — LIVE-LINK RE-RENDER works without reload.
- Click[1+] → no change (single-shot click model, finding #5). Playwright also refused to
  click hidden buttons (buttons inside display:none panels) — harness artifact, not a bug.
- The `$` before a slot (`${balance_display}` in the template) renders as literal `$` +
  interpolation (`_js_template` adds another `$` → `$${...}` → `$` + expr). Verified: `$3481.7`.

NEXT: write tests/test_finance_dashboard.py (pytest) driving the compiled JS in the real
browser via `page.evaluate("batchUpdate(...)")`, plus one real-click live-link test and one
regression-marker test for the click-rebinding limitation.

---

## Entry 005 — Test suite construction and fixes

tests/test_finance_dashboard.py: 36 tests. Compiles the dashboard in-process
(tokenize/parse/analyze/mir/emit_js) → writes tests/_build/finance_dashboard.html, then
drives the REAL program in headless Chromium (playwright) via the exact click runtime path
`batchUpdate(function(){ ... })`, asserting module state AND rendered DOM.

Iteration 1: 19 passed / 17 failed. Failures were BOTH dashboard-logic and test-harness:
1. Dashboard bug: `add_transaction` error branch returned before `recompute()`, so
   `error_display` stayed "none" — the error banner NEVER became visible. FIXED: call
   `recompute()` in the error branch. This is a real state-propagation bug the tests caught.
2. Harness: subprocess `-o` target dir `tests/_build/` didn't exist → mkdir first.
3. Harness: parametrized validator test mis-unpacked the (page, errors) fixture.
4. Harness: wrong expectation for day "00" — `core.round("00")` = 0, `0 > 0` false, so
   is_digits returns false → "Date day must be numeric." (correct rejection, message order).

Iteration 2: 36/36 passed. Notable passing tests:
- `test_real_click_updates_visible_output_without_reload`: physical click on the emitted
  artifact switched views + render# 1→2 — LIVE-LINK DEMONSTRATED IN THE ARTIFACT.
- `test_known_limitation_second_click_is_inert`: pins the single-shot click model.
- `test_state_change_propagates_to_dom_without_reload`: batchUpdate path updates DOM.
- validators parametrized: amount/category/date cases.

## Entry 006 — Final verification (raw outputs)

From RUN_001 dir, cwd = run dir:
```
> python -m omni_compiler.cli check source/finance_dashboard.omni
omni check: OK � finance_dashboard.omni        EXIT=0
> python -m omni_compiler.cli build source/finance_dashboard.omni --target js
omni build: wrote source\finance_dashboard.html (target=js)   EXIT=0
```
Artifact bytes start 60 33 68 ("<!D") → UTF-8, no BOM. Source starts 35 32 102 ("# f") → no BOM.

From repo root E:\simualtion:
```
> python -m pytest OMNISCRIPT_AI_BENCHMARK\...\RUN_001_DEEPSEEK_V4_FLASH_FREE\tests\test_finance_dashboard.py -p no:cacheprovider -q
36 passed in 12.78s
```

Browser verification (probes/demo_verify.py on the artifact, headless Chromium):
1. INITIAL: balance=3481.7, render#1, Overview visible, 5 table rows, 4-category breakdown.
2. batchUpdate(go_transactions) → view=transactions, transactions_display=block (live-link).
3. valid add → balance=3581.2, total_count=6, error_message='', DOM shows Travel/2025-12-01/99.5.
4. invalid add → error_message set, error_display=block, DOM shows red error banner.
5. filter Food → visible_count=2, visible_total=86.7.
6. date range 2020 → visible_count=0, empty-state banner text in DOM.
7. REAL first click (fresh load) → breakdown, render#2.
8. second real click → inert (view stays breakdown). PAGE ERRORS: [] — all OK.

Not verified / verified-what-was-possible:
- Multi-interaction in-browser flows beyond the first click are IMPOSSIBLE with the current
  emitter (bindClicks once; re-render replaces #app). Verified by tests #7/#8 and probe1.
- True form input capture (typing into <input> → reactive store) is IMPOSSIBLE: no DOM read
  path in the language. The form is rendered; add/validation are driven by demo buttons.
  Documented in the artifact itself and in RESULTS.md.