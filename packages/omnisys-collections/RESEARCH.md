# OMNISYS.collections — Research & Design Notes (v6 Phase 1)

Research gate for the Python reference implementation of the OMNISYS
`collections` module (List / Map / Set / Deque / Heap / RingBuffer), produced
per `docs/architecture/04-api-design-principles.md` §1 (the §17.3 eleven
questions) and `docs/architecture/19-quality-gates.md` §6 (the research gate).

Scope: study the borrowed ecosystems (C++ STL, Java Collections, Python
`collections`, Rust std, JS `Array`/`Map`/`Set`), answer the eleven questions,
then record the concrete decisions for THIS Python package and every deviation
from the JS reference (`omnisys/collections.js`) it mirrors.

---

## 1. The eleven questions (§17.3)

### Q1. What problem is it solving?

Collection types and the operations on them: ordered sequences (List), keyed
lookup (Map), membership (Set), double-ended queue (Deque), priority queue
(Heap), and a bounded overwrite buffer (RingBuffer). OMNISYS needs a portable,
AI-first vocabulary for "the usual things you do with a list of things",
shared by every backend without exposing a host library's API surface.

### Q2. Which concepts survived because they're genuinely useful?

- Sequences with push/pop/get/set, slicing, concatenation, search, sort,
  reverse, fold/map/filter, join, zip.
- Associative containers with get/set/remove/has and key/value enumeration.
- Membership containers with add/remove/has and set algebra
  (union/intersection/difference).
- FIFO/LIFO access to both ends of a queue.
- Min-heap priority behavior (peek/pop minimum) and bounded-capacity
  overwriting buffers (ring).

All six survive every studied ecosystem in some form, which is the strongest
signal that they are genuinely useful concepts, not accidents of one host.

### Q3. Which exist due to historical constraints?

- `list_join` over a `sep` string is a string-concatenation idiom (perl/JS)
  that Python's `str.join` and Rust's `join` also carry; it exists because
  printing a flattened list is a universal need.
- `ring_pop` from the front using array shift semantics is an O(n) operation
  in an array-backed buffer; the "ring" name suggests a circular-buffer
  fantasy that the JS implementation does not actually implement (it is an
  array with head-eviction). This is a historical naming artefact.
- Deque as `{"tag", "items"}` with `pop(0)` front removal is the same
  array-shift approximation; real deques (C++ `std::deque`, Python
  `collections.deque`) are O(1) at both ends with different storage.
- Heap represented as an explicit items array rather than an opaque handle is
  a JSON-friendly compromise: the JS emitter can only inline JSON-shaped
  values, and a min-heap is naturally an array with a heap property.

### Q4. Which APIs are awkward due to host language?

- JS `Array.prototype.sort` sorts lexicographically by default and needs a
  numeric comparator `(a, b) => a - b`; OMNISYS fixes this by declaring
  `list_sort` numeric. In Python `sorted` uses `<` (works for numbers, fails
  for mixed types) — a latent deviation (see §8).
- JS `Map` uses strict identity (`===`) key semantics; OMNISYS's JSON-friend
  values are also identity-based. Python dict keys hash — so Python `dict`
  keys must be hashable (`list` keys raise TypeError). That is a host
  constraint, not an OMNISYS design choice.
- JS arrays tolerate sparse holes and `undefined`; Python lists do not. The
  Python lane must be explicit that `list_get` on a missing index panics
  rather than returning `undefined`.
- Java `List` distinguishes `indexOf` (object equality) from `contains`
  (`equals`); Python `list.index` raises `ValueError` instead of returning -1,
  so `list_index_of` must convert the exception (or pre-check) to match JS.

### Q5. Which abstractions are hard for AI agents?

- The Set-as-array representation is easy for agents to read and to
  serialise, but invites the duplicate-bug: an agent may append without
  checking membership. The library hides this by making `set_add` check
  first, but the value shape itself does not enforce uniqueness.
- Tagged container shapes (`{"tag": "deque", ...}`) are easy for agents to
  introspect (`type_of` can see `tag`) but easy to construct wrongly (missing
  `tag`, wrong `items` key). The registry does not enforce construction; the
  test suite documents the shapes.
- Mutable-in-place vs return-new-copy is a constant source of agent bugs.
  OMNISYS draws a hard line per operation and documents it; the property and
  unit tests lock it in.

### Q6. Which concepts become first-class Omni concepts?

All 43 registered functions are first-class OMNISYS concepts with compiler-
checked signatures. The tagged value shapes (Deque/Heap/RingBuffer) are
first-class *values*; the JS emitter inlines them as plain objects. `List`,
`Map`, `Set`, `Deque`, `Heap`, `RingBuffer` appear as nominal types in the
registry signatures.

### Q7. Which remain libraries?

- Non-registered conveniences that exist in the studied ecosystems but are not
  part of the portable core: `sorted` with a key function, reverse iterators,
  `itertools`-style generators, slice with step, `Counter`/`defaultdict`,
  `OrderedDict` guarantees beyond insertion order, multimaps, sorted maps,
  bit sets, `Vec` capacity management, `std::deque` growth policy. These stay
  host-library or escape-hatch territory.

### Q8. Which map to the effect/capability system?

None. Every collections function is declared `pure` (empty `effects` set in
the registry). This is a deliberate capability-honesty statement: collections
never touch network/filesystem/database/secrets/process, so the compiler can
prove purity and freely reorder/parallelise these calls.

### Q9. What belongs in the portable semantic layer?

The operation vocabulary itself: the 43 functions, the six value shapes, the
panic conditions, insertion-order guarantees, in-place vs copy rules, numeric
sort semantics. Anything a user must rely on for correctness across backends
belongs here.

### Q10. What must remain backend-specific?

- Performance characteristics (whether a ring eviction is O(1) or O(n), whether
  a heap is array-backed or node-backed).
- Memory/pointer mechanics (Rust `Vec` capacity, C++ allocators, JS sparse
  arrays).
- Exact error message *text* beyond the OMNISYS panic strings.
- Python's `dict` insertion-order guarantee vs JS object key ordering
  (integer-like keys sort first in JS `Object.keys`); the portable contract
  says "insertion order" and both lanes honour it for non-integer keys.

### Q11. What is the escape hatch?

The value shapes are plain, serialisable JSON-ish structures, so a user can
drop to host libraries directly on any value (e.g. Python `heapq` on a Heap's
`items`, `collections.deque` on a Deque's `items`) without leaving OMNISYS's
data model. `omnisys_core.panic` is the shared escape for error reporting.

---

## 2. Studied ecosystems

### 2.1 C++ STL (`std::vector`, `std::map`, `std::set`, `std::deque`,
`std::priority_queue`)

- Capabilities: contiguous sequence (vector), balanced-tree map/set, double-
  ended deque, heap as a container adapter over vector.
- Strengths: predictable complexity, strong ownership model, rich algorithms
  library. Weaknesses: huge API surface (iterators, allocators, comparators),
  template noise, poor error messages — the worst ergonomics of the five for
  agents.
- Performance: O(1) amortised vector push/pop, O(n) middle insert; map/set
  O(log n).
- Error model: undefined behaviour on out-of-range `operator[]`; checked
  `.at()` throws. OMNISYS chooses a single panic model instead.
- Portability: excellent (standardised), but no JSON story without
  serialisation.
- OMNISYS take-away: the "sequence vs associative vs membership" split maps
  directly onto List/Map/Set.

### 2.2 Java Collections (`java.util.List`, `Map`, `Set`, `Deque`,
`PriorityQueue`)

- Capabilities: interfaces + implementations; `ArrayList`, `HashMap`,
  `HashSet`, `ArrayDeque`, `PriorityQueue`.
- Strengths: uniform interfaces, `Collections` static helpers, clear docs;
  `indexOf`/`contains` use `equals`. Weaknesses: verbosity, generics noise,
  `remove` returns boolean not the element (a famous ergonomic wart).
- Performance: `ArrayList` get O(1), remove middle O(n); hash containers O(1)
  average; `PriorityQueue` is a min-heap by default.
- Error model: checked/unchecked exception split (IndexOutOfBounds is
  unchecked); OMNISYS normalises to panic.
- Portability: portable within JVM; serialisation is JVM-specific.
- OMNISYS take-away: `PriorityQueue.poll/peek` inspire `heap_pop`/`heap_peek`;
  Java's `remove(Object)` wart is why OMNISYS keys removal by index.

### 2.3 Python `collections` stdlib (list, dict, set, `collections.deque`,
`heapq`)

- Capabilities: list/dict/set are built-in and JSON-native; `deque` is a real
  buffer; `heapq` provides `heappush`/`heappop` on a plain list.
- Strengths: exceptional ergonomics; the same list can be a List, a Set, or a
  Heap's `items`; `deque.popleft` is O(1). Weaknesses: Python `set` is not
  JSON-serialisable (unstable order), and dict keys must be hashable.
- Performance: list O(1) get/set/push/pop; `pop(0)`/`insert(0)` are O(n) —
  the reason real deques exist. `heapq` is O(log n) push/pop.
- Error model: exceptions everywhere (`ValueError`, `IndexError`, `KeyError`);
  OMNISYS maps all invalid-state cases to a single panic.
- Portability: stdlib is everywhere; dict insertion order is a CPython 3.7+
  guarantee.
- Interop: perfect JSON interop for list/dict; the reason Set is a list.
- OMNISYS take-away: Python *already* has the exact container family; the
  design question was which host shapes to keep (`list`, `dict`) and which to
  tag (Deque/Heap/Ring as dicts).

### 2.4 Rust std (`Vec`, `HashMap`, `HashSet`, `VecDeque`, `BinaryHeap`,
`Vec` as slice)

- Capabilities: `Vec` sequence; `HashMap`/`HashSet`; `VecDeque` with O(1)
  `push_front`/`pop_front`; `BinaryHeap` (max-heap).
- Strengths: ownership rules make aliasing impossible to get wrong; iterator
  adapter chains (`map`/`filter`/`fold`) are the gold standard for the
  functional ops OMNISYS ships. Weaknesses: borrow-checker friction for
  agents; `BinaryHeap` is a max-heap by default.
- Performance: `Vec` amortised O(1) push; `VecDeque` O(1) both ends;
  `BinaryHeap` O(log n).
- Error model: `panic!` on out-of-bounds slice indexing — the closest analogue
  to OMNISYS's panic model. Rust's `get`/`get_mut` return `Option`; OMNISYS
  deliberately does NOT expose Options for these — it panics instead.
- Portability: portable but with a steep learning curve; JSON needs `serde`.
- OMNISYS take-away: Rust's iterator `fold/map/filter` naming is reused
  verbatim (`list_fold`, `list_map`, `list_filter`); `VecDeque` justifies the
  Deque concept even though our Python lane uses O(n) array shifts.

### 2.5 JS `Array` / `Map` / `Set` (the authoritative reference)

- Capabilities: `Array` is the universal collection (list, stack, queue,
  set-as-array); `Map` is insertion-ordered with `===` keys; `Set` is a real
  value-set with `has`/`add`/`delete`.
- Strengths: `Array` is JSON-native and everywhere; method chaining is
  ergonomic. Weaknesses: arrays conflate list/stack/queue/set semantics;
  `sort` defaults to string order.
- Performance: `push`/`pop` O(1); `shift`/`unshift`/`splice` O(n); `Map`/`Set`
  O(1) hash.
- Error model: `undefined` for missing keys (no panic); `throw` for programmer
  errors; OMNISYS converts missing-key to KeyError in Python (see §8.4).
- Portability: identical semantics in Node and browsers once core.js is
  inlined — this is what the whole platform hinges on.
- OMNISYS take-away: the JS implementation is the conformance authority; the
  Python lane mirrors it operation-for-operation (see §5).

---

## 3. Cross-cutting analysis

### 3.1 Strengths and weaknesses of the six-value design

| Value | Strengths | Weaknesses |
|-------|-----------|------------|
| List = Python list | JSON-native, every host has an array | one shape serves list/stack/queue |
| Map = Python dict | JSON-native, insertion order | keys must be hashable |
| Set = Python list | JSON-native, readable | O(n) membership, no uniqueness invariant |
| Deque = tagged dict | introspectable, portable | O(n) front ops, hand-built shape |
| Heap = tagged dict | introspectable, portable | must be maintained by OMNISYS ops only |
| RingBuffer = tagged dict | introspectable, capacity explicit | O(n) eviction, naming overpromises O(1) |

### 3.2 Performance

- Python list get/set/push/pop are O(1); `list_remove`, `set_remove`,
  `deque_push_front`, `deque_pop_front`, `ring_push` (evict) and `ring_pop`
  are O(n) because they shift arrays — identical to the JS lane.
- `list_sort` is O(n log n); `heap_push`/`heap_pop` are O(log n) (the only
  place the lane implements a real algorithm).
- `list_index_of`, `list_contains`, `set_*` membership are O(n) (linear scan
  with `==`), matching JS `indexOf` semantics.
- No attempt is made to out-perform the JS lane; performance *character* is
  portable, exact constants are not.

### 3.3 Ergonomics

- Mutating ops return the same object (`is`), so chaining is safe; non-mutating
  ops return fresh objects, so callers never alias by accident.
- Names are `module_noun_verb` (`list_push`, `map_get`, `heap_peek`) —
  greppable, discoverable, and exactly match the registry and the JS names.
- All functions are pure and side-effect-free; the only shared dependency is
  `omnisys_core.panic`.

### 3.4 Type-system interaction

- Registry signatures use `List`, `Map`, `Set`, `Deque`, `Heap`, `RingBuffer`
  as nominal types. In Python they map to `list[Any]`, `dict[Any, Any]` and
  tagged `dict[str, Any]` aliases (`Deque`, `Heap`, `RingBuffer`).
- mypy strict: every function is fully annotated; `fn` callbacks are typed
  `Callable[[Any], Any]` / `Callable[[Any, Any], Any]` (mirroring the
  registry's untyped `fn`).
- Panics are typed as returning `None` (not `NoReturn`) so mypy sees code
  after a panic as reachable — a pragmatic match to the JS `throw` that the
  compiler treats as diverging at the OmniScript level.

### 3.5 Portability

- The Python lane ships identical value shapes and semantics to the JS lane,
  so a program's collections behaviour is portable across backends.
- Insertion order for Map keys/values is guaranteed (Python dicts and JS
  objects both preserve it for non-integer-like keys).
- The tagged shapes carry a `tag` field so `omnisys.core.type_of` and
  debugging tools can distinguish Deque/Heap/Ring without host tricks.

### 3.6 Error model (panic vs return)

The studied ecosystems split three ways:

1. Return sentinel: JS returns `undefined` for missing map keys; Python
   `list.index` raises; `dict[key]` raises `KeyError`.
2. Throw/raise: Python `IndexError`/`KeyError`/`ValueError`; JS throws on
   nothing here (out-of-range array access returns `undefined`).
3. Panic: Rust panics on out-of-bounds slice index; C++ UB or `.at()` throws.

OMNISYS unifies on a single panic model for *invalid states* (empty pops,
out-of-range access), routed through `omnisys_core.panic` so the error
travels through the platform's error lane (`[OMNISYS.core] ...`), exactly as
the JS lane does. Missing *data* (a missing map key) is NOT an invalid state
— it is absent data, and the Python lane surfaces it as `KeyError` because
there is no `undefined` value in JSON. This is the single deliberate,
documented error-model deviation (§8.7).

### 3.7 AI usability

- Every name is prefixed by its container (`list_`, `map_`, `set_`, `deque_`,
  `heap_`, `ring_`): an agent can autocomplete or grep the whole vocabulary.
- Deterministic: same inputs, same outputs, no hidden state, no PRNG.
- Panic messages are stable strings that tests assert verbatim, so agents can
  pattern-match failures.
- No overloads, no keyword-only args, no variadic functions: every signature
  is exactly the registry signature.
- Structurally inspectable: `__all__` matches the registry exactly (locked by
  the conformance test).

### 3.8 Interop

- Lists and Maps are directly `json`-serialisable; Sets (list-shaped),
  Deques, Heaps and Rings are plain objects with `items` lists — also
  directly serialisable. This is the whole reason Set is not a Python `set`
  and the containers are dicts rather than classes.
- A Heap's `items` list can be handed to Python `heapq` or a Deque's `items`
  to `collections.deque` as an escape hatch; the reverse is also true (a
  Python `heapq`-maintained list is a valid Heap value).

---

## 4. Concrete design decisions for THIS Python implementation

### D1. List = Python `list`

Direct mirror of JS arrays. Mutating ops (`list_push`, `list_set`,
`list_remove`) mutate and return the same object; non-mutating ops
(`list_slice`, `list_append`, `list_sort`, `list_reverse`, `list_map`,
`list_filter`, `list_zip`) return new lists. `list_fold` is the one op that
returns an arbitrary accumulator.

### D2. Map = Python `dict`

`map_get` is plain `map_[key]` (raises `KeyError` on missing — documented
deviation, §8.7). `map_remove` guards with `if key in map_` to mirror JS
`delete` (a no-op for absent keys) instead of catching `KeyError`.
Keys/values enumerate in insertion order.

### D3. Set = Python `list` with unique items (NOT a Python `set`)

This is the flagship decision. Reasons:

1. **JSON-friendliness**: `json.dumps` of a Python `set` silently converts to
   a list with unstable ordering; a list-shaped Set round-trips losslessly.
2. **Identity with JS**: the JS lane models Set as an array; the Python lane
   must produce identical value shapes for conformance.
3. **Determinism**: list preserves first-insertion order; Python `set`
   iteration order is hash-dependent and non-deterministic across processes.
4. **Nesting**: a Python `set` cannot contain lists or dicts (unhashable); a
   list-shaped Set can hold any JSON value, exactly like JS `indexOf`.

Cost: O(n) membership and `==`-based uniqueness (so `1 == True` collides,
see §8.6). Accepted: correctness of shape and determinism trump constant
factors in a reference implementation.

### D4. Deque / Heap / RingBuffer = tagged dicts

`{"tag": "deque", "items": [...]}`, `{"tag": "heap", "items": [...]}`,
`{"tag": "ring", "capacity": int, "items": [...]}`. Dicts rather than classes
because the JS emitter only inlines JSON-shaped values and the conformance
test requires identical shapes. `tag` mirrors the `type_of` vocabulary so
`type_of(deque)` can say "deque". There are no `deque_new`/`heap_new`
constructors in the registry — callers build the plain dict; `ring_new` is the
only constructor.

### D5. In-place vs copy semantics (hard rule, per operation)

| Returns the same object | Returns a new object |
|---|---|
| `list_push`, `list_set`, `list_remove`, `map_set`, `map_remove`, `set_add`, `set_remove`, `deque_push_front`, `deque_push_back`, `heap_push`, `ring_push` | `list_slice`, `list_append`, `list_sort`, `list_reverse`, `list_map`, `list_filter`, `list_zip`, `map_keys`, `map_values`, `set_union`, `set_intersection`, `set_difference` |

`list_sort`/`list_reverse` copy FIRST, then sort/reverse — the input is never
mutated. `set_union` copies `a` then appends unique items of `b`; it never
mutates either input. The unit tests assert identity (`is`) for mutating ops
and non-aliasing for the copy ops.

### D6. Panic messages (exact strings)

Routed through `omnisys_core.panic` with the full `collections.<condition>`
strings, byte-identical to the JS lane:

- `collections.list_pop on empty list`
- `collections.list_get index out of range`
- `collections.list_set index out of range`
- `collections.list_remove index out of range`
- `collections.deque_pop_front on empty deque`
- `collections.deque_pop_back on empty deque`
- `collections.heap_pop on empty heap`
- `collections.heap_peek on empty heap`
- `collections.ring_pop on empty ring`

### D7. Panic dependency resolution

`omnisys_core` currently ships as a placeholder (`VERSION` only). The Python
lane resolves `panic` defensively: it reads `omnisys_core.panic` if present,
and otherwise falls back to a local `PanicError`-raising `_panic`. A test
bootstrap (`tests/conftest.py`) mirrors the resolved `panic`/`PanicError`
back onto `omnisys_core` so `pytest.raises(omnisys_core.PanicError)` works
today and becomes a no-op the day core ships its real panic. This is a
monorepo-ordering artefact, not an API decision; the public contract remains
"panics are raised by `omnisys_core`".

---

## 5. The JS reference and the mirror rule

The conformance authority is `omnisys/collections.js`; every function in this
package is a transliteration of it:

- `list_*` → `list.append` / guarded `pop` / guarded index access with the JS
  `index < 0 || index >= length` guard preserved exactly; `slice` →
  `list[start:end]`; `append` → `a + b`; `contains` → `in`; `index_of` →
  guarded `list.index` returning -1; `sort` → `sorted` on a copy (JS numeric
  comparator); `reverse` → `list[::-1]`; `fold`/`map`/`filter` → Python
  equivalents with identical left-to-right order and truthiness semantics.
- `list_join` → `sep.join(str(item) ...)`; `list_zip` → pairs up to the
  shorter length.
- `map_*` → dict ops; `set_*` → list-as-set ops with `indexOf`-style
  membership.
- `deque_*` → `items` list with `insert(0, ...)` / `append` / `pop(0)` /
  `pop()` and empty-guards.
- `heap_*` → array-backed min-heap with the exact sift-up (`parent = (i-1)//2`,
  `<=` break) and sift-down (smallest-child swap, break when settled) logic.
- `ring_*` → `items` list, push-then-evict-front when over capacity, pop from
  front.

---

## 6. Deviations from the JS reference

### §8.1 `list_sort` comparator

JS: `(a, b) => a - b` (numeric). Python: `sorted(list_)` uses `<`. For the
numeric inputs the tests and the registry's "numeric sorted copy" promise
target, the results are identical. For mixed or non-numeric types the JS
comparator would return `NaN` (making `sort` leave elements in place) while
Python raises `TypeError`. Deviation chosen because Python has no idiomatic
numeric-subtraction sort; documented as a hard guarantee only for numbers.

### §8.2 `list_slice` negative-index edge

JS `slice(start, end)` clamps and treats negatives relative to `length`;
Python slicing does the same. The two differ for extreme out-of-range
negatives on the *start* bound (e.g. `slice(-100, ...)`: JS clamps to 0,
Python also clamps to 0). No observable deviation for in-range indices;
documented as "mirrors Python slicing".

### §8.3 `list_join` string forms

JS `String(x)`: `null`→`"null"`, `undefined`→`"undefined"`, arrays→`"1,2,3"`.
Python `str(x)`: `None`→`"None"`, `[1, 2, 3]`→`"[1, 2, 3]"`. The OMNISYS
types that reach `list_join` are Text/Number/Boolean (no null/undefined in
JSON), so the observable difference is confined to nested lists.

### §8.4 `map_get` on missing key

JS returns `undefined` (data absent is not an error). Python has no
`undefined`; the lane raises `KeyError`. This is a required deviation to stay
inside Python's type system — returning `None` would conflate "absent key"
with "present key whose value is None". Documented in README and in the
`map_get` docstring; tests either use existing keys or assert `KeyError`.

### §8.5 `==` equality vs JS `===`

JS `indexOf`/`includes` use strict identity: `1` and `true` are different.
Python `in`, `list.index`, `list.remove` use `==`: `1 == True`. Consequently
`list_contains([1], True)` is True in Python and False in JS. For JSON-native
data (numbers, strings, booleans as distinct values) this is unobservable;
it only appears when a caller mixes numeric and boolean values. Documented,
not "fixed": Python's `==` is the only portable equality, and forcing identity
would break JSON value semantics (two equal strings must match).

### §8.6 Set membership equality

Same root cause as §8.5, applied to the list-shaped Set. `set_add([1], True)`
is a no-op in Python but would add in JS. Accepted for the same reason.

### §8.7 `map_remove`/`set_remove` absent-key behaviour

JS `delete obj[key]` and `splice(-1)` are silent no-ops for absent items; the
Python lane guards (`if key in map_`, `if item in set_`) and is a no-op
likewise. No observable deviation; the guard exists to avoid Python's
`KeyError`/`ValueError`.

### §8.8 Deque/Heap/Ring construction

The JS lane has no constructors for Deque/Heap either; values are plain
objects. Python lane is identical — only `ring_new` exists. Tests build
`{"tag": ..., "items": []}` by hand. No deviation; this is the shared
contract.

### §8.9 Panic error type

JS `core.panic` throws `Error("[OMNISYS.core] collections.<msg>")`. Python
raises `PanicError` (the `omnisys_core` error type) carrying the same
message text. The prefix differs (`[OMNISYS.core] ` vs whatever the Python
core prepends) but the *condition strings* are identical and asserted verbatim
by the tests.

### §8.10 Index types

Registry says `Number`; Python types indices as `int`. JS `arr[1.5]` reads an
`undefined` property; Python `list_[1.5]` raises `TypeError`. Numeric indices
in OmniScript are integers by construction; documented as an int-only
guarantee.

---

## 7. Open questions

1. **Set semantics for mixed types**: should the Set ever be upgraded to a
   Python `set` behind a canonicalising wrapper (at the cost of JSON-shape
   purity), or is the list-shaped Set permanent for v6?
2. **`==` vs identity**: if the platform later needs strict-identity
   membership (to distinguish `1` from `True`), how should that be expressed
   in OmniScript, given JSON has no such distinction?
3. **Deque/Heap performance**: the O(n) `pop(0)`/`insert(0)` mirror JS. Should
   a future phase add backend-fast paths while keeping shapes identical (e.g.
   a Python `collections.deque` inside the `items` field, requiring shape
   conversion on introspection)?
4. **`map_get` error model**: is `KeyError` the right surface, or should the
   platform gain an `Option`-returning `map_get_opt` (mirroring Rust `get`)?
5. **`list_sort` stability and keys**: JS's comparator-based sort is stable in
   modern engines; Python `sorted` is stable. Should a key-based `list_sort`
   variant be registered for non-numeric types?
6. **RingBuffer naming**: the "ring" is an array with head-eviction, not a
   true circular buffer. Should the registry rename it (`bounded_queue`?) or
   keep the name for continuity with the JS lane?
7. **Empty-panic vs option**: Rust's `VecDeque::pop_front` returns `None` on
   empty; OMNISYS panics. Is a separate `deque_pop_front_opt` worth adding for
   the "peek without committing" pattern?
8. **Folds and threading**: should `list_fold` gain a right-to-left variant,
   and should any function accept a `Thread`-safe callback contract once
   `omnisys.async` lands?

---

## 8. Gate compliance checklist

- [x] Eleven questions answered (§1).
- [x] Ecosystems studied: C++ STL, Java Collections, Python `collections`,
      Rust std, JS Array/Map/Set (§2).
- [x] Strengths/weaknesses (§3.1), performance (§3.2), ergonomics (§3.3),
      type-system interaction (§3.4), portability (§3.5), error model (§3.6),
      AI usability (§3.7), interop (§3.8) all covered.
- [x] Concrete design decisions for THIS Python impl (§4).
- [x] Deviations from JS documented with rationale (§6).
- [x] Open questions recorded (§7).