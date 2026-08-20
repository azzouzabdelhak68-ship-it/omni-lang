# BENCHMARK REASONING LEDGER — Phase 5 Project 5.4: Project Inspection Tooling

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE` (model: deepseek-v4-flash-free)

This ledger records the observable investigation trajectory in order. It is
NOT rewritten/polished retroactively.

---

## 1. Initial Investigation (2026-08-19)

### Questions
- What is the contract for task 5.4? (read `PROJECT_54_TOOLING_PROJECT_INSPECTION/TASK.md`)
- What conventions does the completed sibling run (5.5 Native Interop) follow?
- Is `OMNISYS.tool` actually registered/implemented, or BLOCKED as TASK.md claims?
- Which OMNISYS modules/functions can the inspection tool use, and what capabilities
  do they require?
- How does the effect checker enforce `uses filesystem` / `uses process`?
- What runtime behavior should I expect from `omni run` and from a DOM-stub harness?

### Files inspected
- `PROJECT_54_TOOLING_PROJECT_INSPECTION/TASK.md` — contract.
- `PROJECT_55_NATIVE_INTEROP_ESCAPE_HATCH/RUN_001_CLAUDE_3_5/` — `BENCHMARK_REASONING.md`,
  `RESULTS.md`, `source/native_interop_demo.omni`, `tests/test_native_interop.py` — structure to mirror.
- `omni_compiler/omnisys_registry.py` — full OMNISYS module/function registry. Confirmed
  `OMNISYS.tool` IS registered (TASK.md "Missing/Blocked" status is STALE):
  - `tokenize(Text)->List` pure, `check(Text)->Map` uses `process`, `explain(Text)->Map`
    uses `process`, `line_count(Text)->Number` pure, `identifier_count(Text)->Number` pure.
  - `OMNISYS.fs` `read_file/file_exists/file_size/list_dir` use `filesystem`;
    `join_path/basename/dirname` are pure.
  - `OMNISYS.collections`: `list_push`, `list_contains`, `list_map`, `map_get`, `map_set`, ...
  - `OMNISYS.core`: `length`, `split`, `substring`, `char_at`, `is_empty`, ...
  - `OMNISYS.serde`: `json_encode/json_decode`.
- `omni_compiler/cli.py` — commands `check`/`run`/`build`/`verify`/`inspect`/`explain`/
  `suggest`/`generate`/`trace`/`lsp`/`fmt`. `build` default target `js` writes `<stem>.html`.
  `verify` emits `omni.verify.batch` JSON, exit 1 if any `failed`.
- `omnisys/tool.js` — Node lane runs `python -m omni_compiler.cli check/explain <path>` via
  `child_process.spawnSync`; panics when `require` is unavailable (browser lane).
- `omnisys/fs.js` — panics via `needNodeFs()` when `require` unavailable.
- `omni_compiler/checker.py` — effect enforcement: `E-EFFECT-001` (pure but uses caps),
  `E-EFFECT-003` (cap used without declaration), `E-EFFECT-004` (module data read/write
  without declaration), `E-EFFECT-010` (pure+borrows), `E-EFFECT-011` (borrows unused),
  `E-EFFECT-012` (borrowed cap not provided). Struct fields limited to
  `Number/Text/Boolean/List/None` + custom types (NOT `Map`).
- `omni_compiler/parser.py` — `parse_if_block` has NO `else if`; `parse_try_block` supports
  `try:` / `on error:` / `catch <var>:` / `finally:`.
- `tests/test_emitter.py` — `_run_emitted` DOM-stub harness pattern (vm.runInThisContext).
- `scripts/run-omnisys.js` — `omni run` runner: binds DOM stubs + `omnisys` runtime,
  does NOT expose `require` inside the vm context.

### Initial hypotheses
1. `OMNISYS.tool` is usable despite TASK.md stale status.
2. `uses process` required for `omnisys.tool.check/explain`; `uses filesystem` for
   `omnisys.fs.*` (except pure path helpers).
3. `when app starts:` block cannot itself consume capabilities (must call named functions).
4. Runtime in the Node/vm lane will panic on fs/tool calls unless wrapped.
5. Map literal `{}` may be rejected (5.5 noted this) — needs probing.

---

## 2. Probes & Raw Outputs

### Probe 1 — pure tool functions, structs, map_set, `{}`
File: `probes/probe1.omni`. Used `omnisys.tool.tokenize/line_count/identifier_count` as pure,
built a struct, `map_set({}, "k", "v")`, `map_get`.
```
$ python -m omni_compiler.cli check probes\probe1.omni
omni check: OK � probe1.omni        EXIT=0
$ python -m omni_compiler.cli run probes\probe1.omni
tokens: 11
lines: 1
ids: 7
struct name: x
map value: v                        EXIT=0
```
Interpretation: `{}` is ACCEPTABLE as a function argument (`map_set({}, ...)`), struct
construction + field access works, pure tool functions work at runtime, Number→Text
auto-concatenation works. So the 5.5 "empty map literal rejected" finding was NOT
reproducible for the argument position; `{}` as a plain assignment also passed later
(probe 7/8 used `{}` with map_set).

### Probe 2 — effectful tool/fs, capability declarations
Used `omnisys.tool.check` (in `run_tool_check`, `uses process`) and `omnisys.fs.read_file`
/`list_dir` (in functions with `uses filesystem`). App block called only the named function.
```
$ python -m omni_compiler.cli check probes\probe2.omni
omni check: OK � probe2.omni        EXIT=0
```
Interpretation: capability model confirmed. `check_result["ok"]` (Map index access) works.

### Probe 3 — map index WRITE is a syntax error
`m = {}` then `m["a"] = 1`.
```
$ python -m omni_compiler.cli check probes\probe3.omni
{"code":"E-SYNTAX-001","message":"Syntax error.",
 "details":"Unexpected token '=' of type TokenType.ASSIGN at line 7, col 12"}   EXIT=1
```
Interpretation: confirmed the brief — map index WRITE is a SYNTAX ERROR. Only
`omnisys.collections.map_set` writes maps. (Phase-1 project `file_organizer.omni` also
fails check today on its `m[k] = v` line — the language has moved on.)

### Probe 4 — multiple capabilities in one function
`fn combined(...)`: declared `uses filesystem` + `uses process`, called `fs.file_exists`
and `tool.check` directly inside it.
```
$ python -m omni_compiler.cli check probes\probe4.omni
omni check: OK � probe4.omni        EXIT=0
```
Interpretation: a single function can declare multiple capabilities; direct OMNISYS calls
inside the function (not just wrapped helpers) are fine as long as declared.

### Probe 5 — try/on error; E-EFFECT-004 on app-block var name collision
`safe_check` used `res` as a try-local AND the app block assigned `res`. 
```
$ python -m omni_compiler.cli check probes\probe5.omni
{"code":"E-EFFECT-004","message":"Module data 'res' accessed via writes without declaration."}  EXIT=1
```
Interpretation (KEY RULE): any name assigned in `when app starts` (or top level) becomes
MODULE data; writing a same-named variable inside a function requires `writes <name>`.
Fixed probe 5b by using distinct names (`out`, `check_result` inside fn; `check_outcome`
in app block) and added try/on error around `tool.check`.
```
$ python -m omni_compiler.cli run probes\probe5b.omni
ok: false
reason: cli-unavailable              EXIT=0
```
Interpretation (KEY RULE): `try: ... on error: ... end` CATCHES runtime panics from
OMNISYS capability calls in the vm lane. This gives graceful degradation. The vm lane
(`omni run` / DOM-stub harness) does NOT provide `require`, so tool.check panics there.

### Probe 6 — string ops, while, lstrip/starts_with; module-data collision
Built `lstrip` (char-scan while loop) and `starts_with` (substring compare). App block
originally reused `n` and `sub` → E-EFFECT-004 again; renamed app vars to `app_n`/`app_sub`.
```
$ python -m omni_compiler.cli run probes\probe6.omni
stripped: fn hello()
sw: true
sub: bcd
line count: 3                       EXIT=0
```
Interpretation: `substring(s,1,4)` on "abcdef" gives "bcd" (end-exclusive). while/break
works. App-block names must be disjoint from function-local names.

### Probe 7 — extraction pipeline + nested map + json_encode
Implemented `extract_functions/extract_capabilities/extract_imports` over
`split(text, "\n")`, built a metrics Map with `map_set`, `json_encode`'d it.
First attempt used `else if`:
```
{"code":"E-SYNTAX-001","details":"Expected token type TokenType.COLON, got TokenType.IF ('if') at line 69, col 14"}  EXIT=1
```
Interpretation (KEY RULE): `else if` is NOT supported by the parser. Nested
`else: if ... end end` required. After restructuring:
```
$ python -m omni_compiler.cli run probes\probe7.omni
report: {"lines":6,"tokens":19,"identifiers":14,"functions":["hello"],"capabilities":["pure"],"imports":["OMNISYS.core"]}
first fn: hello                     EXIT=0
```
Interpretation: `\n` escapes in Text literals are real newlines; the extraction +
map-building + json_encode pipeline works end to end at runtime.

### Probe 8 — else-if confirmed unsupported (isolated)
```
{"code":"E-SYNTAX-001","details":"Expected token type TokenType.COLON, got TokenType.IF ('if') at line 8, col 10"}  EXIT=1
```
Confirmed in isolation.

### Probe 9 — Map index as a condition
`if flag_map["ok"]:` compiled and ran (`picked: yes`). IndexExpr value usable as Boolean.

### Probe 10 — struct field type restriction
`type FileReport = { ..., check: Map }`.
```
{"code":"E-TYPE-001","message":"Unknown type 'Map' in fields of 'FileReport'."}  EXIT=1
```
Interpretation (KEY RULE): struct fields accept only `Number/Text/Boolean/List/None` or
declared custom types — NOT `Map`. Redesigned `FileReport` with `status: Text` and
`check: Text` (json-encoded diagnostic) instead.

---

## 3. Architectural & Code Decisions

### Naming policy (module-data collision avoidance)
- All app-block variables prefixed `app_` so no function-local name can collide with
  module-scope data (E-EFFECT-004). Verified: final source checks clean.

### Report shape
- Pure `inspect_source_text(text) -> Map`: `{lines, tokens, identifiers, functions,
  capabilities, imports, constructs}` — computed with OMNISYS.tool + string scanning.
- `type FileReport` struct (typed fields only): `name, path, exists, size, lines, tokens,
  identifiers, functions, capabilities, imports, constructs, status, check`.
- `build_file_entry(name, dir) -> FileReport` — fs read + metrics + `tool_check_safe`.
- `inspect_project(dir) -> Text` — enumerates `.omni` files, accumulates typed summary
  via a LOCAL `entry` variable (loop vars over List are `unknown`, so field access inside
  `for entry in files:` fails — 5.5 finding reproduced; fixed by assigning
  `entry = build_file_entry(...)` inside the `for name in names:` loop instead), returns
  `json_encode` of the top-level report map.

### Capability wrapping
- `file_exists_safe / file_size_safe / read_source_safe / list_source_dir_safe`
  (`uses filesystem`) and `tool_check_safe / tool_explain_safe` (`uses process`) each wrap
  their OMNISYS call in `try:/on error:` and return defaults on panic → graceful
  degradation on lanes without the capability.
- `build_file_entry` and `inspect_project` declare BOTH `uses filesystem` and `uses process`.

### Entry point
- App block calls pure `inspect_source_text` on an inline sample (runtime-testable) and
  effectful `inspect_project("source")` (degrades on capability-less lanes).

### Alternatives considered & rejected
1. **Return `check: Map` in a struct** — rejected (E-TYPE-001, Map not a struct field type);
   stored as json-encoded `Text` + `status: Text`.
2. **`else if` chains** — rejected (parser unsupported); nested `if/else`.
3. **Map index writes `m["k"] = v`** — rejected (E-SYNTAX-001); `map_set` only.
4. **Iterating a `List` of structs and reading fields** — rejected (loop var `unknown`,
   E-TYPE-002); accumulate via locally-typed `entry` variable.
5. **Letting capability calls panic uncaught** — rejected; try/on error gives graceful
   degradation and keeps `omni run` exit 0.
6. **Dependency on `omnisys.tool.check` at runtime under `omni run`** — rejected as the
   *only* path; vm lane lacks `require` → panics → caught. Full capability path requires
   a require-bridging harness (see runtime discovery below).

---

## 4. Runtime Discovery: the `require` bridge gap

`scripts/run-omnisys.js` (used by `omni run`) runs the emitted program with
`vm.runInThisContext`, which has NO `require` in scope. Both `omnisys/fs.js` and
`omnisys/tool.js` gate their Node backends behind `typeof require !== "undefined"`, so on
the reference `omni run` lane the fs + tool capabilities are UNREACHABLE even though Node
is present. `omni run` of the final source exits 0 with graceful degradation
(inline metrics real; project sources empty).

Probe: I wrote `probes/run_with_require.js` — a DOM-stub harness identical to
`tests/test_emitter.py::_run_emitted` but adding `global.require = require`:
```
$ node probes\run_with_require.js source\project_inspector.html
["inline-metrics: {\"lines\":6,\"tokens\":25,\"identifiers\":20,\"functions\":[\"add\"],...}",
 "project-report: {\"tool\":\"project-inspector\",\"target\":\"source\",
  \"sources\":[{\"name\":\"project_inspector.omni\",\"path\":\"source\\\\project_inspector.omni\",
   \"exists\":true,\"size\":11718,\"lines\":359,\"tokens\":2934,\"identifiers\":2652,
   \"functions\":[\"lstrip\",\"starts_with\",...,\"inspect_project\"],
   \"capabilities\":[\"pure\",...,\"filesystem\",...,\"process\",...],
   \"imports\":[\"OMNISYS.core\",\"OMNISYS.tool\",\"OMNISYS.fs\",\"OMNISYS.collections\",\"OMNISYS.serde\"],
   \"constructs\":[\"fn:21\",\"type:1\",\"if:12\",\"for:5\",\"while:2\",\"try:6\",\"show:2\"],
   \"status\":\"clean\",\"check\":\"null\"}],
  \"summary\":{\"files\":1,\"lines\":359,\"tokens\":2934,\"identifiers\":2652,\"functions\":21,\"capabilities\":23}}"]
```
Interpretation: with the `require` bridge the ENTIRE tool works end-to-end on the Node
lane — real fs reads of `source/`, real `omnisys.tool.check` subprocess against the python
CLI (status `clean`), full metric extraction (21 functions / 23 capability declarations
found, matching source count). This is an ecosystem gap worth reporting: the reference
runner should bind `require` to unlock the Node fs/process capabilities it already ships.

---

## 5. Final Source & Verification (raw outputs)

`source/project_inspector.omni` — 358 lines, 21 functions, 1 struct type.

```
$ python -m omni_compiler.cli check source\project_inspector.omni
omni check: OK � project_inspector.omni              EXIT=0

$ python -m omni_compiler.cli build source\project_inspector.omni -o <tmp>.html
omni build: wrote <tmp>.html (target=js)             EXIT=0

$ python -m omni_compiler.cli verify source\project_inspector.omni
{"schema":"omni.verify.batch","version":"1.0","results":[ 21 results, all "status":"no-contracts" ]}   EXIT=0

$ python -m pytest tests/ -q
17 passed in ~3.1s
```

`omni inspect` (AI-native tooling surface) on a function:
```
$ python -m omni_compiler.cli inspect inspect_source_text source\project_inspector.omni
{"schema":"omni.symbol","version":"1.0","name":"inspect_source_text","kind":"function",
 "type":"fn(Text) -> Map","declared_effects":{"uses":[],"reads":[],"writes":[],
 "borrows":[],"pure":true},"span":{...},"location":{...},"dependencies":[],"exported":true}   EXIT=0
```

---

## 6. Discovered Language Rules (summary)

1. `OMNISYS.tool` is registered + implemented (TASK.md status stale): tokenize/line_count/
   identifier_count pure; check/explain use `process`.
2. Capability enforcement: undeclared use → E-EFFECT-003; pure using caps → E-EFFECT-001;
   app-block names are module data (read/write without `reads`/`writes` → E-EFFECT-004).
   App block itself cannot declare capabilities; it must call named capability functions.
3. One function may declare multiple capabilities (`uses filesystem` + `uses process`).
4. Map index WRITE `m["k"] = v` is a SYNTAX ERROR; use `omnisys.collections.map_set`.
5. `else if` is NOT supported → nest `else: if ... end end`.
6. Struct fields accept only `Number/Text/Boolean/List/None` + custom types; `Map` rejected
   (E-TYPE-001).
7. Loop variables over `List` are `unknown` — no field access (E-TYPE-002); assign the
   function result to a local variable to get a typed struct.
8. `try:/on error:/end` catches runtime panics from OMNISYS capability calls.
9. `substring(start, end)` is end-exclusive; `\n` in Text literals is a real newline;
   Number auto-converts in string `+`.
10. vm-lane (`omni run`, DOM-stub harness) lacks `require`, so fs/process capabilities
    panic; binding `global.require = require` unlocks the full Node lane.

## 7. Unresolved Questions
- `omnisys.tool.check` returns `diagnostic: null` on success; no schema/version info about
  the diagnostic payload in the tool result itself (only in the JSON it spawns).
- Whether `omni verify` will ever emit `verified` for require/ensure contracts on effectful
  functions (all current results are `no-contracts`).
- Whether the reference runner will adopt the `require` bridge.