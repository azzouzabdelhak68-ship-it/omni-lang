# OMNISYS.ui — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 (research before
implementation) and `docs/architecture/05-ui.md`. Grounded in the JS reference
`omnisys/ui.js` and the compiler registry `OMNISYS_MODULES["ui"]`.

## 1. Ecosystems studied

- **SwiftUI** — declarative `View` values; structural identity; environment
  propagation; state via `@State`/`@Binding`. Pattern kept: *the UI is a
  value* (here: a JSON element tree), re-renders are recomputations of that
  value, state is an explicit mutable cell (`state`/`state_get`/`state_set`).
- **WPF** — markup as a hierarchy of elements with attributes and children;
  data binding slots (`bind` mirrors WPF's `{Binding}` attached-property
  idea on a plain JSON tree). Pattern kept: attribute dictionaries +
  children lists as the universal element shape.
- **Qt** — layout containers (row/column ↔ HBox/VBox); widget trees; signal
  handlers attached to widgets (`button(action)` mirrors a clicked signal).
- **Web/HTML** — the reference render lane: elements serialize to an HTML
  string with escaping (XSS-safe), inline flexbox for layout.

## 2. What was adopted

- One element value shape `{"tag": "element", "kind", "attrs", "children"}`
  (JSON-friendly, machine-readable — the AI-native mandate).
- Escaping rule set from the web lane: `& < > "` in text and attribute
  values, whitelisted attributes only (`value`, `placeholder`, `class`, `id`).
- `bind` deep-copies via JSON round-trip (structural independence, no shared
  state between the original and the bound copy) — matches JS exactly,
  including dropping non-serializable `action` callbacks.
- Mutable `state` cell with `state_get`/`state_set`, returning the same value.

## 3. Strengths / weaknesses of the studied ecosystems

- SwiftUI: strongest *reactive* ergonomics; weakest portability (Apple-only).
- WPF: powerful binding but heavy, Windows-only.
- Qt: mature cross-platform; C++-centric type system, verbose for scripting.
- Web: universally portable, but the DOM is imperative/mutable underneath.

OMNISYS takes the portable *semantic* layer only: a value model that any
backend (SwiftUI/WPF/Qt/web/native) can render. No host widget is wrapped.

## 4. Performance

- Element trees are plain dicts/lists; `render` is a single tree walk
  (O(n)). HTML output is string concatenation — negligible cost for the
  reference lane. Deep-copy in `bind` is O(n) via JSON, matching JS.

## 5. Type-system interaction / portability

- Types are registry-level: `fn(Text, Map, List) -> Element` etc. Python
  typing uses `Element = dict[str, Any]` aliases; the checker vocabulary maps
  `Text→str`, `Map→dict`, `List→list`, `any→Any`, `Number→int|float`.
- Value shapes are JSON-serializable (except an optional `action` callback,
  which mirrors JS where functions live on the value but do not serialize).

## 6. Lifecycle / error / concurrency model

- UI values are immutable-by-convention; `state` is the single mutable cell
  (no hidden global state, no threads — matches the single-threaded script
  model of OmniScript).
- No runtime errors except host coercion (`str()` never throws); rendering a
  non-object node raises a host `AttributeError` (JS throws `TypeError`).

## 7. AI usability

- The whole API is value-in/value-out over JSON shapes: an agent can build,
  inspect, and serialize a UI without a runtime, and the render output is
  directly verifiable text.

## 8. Interop requirements

- Future escapes: a `screen` capability (native windowing) and an `input`
  capability (event wiring) per `docs/omnisys/ui/README.md`; both keep the
  element/state value model as the semantic contract.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/ui.js`) | Python (this package) | Reason |
|---|----------------------|-----------------------|--------|
| 1 | `JSON.stringify` drops `action` on deep copy | `_jsonable` drops callable dict entries | Same observable result |
| 2 | `String(content)` | `str(content)` | Same for str/int; `None→'None'` vs `'null'` (out-of-contract corner) |
| 3 | `render({})` throws (`undefined.children.map`) | `render({})` → `<div></div>` | Kind/children defaulting; documented tolerance |
| 4 | `node.kind || "div"` | `node.get('kind') or 'div'` | Same for `None`/missing |
| 5 | attribute coercion `attrs[key]` (any) | `_escape_html(value)` stringifies | Same for str/int |
| 6 | function-valued attrs survive `bind` untouched | callable attr values dropped by deep-copy | Matches `JSON.stringify` behavior (only functions dropped) |

## 10. Verification

- `python -m pytest packages/omnisys-ui/tests -q -W error` — 33 tests pass,
  zero warnings.
- Coverage: `packages/omnisys-ui/src` **100% branch**.
- `mypy --strict packages/omnisys-ui/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-ui` — clean.