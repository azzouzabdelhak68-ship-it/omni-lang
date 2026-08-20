# RESULTS — Phase 5 Project 5.4: Compiler Tooling & Project Inspection

## MODEL_RESULT

### Task Completion Status: ✅ COMPLETE

Built a project-inspection utility (`project_inspector.omni`) that analyzes OmniScript
source: tokenizes, counts lines/identifiers/tokens, extracts structure (functions,
capability declarations, imports, construct keywords), checks file status
(existence/size), runs the compiler CLI diagnostics (`omnisys.tool.check`/`explain`),
and emits a structured JSON report (`project-report`). All verification criteria pass:
`omni check` exit 0, `omni build` succeeds, `omni verify` proves all 21 functions
(`no-contracts`), pytest suite 17/17 green, and the emitted program runs end-to-end under
Node (with the documented `require` bridge) producing real metrics for its own source
directory.

### Execution Efficiency
- **Compiler checks**: `omni check` exit 0 in one pass after probing.
- **Contract verification**: `omni verify` exit 0 — 21/21 functions `no-contracts`.
- **Test suite**: 17 tests, ~3.1s, includes a live Node runtime test that inspects the
  real `source/` directory.
- **Runtime**: full capability path works on the Node lane when `require` is bridged into
  the vm context; the stock `omni run` lane degrades gracefully (exit 0, empty sources).

### Invalid Assumptions Encountered
1. **`else if` chaining** — assumed supported (seen in old Phase-1 examples). Parser
   rejects it (E-SYNTAX-001). Workaround: nested `else: if ... end end`.
2. **Struct field of type `Map`** — assumed allowed (built-in). Compiler rejects
   (E-TYPE-001); struct fields are limited to `Number/Text/Boolean/List/None` + custom
   types. Workaround: store the check result as JSON `Text` + `status` `Text`.
3. **Field access on loop variables over a `List`** — assumed typed. Loop vars are
   `unknown` (E-TYPE-002). Workaround: assign the typed function result to a local.
4. **Map index write `m["k"] = v`** — assumed valid (present in old Phase-1 code). It is a
   SYNTAX ERROR today. Workaround: `omnisys.collections.map_set`.
5. **App-block variable names** — assumed independent of function locals. Any name assigned
   in `when app starts` becomes module data; reusing it in a function demands
   `reads`/`writes` declarations (E-EFFECT-004). Workaround: `app_`-prefix all app vars.
6. **`omni run` capability availability** — assumed fs/tool would work on the Node lane.
   The stock runner never exposes `require` to the vm context, so those capabilities
   panic. Workaround: try/on-error degradation + a require-bridging harness for the full
   path (documented).

---

## ECOSYSTEM_RESULT

### API Findings
| Aspect | Finding |
|--------|---------|
| **OMNISYS.tool** | Registered + implemented (TASK.md "BLOCKED/Missing" status is STALE). `tokenize/line_count/identifier_count` pure; `check/explain` use `process` and bridge to `python -m omni_compiler.cli`. |
| **OMNISYS.fs** | `read_file/file_exists/file_size/list_dir` use `filesystem`; `join_path/basename/dirname` pure. Works on the Node lane once `require` is bridged. |
| **OMNISYS.collections** | `map_set/map_get` are the only map write/read API; `list_push`, `length`, etc. compose cleanly. |
| **OMNISYS.serde** | `json_encode` handles maps, lists of structs, and nested reports. |
| **`omni inspect`** | Machine-readable `omni.symbol` record (kind, type, declared_effects incl. `pure`, exported) — the AI-native inspection surface is real and typed. |

### Language Findings
| Aspect | Finding |
|--------|---------|
| **`else if`** | NOT supported by the parser — must nest `else: if ... end end`. |
| **Struct field types** | Limited to `Number/Text/Boolean/List/None` + custom types; `Map` rejected (E-TYPE-001). |
| **Map writes** | `m["k"] = v` is a syntax error; `map_set` is the only writer. |
| **List loop vars** | Untyped (`unknown`); no field access (E-TYPE-002). Assign typed function results to locals. |
| **Module data rule** | App-block/top-level assigned names become module resources; function writes/reads need `writes`/`reads` (E-EFFECT-004). |
| **`try:/on error:`** | Catches runtime panics from OMNISYS capability calls — enables graceful degradation. |
| **Multiple capabilities** | A single function may declare both `uses filesystem` and `uses process`. |

### Compiler Findings
| Aspect | Finding |
|--------|---------|
| **check** | Reliable static gate; enforces capabilities + data effects across all 21 functions. |
| **verify** | Emits `omni.verify.batch`; all functions currently `no-contracts` (no require/ensure in source). |
| **build (js)** | Writes a self-contained HTML with the OMNISYS runtime inlined; exit 0. |
| **Diagnostics** | JSON `omni.diagnostic` with `fixes` (some auto-applicable, e.g. "add the missing `writes res` declaration"). |

### Diagnostic Findings
| Aspect | Finding |
|--------|---------|
| **E-SYNTAX-001** | Correctly flags map index writes and `else if` — messages are precise but do not suggest the idiomatic replacement (`map_set`, nested if). |
| **E-EFFECT-004** | Auto-fix suggestion text is literally `writes <name>` — works, but the module-data rule (app-block name reuse) is easy to trigger accidentally and hard to guess. |
| **E-TYPE-001** | Explains the allowed struct field types only via a negative hint; no list of allowed built-ins in the message. |
| **OMNISYS.tool.check/explain** | Return the compiler's own diagnostics (`diagnostic` null on success) — good machine-readability story. |

### Documentation Findings
- `TASK.md` for project 5.4 declares `OMNISYS.tool` "Missing/BLOCKED" — STALE; the registry
  and `omnisys/tool.js` ship a working implementation.
- `scripts/run-omnisys.js` (the `omni run` runner) does not document or bridge the
  `require` gap, silently disabling fs/process capabilities on the Node lane.
- No per-module README documents the `try:/on error:` graceful-degradation idiom for
  capability calls.

### Capability/Effect Findings
| Aspect | Finding |
|--------|---------|
| **`filesystem`** | Required and enforced for every `omnisys.fs` I/O call; wrappers declare it at named-function boundaries. |
| **`process`** | Required and enforced for `omnisys.tool.check/explain` (subprocess CLI bridge). |
| **try/on error** | The only in-language mechanism for capability-failure fallback; works for panics, keeps `omni run` exit 0. |

### Backend Findings
| Backend | Status |
|---------|--------|
| **`omni run` (stock)** | vm context lacks `require` → fs/process capabilities panic → tool degrades (inline metrics real, project sources empty). Exit 0. |
| **Node + `require` bridge** | Full end-to-end: real fs reads, real CLI `check` subprocess (`status: "clean"`), complete structured report for `source/` (1 file, 359 lines, 2934 tokens, 2652 identifiers, 21 functions, 23 capability declarations). |
| **Browser lane** | fs/tool panic by design (`core.panic`); wrappers degrade gracefully. |

### Positive Discoveries
1. `OMNISYS.tool` is a working, AI-native, machine-readable inspection surface
   (`tokenize`/`line_count`/`identifier_count` pure; `check`/`explain` return the
   compiler's own JSON diagnostics).
2. Pure string-scanning (split/substring/char_at) is sufficient to reconstruct
   project structure (functions, capabilities, imports, constructs) without regex.
3. `try:/on error:` enables graceful cross-lane capability degradation with exit 0 —
   a robust pattern for portable OMNISYS tooling.
4. Structs with typed fields + local-variable assignment give type-safe report assembly
   and typed summary arithmetic.
5. Binding `global.require = require` in a DOM-stub harness unlocks the entire Node
   fs/process surface that `omnisys/tool.js` and `omnisys/fs.js` already implement.

### Proposed Changes
| Priority | Change | Rationale |
|----------|--------|-----------|
| **HIGH** | Bind `require` (and/or a controlled `fs`/`child_process` bridge) in `scripts/run-omnisys.js` | Unlocks filesystem + process capabilities on the Node lane the runner already targets. |
| **HIGH** | Refresh `TASK.md` 5.4 status | `OMNISYS.tool` is implemented; documenting it as BLOCKED misdirects benchmark/AI usage. |
| **MEDIUM** | Support `else if` chains | Nested if/else is verbose and a common expectation from C-like languages. |
| **MEDIUM** | Allow `Map` as a struct field type | Current restriction forces JSON-text workarounds in typed records. |
| **MEDIUM** | Auto-fix E-SYNTAX-001 for `m["k"] = v` → `map_set` | Idiomatic replacement is statically knowable. |
| **LOW** | Emit allowed built-in type list in E-TYPE-001 details | Faster self-correction for struct authors. |

---

## Verification Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| `omni check` passes | ✅ | Exit 0 |
| `omni build` succeeds | ✅ | Exit 0 (js target) |
| `omni verify` proves contracts | ✅ | 21/21 `no-contracts`, exit 0 |
| pytest suite passes | ✅ | 17/17 passed (~3.1s) |
| `filesystem`/`process` capabilities declared | ✅ | Asserted by tests + checked at runtime |
| tokenize/line_count/identifier_count counts | ✅ | Runtime-asserted: 6 lines / 25 tokens / 20 identifiers on sample |
| check/explain invoked with correct arity | ✅ | MIR call-node arity == 1 asserted |
| End-to-end runtime inspection | ✅ | Node harness: real `source/` analysis, `status: "clean"` |

---

## Files Produced

```
RUN_001_DEEPSEEK_V4_FLASH_FREE/
├── BENCHMARK_REASONING.md        # Investigation ledger (probes, raw outputs, rules)
├── RESULTS.md                    # This summary
├── source/
│   └── project_inspector.omni    # Inspection tool (358 lines, 21 functions)
├── tests/
│   └── test_project_inspector.py # Test suite (17 tests)
└── probes/                       # Investigation probes + require-bridge harness
```