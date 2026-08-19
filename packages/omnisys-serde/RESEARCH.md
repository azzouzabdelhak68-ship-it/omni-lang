# OMNISYS.serde — Research & Design Notes (v6 Phase 1)

Research gate for the Python reference implementation of `OMNISYS.serde`
(JSON, CSV, hex, base64, schema validation). Produced before implementation
per spec §17.8 and `docs/architecture/19-quality-gates.md` §6, using the
eleven questions from `docs/architecture/04-api-design-principles.md` §1
(which restates spec §17.3 "Do Not Wrap — Design Native").

Ecosystems studied: Python stdlib `json`, Rust serde / serde_json,
JSON Schema, Go `encoding/json`, MessagePack/CBOR/bincode (as future binary
formats), and Protocol Buffers / FlatBuffers (as schema-binary comparisons).
The JS reference implementation (`omnisys/serde.js`) is the semantic
authority; this document records where the Python lane mirrors it, where it
deviates, and why.

---

## 1. The eleven questions (§17.3)

### 1.1 What problem is it solving?

Structured data exchange across an OmniScript program's boundaries: turning
in-memory values into portable text (and back), plus a lightweight
schema-driven validation mechanism so AI agents and tooling can check that
untrusted or generated data matches an expected shape.

### 1.2 Which concepts survived because they're genuinely useful?

- A single universal text format (JSON) that every host ecosystem and every
  model already understands.
- A human-readable tabular format (CSV) with trivial ergonomics for flat
  data.
- Byte-oriented encodings (hex, base64) as the escape hatches for binary
  payloads inside a text-only language.
- Declarative, data-as-code validation (a dict schema) rather than
  imperative checks.

### 1.3 Which exist due to historical constraints?

- JSON's lack of comments, trailing commas, `undefined`, NaN/Infinity, and
  integer/float distinction (all host-JS artifacts that we do not re-export).
- CSV's total lack of an escaping standard (RFC 4180 is advisory; the JS
  reference does not implement quoting, so neither do we).
- base64's padding rules (`=`) and hex's odd-length ambiguity, both inherited
  from byte-encoding conventions, not from any OmniScript need.

### 1.4 Which APIs are awkward due to the host language?

- JS `JSON.stringify` escapes non-ASCII; Python `json.dumps` only does so when
  asked. We pick the readable behavior (`ensure_ascii=False`) for both lanes.
- JS `typeof` has no separate integer type and treats `bool` as distinct from
  `number`; Python's `bool` subclasses `int`. Our `number` check must exclude
  booleans explicitly.
- JS iterates UTF-16 code units; Python iterates code points. This forces the
  documented `to_hex` deviation for non-BMP text.
- JS coerces inputs (`String(x)`); Python does not. The Python lane types its
  parameters as `str` and does not coerce.

### 1.5 Which abstractions are hard for AI agents?

- JSON Schema (full draft) is enormous, with a huge keyword surface
  (`anyOf`, `$ref`, `patternProperties`, …). An AI agent cannot reliably
  remember or produce it. Our `schema_validate` keeps a tiny closed set of
  `type` names plus a recursive `fields` map — greppable, memorizable,
  checkable in one command.
- Go's `encoding/json` `struct` tags are type-level, not data-level, and
  therefore unusable for validating dynamically shaped values.
- serde's derive-macro model requires compile-time Rust types; it is the
  opposite of data-driven validation.

### 1.6 Which concepts become first-class Omni concepts?

- **Text** as the universal carrier: every function in this module is
  text-in/text-out (or value↔text), keeping the OmniScript type system tiny.
- **Map** as the schema format: a schema is just a value, so agents can
  generate, inspect, and round-trip schemas with `json_encode`/`json_decode`
  without any extra grammar.
- **Boolean result** from `schema_validate`: validation is a pure predicate,
  combinable with OmniScript `and`/`or`/`if`.

### 1.7 Which remain libraries?

- Full JSON Schema validation, TOML/YAML parsing, MessagePack/CBOR codecs,
  Protobuf/FlatBuffers compilation. These stay outside the portable core and
  are listed as open questions / future formats in §8.

### 1.8 Which map to the effect/capability system?

None. Every function is `pure` (no network, filesystem, database, GPU,
process, or secrets effects) — confirmed by the registry
`effects=frozenset()` for all nine entries and locked by the conformance
test `test_registry_functions_are_pure`.

### 1.9 What belongs in the portable semantic layer?

- Value→text and text→value for JSON and CSV.
- Byte-encoding of text via hex and base64.
- Recursive, dict-schema-driven validation with the closed type vocabulary.
- Exceptions-as-errors are *not* the portable error model (spec §17.4); see
  §6.3. The portable layer is the *raising* behavior; the OmniScript compiler
  surfaces those as structured `core` errors.

### 1.10 What must remain backend-specific?

- Host codec *performance* implementations (Rust serde, Go
  `encoding/json`, V8 JSON.stringify).
- Anything requiring compile-time type generation (serde derives, Protobuf
  `protoc`).
- Binary format negotiation, streaming parsers, and schema registries.

### 1.11 What is the escape hatch?

- `to_hex`/`from_hex` and `base64_encode`/`base64_decode` carry arbitrary
  bytes through any text-only pipeline.
- `json_encode`/`json_decode` carry arbitrary JSON-compatible values.
- `schema_validate` with `type: any` or an empty schema validates everything,
  so callers can opt out of checking without changing call shape.

---

## 2. Ecosystem survey

### 2.1 Python stdlib `json`

The Python lane's primary engine.

- **Strengths:** battle-tested; part of the stdlib (zero deps); C-accelerated
  (`_json`); exact round-trip for JSON-compatible values; deterministic
  output; handles all JSON types including nested and deeply recursive
  structures.
- **Weaknesses:** raises `JSONDecodeError`/`TypeError` instead of returning
  result values; `bool`/`int`/`float` nuances; no streaming by default;
  historically permissive (NaN/Infinity accepted by default — we keep
  `allow_nan` defaults but the language-level contract never produces them).
- **Performance:** O(n) scan-based parse with a fast C path; adequate for the
  AI-first workloads this module targets (small, schema-shaped messages).
- **Ergonomics:** best-in-class — `dumps`/`loads` are one-liners and the exact
  inverse of the JS `stringify`/`parse` shape, which keeps the two lanes
  symmetric.
- **Type-system interaction:** dynamic; any JSON-compatible Python value
  serializes, and `loads` returns untyped values — exactly the OmniScript
  model (`any`).
- **Portability:** every Python ≥3.5 ships it. Highest possible portability.
- **Error model:** exceptions (`JSONDecodeError` is a `ValueError`;
  `TypeError` for unserializable values).
- **AI usability:** the semantics are well-known to models; `ensure_ascii=False`
  produces human-readable output that models can diff and edit directly.

### 2.2 Rust serde / serde_json

The reference *data-model* architecture.

- **Strengths:** a single trait-based data model (`Serialize`/`Deserialize`)
  decouples formats (JSON, TOML, YAML, MessagePack, CBOR, bincode) from data
  types; zero-copy and format-agnostic; the ecosystem standard.
- **Weaknesses:** requires compile-time derive macros and static Rust types;
  no dynamic, data-driven validation; `Value` (untyped) exists but is
  awkward; two error paths (`Result`, `serde_json::Error`).
- **Performance:** among the fastest JSON parsers (manual SIMD in
  `simd-json`); irrelevant for our dynamic text pipeline.
- **Type-system interaction:** static, compile-time, dual (serialize and
  deserialize are separate traits) — the antithesis of OmniScript's dynamic
  `any`.
- **Portability:** Rust-only; forms no interoperability surface with the JS
  lane.
- **Lesson adopted:** a single *data model* (here: JSON-compatible Python
  values) shared by all future formats. If MessagePack/CBOR arrive (§8), they
  serialize the same values, exactly as serde's formats serialize the same
  types.

### 2.3 JSON Schema

- **Strengths:** the de-facto standard for data validation; rich vocabulary;
  machine-readable; tooling (generators, linters, editors).
- **Weaknesses:** enormous surface area (hundreds of keywords, `$ref`,
  formats, vocabularies); draft churn (2020-12 vs 2019-09 …); cross-implementer
  divergence; overkill for AI-authored data.
- **Performance:** schema compilation is expensive; validation is
  interpreter-bound.
- **Ergonomics:** poor for quick checks — writing a valid JSON Schema is a
  cognitive load for agents and learners alike.
- **Type-system interaction:** data-driven (schemas are documents), which we
  *do* adopt conceptually, but we reduce the vocabulary to the minimum the
  reference semantics need.
- **AI usability:** the main reason to skip full JSON Schema — models
  hallucinate keywords and mixing drafts silently changes meaning.
- **Interop:** a full `schema_validate` is intentionally *not* JSON Schema
  compatible. Conformance with JSON Schema is an open question (§8).

### 2.4 Go `encoding/json`

- **Strengths:** strong round-trip guarantees; `json.Number` opt-in; safe by
  construction for network use.
- **Weaknesses:** struct-tag driven — validation and mapping live in type
  definitions; no dynamic validation; `interface{}` (untyped) handling is
  clumsy; `-0.0`/integer-float edge cases.
- **Type-system interaction:** static types with runtime `interface{}`
  escape; map[string]interface{} mirrors our dynamic model but loses all
  static safety.
- **Performance:** decent; still C-backed or reflection-bound.
- **Lesson:** confirms that host-static-type lanes need an explicit dynamic
  value type (Go's `map[string]interface{}`, Python's `Any`, JS's `any`) to
  serve a dynamic language.

### 2.5 MessagePack / CBOR / bincode (future binary formats)

- **MessagePack:** JSON-like types, binary, compact; excellent library
  support; trivially maps onto the same data model; preserves int/float and
  map/array distinctions. Natural first future format.
- **CBOR:** RFC 8949; tagged types, streams, indefinite lengths; heavier spec;
  used in COSE/WebAuthn. Over-specified for our needs today.
- **bincode:** Rust-native, smallest footprint; not a data-exchange format
  (no self-describing structure); poor interop.
- **Decision:** none shipped now. MessagePack is the leading candidate (§8);
  all three confirm that a single serde-style data model (§2.2 lesson) is the
  right architecture to grow into.

### 2.6 Protocol Buffers / FlatBuffers (comparison)

- **Protocol Buffers:** schema-first, codegen-driven, binary, versioned
  fields. Strengths: compactness, cross-language, long-term stability.
  Weaknesses: schema files are a second grammar; no dynamic data without
  `Any`/`Struct` (which reintroduce JSON); requires `protoc` toolchains per
  backend — directly violates the "no codegen, portable core" rule.
- **FlatBuffers:** zero-copy, no parse step. Strengths: extreme read
  performance, mmap-friendly. Weaknesses: layout-dependent, write-twice,
  mutation-averse; totally unsuitable for a text-first AI language.
- **Lesson:** both are backend-specific escapes at best; the portable core
  stays text-based. Neither is a candidate for phase 1.

---

## 3. Cross-cutting analysis

### 3.1 Strengths / weaknesses of the chosen design

**Strengths**

- Nine functions, all pure, all stdlib — trivially portable and testable.
- JSON carries the full value model; hex/base64 carry bytes; CSV carries flat
  tables; `schema_validate` closes the loop for AI-generated data.
- Deterministic: identical inputs produce identical text on both lanes
  (modulo the two documented deviations in §7).
- Small, greppable surface — passes the discoverability rule
  (04-api-design-principles.md §2).

**Weaknesses**

- No CSV quoting/escaping (inherited from JS; `csv_encode` of a cell with a
  comma or newline does not round-trip).
- `schema_validate` is presence+type checking only — no value ranges, no
  pattern matching, no optional fields.
- Exceptions, not values (see §6.3): the Python lane raises; callers who need
  the `Result` error model must wrap.
- Binary formats are not yet supported.

### 3.2 Performance

- `json.dumps`/`json.loads` are C-accelerated; `base64` and `binascii.hexlify`
  are C-backed. All functions are O(n) in input size.
- No copying beyond what the semantics require; `csv_decode` builds one
  string list per row.
- For the target workload (small, schema-shaped AI messages) performance is
  a non-issue; measured headroom is orders of magnitude beyond typical
  message sizes. If it ever matters, the compiler can substitute
  backend-specific codecs behind the same registry contract (§1.10).

### 3.3 Ergonomics

- Function names read as plain verbs (`to_hex`, `from_hex`) — nothing to
  memorize for learners; they match the JS lane exactly, so one mental model
  covers both backends.
- Schemas are plain Maps — the same literal syntax an agent uses for data.
- `csv_encode([])` → `''` and `csv_decode('')` → `[]` are stable, boring
  edge cases (locked by tests).

### 3.4 Type-system interaction (dynamic vs static typing)

- OmniScript is dynamic; the registry signatures use `any`, `Text`, `List`,
  `Map`, `Boolean`, `Number`.
- Python mirrors this with `Any`, `str`, `list[list[Any]]`, and `bool`.
- The `number` check must special-case `bool` (Python `bool` ⊂ `int`); the
  `map` check must exclude `list`; the `text` check must exclude subclasses
  consistently. These are the exact spots where the host type system would
  otherwise leak into the semantics.
- `schema_validate` is fully data-driven: no Python types are ever required
  to validate — the schema alone decides. This is the dynamic-type-friendly
  core we want to preserve across any future static-typing work.

### 3.5 Portability

- Stdlib-only: `json`, `base64`, `binascii`. Runs on any CPython ≥3.8 with
  zero installation surface beyond the package itself.
- The package depends conceptually on `omnisys_core` (registry `js_deps`),
  but the code never imports it — keeping serde usable as a leaf dependency.
- Behavior is identical across platforms because text/bytes codecs are
  locale-independent (UTF-8 fixed, newlines always `\n`).

### 3.6 Lifecycle / error model (exceptions vs result values)

- Spec §17.4 says errors are values (`Result`/`Error`), never bare host
  exceptions. At the *portable semantic* level, however, the JS reference
  throws, and the Python lane must mirror it: `json_decode` raises
  `JSONDecodeError`, `from_hex` raises `ValueError`, `base64_decode` raises
  `binascii.Error`.
- The reconciliation: the raising function is the portable *primitive*; the
  OmniScript compiler wraps failures into structured `core` errors at the
  call site. Documenting the raising behavior precisely (which exceptions,
  when) is therefore part of the contract, not a violation of the error
  model.
- Alternative considered — returning `None`/`Result` from the Python
  functions — was rejected: it would silently diverge from the JS lane and
  hide malformed input.
- `schema_validate` never raises for *semantic* mismatch (returns `False`);
  it only reflects the input schema shape, exactly like the JS `typeMatches`.

### 3.7 AI usability (schema-driven validation)

- `schema_validate` gives agents a data-checking primitive: generate a
  value, then assert a shape. Because schemas are values, an agent can
  `json_encode`/`json_decode` them, diff them, and iterate without tooling.
- The closed vocabulary (`any`, `text`, `number`, `boolean`, `list`,
  `map`) is small enough for a model to enumerate from memory.
- Determinism aids diagnosis: same input → same result, no hidden state, no
  order-dependent behavior in the `fields` check (dict iteration order is
  insertion order in Python, but the result is order-independent: all keys
  must pass, so the check is commutative).

### 3.8 Interop

- JSON text ↔ any JSON-compatible value: universal interop target.
- base64/hex text ↔ arbitrary UTF-8 text: carries bytes through
  text-only transports (HTTP headers, logs, config files).
- CSV: interop with spreadsheets and tabular tooling — deliberately
  minimal (no quoting) to stay honest about the format's limits.
- Cross-lane interop is the headline goal: a value encoded by the Python
  lane must decode identically on the JS lane and vice versa. The known
  vectors in `tests/test_serde.py` (`616263`, `aGVsbG8=`) pin this.

---

## 4. Concrete design decisions for THIS Python implementation

1. **`json_encode` uses `ensure_ascii=False`.** JSON.stringify never escapes
   non-ASCII; Python defaults to `\uXXXX`. The flag gives cross-lane text
   parity and human-readable output. Test: `test_json_encode_keeps_non_ascii`.
2. **`json_decode` calls `json.loads` directly.** Exact inverse; invalid input
   raises `JSONDecodeError` (documented in the docstring).
3. **`csv_encode` = `'\n'.join(','.join(str(cell) …))`.** Mirror of the JS
   `map(String).join` chain; cells are stringified, never quoted.
4. **`csv_decode` strips, splits on `\n`, drops empty lines, trims cells.**
   Exact JS behavior including the `String(text)` coercion (Python's `str`
   params make this a no-op) and the `line.length > 0` filter.
5. **`to_hex`/`from_hex` are UTF-8 byte based** (`text.encode('utf-8').hex()`
   and `bytes.fromhex(...).decode('utf-8')`), which is the base64-compatible,
   spec-conformant interpretation for a UTF-8 language. The JS UTF-16
   behavior is a host artifact (deviation in §7).
6. **base64 is UTF-8 based** (`b64encode(text.encode('utf-8'))`); the JS
   reference already uses `TextEncoder`/`TextDecoder` (UTF-8), so there is
   exact parity.
7. **`base64_decode(…, validate=True)`** — `atob` throws on non-base64
   characters; `validate=True` reproduces that strictness instead of Python's
   default silent tolerance.
8. **`schema_validate` structure** mirrors the JS exactly: non-dict schema →
   `True`; truthy `type` checked via the closed vocabulary (unknown → `True`);
   `fields` (when a dict) requires every key present (`key in value`) and
   recursively validated. `bool` is excluded from `number`; `list` is excluded
   from `map`.
9. **Exceptions, not `None`.** Invalid input raises (mirrors JS); no silent
   `None` returns that could be confused with valid output. `schema_validate`
   is the only `Boolean`-returning function and returns `False` on mismatch.
10. **Private helper `_type_matches`** keeps the closed vocabulary in one
    place; `__all__` exposes exactly the nine registry names (locked by the
    conformance test).
11. **Stdlib only.** No dependency on any third-party codec; the package can
    be copied into any Python environment.

---

## 5. Deviations from the JS reference

Deliberate, documented divergences (each is small, tested, and justified):

1. **`to_hex` (and hence `from_hex`) encode UTF-8 bytes, not UTF-16 code
   units.** The JS reference iterates `String(text)` code units and emits
   their UTF-16 code; for ASCII/UTF-8-safe text the two agree (tested:
   `'abc'` → `616263`). For non-BMP or non-ASCII text they differ. Why: the
   language contract is UTF-8 text; hex is a byte encoding; UTF-16 was a host
   accident (JS has no byte view of a string without an encoder). The Python
   lane is internally consistent (`to_hex`↔`from_hex` round-trips any
   non-surrogate text, property-tested).
2. **`from_hex` rejects odd-length and non-hex input (`ValueError`)** instead
   of silently dropping the trailing character or producing garbage
   (`parseInt(..., 16)` on `'zz'` yields `NaN` → `'\u0000'`). Also,
   `bytes.fromhex` accepts uppercase and ASCII whitespace separators where JS
   would misparse. Strict failure beats silent corruption.
3. **`base64_decode` raises `binascii.Error`/`ValueError`** (via
   `validate=True`) rather than JS Buffer's tolerant base64. The `atob` path
   (browsers) throws, so the strict behavior matches the strictest JS path.
4. **No `String(x)` coercion.** JS `String(null)` → `'null'`; Python `str`
   parameters reject non-str statically (mypy strict). Inputs are typed
   `Text` in the contract, so coercion would be dead code.
5. **`number` excludes `bool` explicitly** — Python host-type leak that JS
   does not have (`typeof true` is `'boolean'`).
6. **`map` excludes `list`** — in JS, `typeof [] === 'object'`, so the JS
   `typeMatches` needs an `Array.isArray` guard; Python's `dict`/`list`
   separation makes the guard redundant but it is kept for symmetry and to
   protect against exotic subclasses.
7. **Minor CSV edge: `.strip()` vs `.trim()`.** Python's `str.strip()` removes
   a slightly wider whitespace set than JS `.trim()`; for the ASCII/latin
   whitespace in real data the results are identical.

Each deviation is locked by a test (see `tests/test_serde.py` and
`tests/test_properties.py`) so a future refactor cannot silently regress it.

---

## 6. Open questions

1. **TOML / YAML as future text formats?** Both add dependency weight and
   type ambiguity (YAML 1.1 booleans/ints, TOML date types). YAML is useful
   for config-shaped data; TOML for tool metadata. Decision deferred.
2. **MessagePack / CBOR as future binary formats?** Strongly indicated by the
   serde lesson (§2.2, §2.5); MessagePack is the leading candidate because it
   maps 1:1 onto the JSON value model. No work before phase 2.
3. **Full JSON Schema conformance?** Deliberately not implemented. Would
   require a large keyword subset and a dependency (or a mini-implementation).
   Open question whether `schema_validate` should grow optional keywords
   (`optional`, `pattern`, `min`/`max`) or stay minimal.
4. **Error model bridging:** should the Python lane expose a
   `schema_validate`-style `try` helper, or is the compiler-level
   exception→`Result` wrap (spec §17.4) the only sanctioned surface?
5. **Unicode normalization:** should text functions normalize NFC/NFD?
   Currently no — bytes must round-trip exactly.
6. **CSV quoting:** RFC 4180 quoting would fix the comma/newline round-trip
   hole but would diverge from the JS lane. Open until a backend requests it.
7. **`json_encode` determinism:** Python sorts dict keys only if
   `sort_keys=True` (we do not); insertion order is preserved. Both lanes
   agree on this (JS preserves insertion order too), so cross-lane text
   equality holds for equal insertion orders — worth documenting for
   hash-consing use cases.

---

## 7. How to read the gates for this module

- **Coverage:** every function and every branch in `schema_validate`
  (non-dict schema, truthy/falsy `type`, `fields` present/absent, key
  present/missing, nested pass/fail) is exercised; ≥95% branch is enforced.
- **Conformance:** `tests/test_conformance.py` locks the nine registry names,
  their callability, their purity, and the `__all__` surface.
- **Properties:** `tests/test_properties.py` pins the invariants (JSON, hex,
  base64, CSV round-trips; lenient schemas accept anything) across generated
  inputs, not just hand-written vectors.
- **Typing/linting:** mypy `--strict` (zero errors) and ruff (E, F, I, UP, B,
  SIM, N, D, PL, T20, PTH, ERA, Q, TID, RET; line length 100; single quotes)
  are clean.

The research gate, the registry contract, and the JS reference together
determine every line of this implementation; there is no
backend-specific behavior hidden in the portable core.