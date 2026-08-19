# OMNISYS.graphics — Research & Design Notes (v6 Phase 3)

Research gate for the Python reference implementation of `OMNISYS.graphics`
(portable 2D canvas model + op recorder). Produced before implementation per
spec §17.8 and `docs/architecture/13-package-system.md` §7, using the eleven
questions from `docs/architecture/04-api-design-principles.md` §1 (spec §17.3
"Do Not Wrap — Design Native"). Architecture anchor:
`docs/architecture/07-graphics-gpu-scene.md` (a semantic rendering model over
platform backends; the effect system keeps every backend difference explicit).
The JS reference implementation (`omnisys/graphics.js`) and the registry
contract (`omni_compiler/omnisys_registry.py`, `OMNISYS_MODULES["graphics"]`,
deps `("core",)`) are the semantic authorities; this document records where
the Python lane mirrors them, where it deviates, and why.

Ecosystems studied: HTML5 Canvas 2D, SVG, Cairo, Skia. All four are host
drawing *engines*; OMNISYS.graphics borrows their primitive vocabulary
(`line`/`rect`/`circle`/`polygon`/`text`/`clear` + fill/stroke state) and
rejects their stateful, immediate-mode execution models in favor of a pure
recorded op list.

---

## 1. The eleven questions (§17.3)

### 1.1 What problem is it solving?

Give OmniScript a portable 2D drawing vocabulary: a canvas value, draw calls
that mutate it, and `render`/`to_json` that expose the drawing as a
deterministic, serializable op list. The same semantic model feeds HTML5
canvas, SVG, Cairo, or Skia as backend escapes
(`07-graphics-gpu-scene.md` §2: "serializable output for any backend").

### 1.2 Which concepts survived because they're genuinely useful?

- A canvas as a plain value holding a list of draw ops plus current
  `fillColor`/`strokeColor` state — every studied ecosystem has these
  concepts; recording them as data makes the model pure.
- The primitive vocabulary: `line`, `rect`, `circle`, `polygon`, `text`,
  `clear` — the union of what Canvas 2D, SVG, Cairo, and Skia can all draw.
- Color fallback: shapes inherit the current fill/stroke color when none is
  given (`color || canvas.fillColor`) — the context-state model every
  ecosystem shares.

### 1.3 Which exist due to historical constraints?

- Canvas 2D's immediate-mode state machine (`beginPath`/`moveTo`/`closePath`,
  `ctx.save`/`ctx.restore` stack, current transformation matrix) — pure
  recorder complexity with no value for a semantic model.
- SVG's XML/attribute syntax and its coordinate-system layering — the
  document format of a specific browser feature, not a semantic API.
- Cairo's C-level context (`cairo_t*`) and path-building call sequences —
  host-language artifacts.
- Skia's `SkCanvas`/`SkPaint`/`SkPath` object graph and reference-counted
  surface plumbing — implementation detail, not vocabulary.

### 1.4 Which APIs are awkward due to the host language?

- JS `color || canvas.strokeColor` treats `''`, `0`, `NaN`, `false`, `null`,
  `undefined` as falsy; Python `color or canvas['strokeColor']` treats `''`,
  `0`, `False`, `None` as falsy but `float('nan')` as truthy. For the
  contract-typed `Text` colors this only differs out of contract (§5, D2).
- JS `String(x)` renders `null` → `'null'`, `true` → `'true'`, `1.0` →
  `'1'`; Python `str(x)` renders `None` → `'None'`, `True` → `'True'`,
  `1.0` → `'1.0'`. Identical for `str` and `int` (§5, D1).
- JS `undefined` for an omitted color vs Python `None` — same role (§5, D3).
- JS has one `Number` float type; Python distinguishes `int`/`float`. Both
  lanes record the given coordinate verbatim (§5, D5).

### 1.5 Which abstractions are hard for AI agents?

- Immediate-mode state machines (`beginPath`, path builders, transform
  stacks) — invisible ordering constraints that property tests cannot pin.
- Backend-specific surface/context lifecycle (Skia `SkSurface` creation,
  Cairo surface types, canvas element acquisition) — pure overhead for a
  model that just wants a list of draw commands.
- Rasterization/paint engine options (antialiasing hints, compositing
  operators, gradient objects) — infinite option space, no semantic payoff.

### 1.6 Which concepts become first-class Omni concepts?

- **Canvas** as a plain Map: `{"tag": "canvas", "width": ..., "height": ...,
  "ops": [], "fillColor": None, "strokeColor": None}` — same literal syntax
  as any other OmniScript value; agents can construct, diff, and round-trip
  it with `serde`.
- **Ops** as plain Maps (`{"op": "line", "x1": ..., "color": ...}`) — a
  verifiable, machine-readable draw list.
- **The recorder discipline**: mutating draw calls return the SAME canvas
  (JS does `canvas.ops.push(...); return canvas`), so calls chain like host
  drawing code while every observable effect is recorded data.

### 1.7 Which remain libraries?

- Real rasterization: HTML5 canvas element APIs, SVG serialization, Cairo
  surfaces, Skia surfaces — all backend escapes behind the same op list
  (`07-graphics-gpu-scene.md` §2: the semantic model "feeds native renderers,
  WebGPU, and the `scene:` language block").
- Font metrics, text shaping, image decoding — engine concerns, not portable
  vocabulary.

### 1.8 Which map to the effect/capability system?

All eleven functions are `_pure` in the registry — zero declared effects.
`07-graphics-gpu-scene.md` §5 notes the `graphics` module "uses GPU"
conceptually (drawing eventually touches a GPU), but the *recorder* itself
touches nothing: it appends dicts. The `_pure`/`_fn` markers are capability
metadata only; this Python package implements every function as a plain
synchronous function. The conformance test locks the exact partition (all
`fn.effects == frozenset()`).

### 1.9 What belongs in the portable semantic layer?

- Canvas construction, op recording with exact op shapes, fill/stroke state,
  color fallback (`color or current`), `render` (copy of ops),
  `to_json` (tag + dims + copy of ops, no state leakage).

### 1.10 What must remain backend-specific?

- Rasterization engines (Canvas 2D, SVG, Cairo, Skia), paint/antialiasing
  options, text shaping, and any GPU integration. `07-graphics-gpu-scene.md`
  §6 carries the open questions (rendering-model scope, scene interchange
  format) for the backend lane.

### 1.11 What is the escape hatch?

- `render` returns the raw op list — any backend escape consumes exactly
  that; `to_json` returns the JSON-friendly shape for transport.
- Ops and colors are open values (`dict[str, Any]` in Python, plain dicts in
  JS), so backend specifics (fill rules, dash arrays, fonts) can ride along
  as ordinary recorded fields without touching the portable core.

---

## 2. Ecosystem survey

### 2.1 HTML5 Canvas 2D

- **Strengths:** the vocabulary OMNISYS.graphics borrows (the `lineTo`/`rect`/
  `arc`/`fillText` primitive set, `fillStyle`/`strokeStyle` state); it is the
  natural first browser escape.
- **Weaknesses:** immediate-mode state machine (`beginPath`, current path
  mutating under every call); `save`/`restore` stack; transform matrix;
  zero serialization story (a canvas element is a bitmap, not data).
- **Performance:** excellent GPU-backed rasterization; the recorder model
  does not compete with it — the recorder is O(1) per op and the engine
  rasterizes at the escape.
- **Portability:** browser-only.
- **Lesson adopted:** the primitive vocabulary and the fill/stroke state
  concept; reject the mutable path/state machinery in favor of recorded ops.

### 2.2 SVG

- **Strengths:** declarative document model (elements + attributes) — the
  closest existing system to a "serializable draw list"; `<path>`/`<rect>`/
  `<circle>`/`<polygon>`/`<text>` map one-to-one onto our ops.
- **Weaknesses:** XML syntax, viewBox/coordinate-system layering, style-vs-
  presentation-attribute duplication; not a programming API.
- **Performance:** DOM-tree processing; fine for static graphics, heavy for
  dynamic ones.
- **Portability:** a serialization format, portable by nature.
- **Lesson adopted:** the op list is effectively a generic SVG scene graph
  without SVG's syntax; an SVG serializer is a trivial future escape
  (`render` ops → `<rect>`/`<circle>`/… elements).

### 2.3 Cairo

- **Strengths:** the classic C drawing API (context + path + source); its
  `cairo_rectangle`/`cairo_arc`/`cairo_fill` primitives are the source of
  many later APIs' shapes.
- **Weaknesses:** C-level context object (`cairo_t*`), manual path sequences
  (`move_to`/`line_to`/`close_path`/`fill`), error-state inspection via
  `cairo_status`; no data model at all.
- **Performance:** excellent CPU rasterizer; again engine work, not recorder
  work.
- **Portability:** bindings everywhere (pycairo, etc.).
- **Lesson adopted:** confirms the primitive list and the current-source
  color model; rejects context-object mutation as a semantic API.

### 2.4 Skia

- **Strengths:** the modern engine behind Chrome/Flutter/Android; rich
  `SkCanvas`/`SkPaint`/`SkPath` model with the same primitive set.
- **Weaknesses:** heavyweight C++ object graph, reference-counted surfaces,
  device-specific types (`SkSurface` per backend); enormous API surface.
- **Performance:** state of the art; irrelevant to an in-process recorder.
- **Portability:** C++ library with many bindings.
- **Lesson adopted:** same vocabulary/state lesson; the `SkPaint`-style
  fill-vs-stroke color state maps to `fill`/`stroke` in our model.

---

## 3. Cross-cutting analysis

### 3.1 Strengths / weaknesses of the chosen design

**Strengths**

- Eleven functions, all pure, stdlib-only (no imports at all beyond
  `typing`): trivially portable and testable; the registry `js_deps =
  ("core",)` exists for the JS inliner, but the Python lane imports nothing
  (no panic conditions in `graphics.js`).
- The whole model is data: a canvas is a dict, every op is a dict, and
  `render`/`to_json` return verifiable lists. Deterministic, diffable,
  property-testable.
- O(1) per-op recording with no hidden copies; `render`/`to_json` copy only
  the op list (matching JS `.slice()`), not the op dicts.
- No failure paths anywhere: the module has zero branches for errors, so
  conformance (`_IMPURE = frozenset()`) and 100 % branch coverage are
  trivial to pin.

**Weaknesses**

- Nothing is actually drawn: no rasterization, no pixels, no backend. This
  is the intended trade-off (`07-graphics-gpu-scene.md` §2 — backends are
  escapes).
- The op list is unbounded (no max ops, no op-size limits) — the JS lane has
  the same property; backends may enforce their own limits.
- JS/Python falsiness and `String` vs `str` coercion differ on the out-of-
  contract corners (§5).

### 3.2 Performance

- Every draw call appends one dict: O(1) time, O(1) amortized space per op.
- `render` and `to_json` are O(n) in op count (a shallow list copy), matching
  JS `canvas.ops.slice()`. Op dicts are shared, exactly as in JS.
- `text` stringifies with C-accelerated `str`; no other allocation beyond the
  op dict itself.

### 3.3 Ergonomics

- Names read as plain verbs and match the JS lane exactly — one mental model
  for both backends.
- Mutating calls return the same canvas, so code reads like host drawing code:
  `line(canvas, 0, 0, 10, 10, 'red')` followed by `render(canvas)`.
- Colors are plain strings (`'#e11d48'`, `'red'`) with the `fill`/`stroke`
  conveniences for shared state — no color objects to construct.

### 3.4 Type-system interaction (dynamic vs static typing)

- Registry signatures use `fn(Canvas, Number, ...) -> Canvas`, `fn(Canvas) ->
  List`, `fn(Canvas) -> Map`; Python mirrors them with the private `Canvas`
  (`dict[str, Any]`) and `Number` (`int | float`) TypeAliases and `str`/
  `list[list[Number]]`/`list[Any]`.
- `Canvas`/`Number` are TypeAliases, deliberately *not* in `__all__` — the
  public surface is exactly the eleven registry names.
- `cast` bridges the untyped dict access (`canvas["ops"]`) to the typed
  `list[dict[str, Any]]`/`list[Any]` views required by `mypy --strict`
  (including `warn_return_any` on `render`/`to_json`).
- `color` is typed `str | None` — `None` plays JS `undefined`/`null` for the
  `color || current` fallback.

### 3.5 Portability

- Zero runtime dependencies (only `typing`, erased at runtime); runs on any
  CPython ≥3.11 with no install surface.
- Value shapes are plain JSON-friendly dicts: `serde.json_encode(canvas)`
  round-trips, and `to_json` is the canonical transport form.
- Behavior is platform-independent: op ordering, colors, and str/int
  coercion are locale-independent.

### 3.6 Lifecycle / error model

- No lifecycle: a canvas is born at `canvas(w, h)` and lives as long as its
  ops list; no open/close/destroy.
- No error model: `graphics.js` has no panic conditions and never throws for
  contract-conforming inputs, so the Python lane has no failure branches at
  all — pure recording all the way.
- No concurrency concerns: every function is synchronous and touches only the
  argument dict; two canvases never share state (ops lists are distinct).
  Thread safety is the same as any dict operation.

### 3.7 AI usability

- Eleven greppable names, one value shape (Canvas), six op shapes — a model
  can enumerate the whole module from memory.
- JSON-in/JSON-out: `to_json(canvas)` yields the exact shape a renderer or a
  diff test consumes; `render` yields the verifiable op list. An agent can
  generate a drawing, inspect its ops, and assert on them with no engine
  knowledge.
- Deterministic and pure: same inputs → same ops, so property tests and
  golden snapshots are exact.

### 3.8 Interop

- All values are JSON-friendly, so any drawing can be serialized via `serde`
  and transported by any backend escape.
- Cross-lane interop is the headline goal: the Python lane reproduces the JS
  value shapes and defaults exactly (deviations in §5), so a canvas built on
  one lane produces the identical `render`/`to_json` output on the other.
- Future backend escapes: an HTML5-canvas renderer consumes `ops` directly
  (the `ctx`-family calls map one-to-one); an SVG serializer emits
  `<rect>`/`<circle>`/`<polygon>`/`<text>` elements; a Cairo/Skia escape
  drives the same primitives from the same op list.

---

## 4. Concrete design decisions for THIS Python implementation

1. **`canvas(width, height)` mirrors JS exactly.** The value is `{"tag":
   "canvas", "width": w, "height": h, "ops": [], "fillColor": None,
   "strokeColor": None}` — byte-identical to the JS reference. Width/height
   are typed `Number` (`int | float`) per the registry.
2. **Colors are typed `str | None`.** JS color parameters are optional/falsy
   (`undefined` allowed); Python `None` plays that role. `clear`, `fill`,
   and `stroke` record/assign the color verbatim (no fallback), matching JS.
3. **`line`/`rect`/`circle`/`polygon`/`text` implement the JS fallback
   literally:** `color or canvas['strokeColor']` / `color or
   canvas['fillColor']`, reproducing JS `color || canvas.strokeColor` /
   `color || canvas.fillColor`. Python `''` and `None` are falsy exactly as
   JS `''`/`undefined`/`null` are, so fallback matches for all contract
   `Text` values.
4. **`text` stringifies with `str(content)`**, matching JS `String(content)`
   for `str`/`int` (and any JSON-friendly scalar except the §5 corners).
5. **`render` returns `canvas['ops'][:]`** — a shallow list copy, exactly
   JS `canvas.ops.slice()`; op dicts are shared, only the list is detached.
6. **`to_json` returns `{"tag": "canvas", "width": ..., "height": ...,
   "ops": canvas['ops'][:]}`** — JS's exact shape; fill/stroke state is
   deliberately not serialized.
7. **`__all__` is exactly the eleven registry names**; `Canvas`/`Number`
   TypeAliases are private.
8. **`cast` appears only where needed for `mypy --strict`** — on `ops`
   access, so `render`/`to_json` don't trip `warn_return_any` and the
   append sites are explicitly `list[dict[str, Any]]`.
9. **No `omnisys_core.panic` import.** `graphics.js` has zero panic
   conditions and uses no collection helpers, so `omnisys_core` is not
   needed despite the registry `js_deps = ("core",)`.
10. **Stdlib only** (nothing beyond `typing`, which is erased at runtime);
    the module can be copied into any Python environment.

---

## 5. Deviations from the JS reference

| # | JS (`omnisys/graphics.js`) | Python (`omnisys_graphics`) | Impact |
|---|---|---|---|
| D1 | `String(content)`: `String(null)` → `'null'`, `String(true)` → `'true'`, `String(1.0)` → `'1'` | `str(content)`: `str(None)` → `'None'`, `str(True)` → `'True'`, `str(1.0)` → `'1.0'` | `text` content renders differently for `None`/bools/float-with-zero-fraction; identical for `str` and `int` (the contract-typed `Text`/JSON cases). |
| D2 | `color || canvas.fillColor` treats `NaN`, `0`, `false` as falsy too | `color or canvas['fillColor']` treats `0`/`False` as falsy but `float('nan')` as truthy | Out of contract (`color` is typed `Text`); `''` and `None` fall back identically in both lanes. |
| D3 | Omitted color is `undefined` | Color parameters default to (are typed) `str \| None` | `None` plays `undefined`/`null`; observable behavior identical. |
| D4 | `canvas.ops.slice()` | `canvas['ops'][:]` | Same shallow-copy semantics: the list is detached, the op dicts are shared. |
| D5 | One `Number` float type (`1.0` and `1` are the same) | `Number = int \| float` distinguishes them | Coordinates are recorded verbatim either way; only matters if a caller round-trips the JSON and compares text (spec §13.5 sanctions float-rendering differences). |

Every deviation is documented and covered by either a unit test or an
explicit RESEARCH note; none affects contract-conforming `Text`/JSON usage.

---

## 6. Verification

All gates run from the repo root (`E:\simualtion`):

| Gate | Command | Result |
|---|---|---|
| Tests | `python -m pytest packages/omnisys-graphics/tests -q -W error` | **53 passed**, zero warnings |
| Coverage | `python -m pytest --cov=packages/omnisys-graphics/src --cov-branch --cov-report=term-missing packages/omnisys-graphics/tests -q` | **100% statement, 100% branch** (39 stmts, 0 miss, 0 branch parts) |
| Lint | `python -m ruff check packages/omnisys-graphics` | **All checks passed** |
| Format | `python -m ruff format --check packages/omnisys-graphics` | **4 files already formatted** |
| Types | `MYPYPATH=<all packages/src>; python -m mypy --strict packages/omnisys-graphics/src` | **Success: no issues found in 1 source file** |

Test coverage map: unit tests exercise every function, both branches of each
`color or current` fallback (truthy color and falsy `None`/`''`), and the
`render`/`to_json` copy semantics (result detachment both directions);
property tests pin canvas shape, exactly-one-op appends, op ordering, header
preservation, color fallback (`color or '#abc'`), `text` stringification,
and `render`/`to_json` isolation. The conformance test locks the eleven
registry names, their callability, their module origin, the exact `__all__`
set (`_ALLOWED_EXTRA = frozenset()`), and the all-pure effect partition
(`fn.effects == frozenset()` for all 11).

The research gate, the registry contract, and the JS reference together
determine every line of this implementation; there is no backend-specific
behavior hidden in the portable core.