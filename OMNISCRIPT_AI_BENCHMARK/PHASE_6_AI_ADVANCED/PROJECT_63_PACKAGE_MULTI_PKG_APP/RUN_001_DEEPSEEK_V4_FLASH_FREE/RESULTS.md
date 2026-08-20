# RESULTS — Phase 6 Project 6.3: Package System / Multi-Package App

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE` (model: deepseek-v4-flash-free via opencode).

## MODEL_RESULT

### Task Completion Status: ✅ COMPLETE

**Summary**: Built a working multi-package dependency inspector in OmniScript on
top of `OMNISYS.pkg`:

1. `build_registry()` is a `pure` function that constructs a registry of 6 specs
   (core 1.0.0 / 1.1.0 / 2.0.0, parser 1.0.0 ← core `^1.0.0`, app 1.0.0 ←
   core `^1.0.0` + parser `^1.0.0`, analytics 1.0.0 ← core `^1.0.0`) purely via
   `omnisys.pkg.create` + `omnisys.pkg.registry_add`.
2. `test_list_dependencies()` lists each package's dependency names and encodes
   the result map through `omnisys.serde.json_encode` (map writes go through
   `omnisys.collections.map_set` only).
3. `test_version_satisfaction()` exercises the full semver constraint surface —
   exact (`1.2.3`), caret (`^1.2.3`), tilde (`~1.2.3`), range (`>=1.2.0`) — plus
   a deliberately failing case (`1.2.2` vs `^1.2.3` → `false`).
4. `test_dependency_resolution()` proves constraint-aware, deterministic,
   topological resolution: `resolve("app","1.0.0",reg)` → `app` → `core 1.1.0`
   (best match for `^1.0.0`) → `parser 1.0.0`.
5. `test_checksums()` proves `compute_checksum` determinism: `cs1 == cs2`
   (`"match":"true"`) with a different result for other content.
6. `test_manifest_parsing()` reads `omni.pkg.json` through the Node fs lane when
   available, otherwise degrades via `try`/`on error` to a synthetic manifest.
7. `test_install_packages()` demonstrates the filesystem `install` surface
   (declared but not called from the app block).

### Execution Efficiency
- `omni check source/package_inspector.omni` — exit 0.
- `omni build source/package_inspector.omni -o <tmp>.html` — exit 0 (JS lane).
- `omni verify source/package_inspector.omni` — exit 0; all 7 functions
  `no-contracts` (the program declares no `require`/`ensure` contracts).
- `omni run source/package_inspector.omni` — exit 0; all markers printed,
  ending with `=== Inspection Complete ===`.
- `python -m pytest tests/test_package_inspector.py -q` — 18 passed (~2 s).

### Invalid Assumptions Encountered
Real runtime bugs in `omnisys/pkg.js` found and FIXED (genuine benchmark
discoveries):

1. **`registry_add` signature mismatch.** The declared contract in
   `omni_compiler/omnisys_registry.py` is `fn(Map, Text, Map) -> Map` =
   `(registry, name, spec)`, but `omnisys/pkg.js` implemented
   `registry_add(registry, spec, version)`. Under the declared contract the
   runtime silently keyed the registry under the *spec object* (stringified
   `[object Object]`), so `registry_get(reg, "core", "1.0.0")` returned `null`.
   Fixed `omnisys/pkg.js` to accept `(registry, name, spec)` while tolerating
   the legacy `(registry, spec, version)` shape.
2. **`compute_checksum` was asynchronous.** Declared
   `_pure('fn(Text) -> Text')` but implemented with `await crypto.subtle...`,
   returning a `Promise`. `json_encode` rendered the promise as `{}` and
   `cs1 is cs2` compared two distinct promise objects → `false`. Fixed to a
   synchronous checksum: Node `crypto` SHA-256 when `require` is available,
   portable FNV-1a fallback otherwise — deterministic in both lanes.
3. **`resolve` treated the constraint as an exact registry key.**
   `resolve("app", "^1.0.0", reg)` looked up `registry["app"]["^1.0.0"]`,
   found nothing, and returned only `[app]`. Fixed to resolve constraints via
   `selectBestVersion` so `app@^1.0.0` yields `app`, `core 1.1.0`, `parser
   1.0.0` in topological order.
4. **fs calls in the app block need `try`/`on error` degradation.** The manifest
   read (and any fs lane call) can fail when the fs lane is unavailable or the
   file is not at the cwd; the program wraps `omnisys.fs.file_exists` in
   `try`/`on error` and falls back to a synthetic manifest.

Additional assumptions corrected during this run:
- **`omni run` does NOT expose `require`.** The task brief stated `require` is
  available in the run context, but `scripts/run-omnisys.js` never binds
  `global.require`, so the Node fs lane stays inactive under `omni run`
  (checksums use the FNV-1a fallback, and `file_exists` panics into the
  `on error` branch → synthetic manifest). Both lanes are graceful and
  deterministic; the test harness (which does bind `require`) exercises the
  sha256/fs-active lane.
- **Verify reports 7 functions, not 9.** The program defines 7 user functions
  (the remaining two named functions in the task brief were planning-only), so
  the test asserts status per function rather than a fixed count.

---

## ECOSYSTEM_RESULT

### API Findings
| Aspect | Finding |
|--------|---------|
| **`OMNISYS.pkg`** | Full surface present and working: `create(name,version,deps)->spec`, `registry_add(reg,name,spec)->reg`, `registry_get(reg,name,version)->spec|null`, `list_dependencies(spec)->[names]`, `parse_version(v)->{major,minor,patch,prerelease,build}`, `satisfies(v,constraint)->bool`, `resolve(name,version,reg)->[spec...]`, `resolve_versions(specs,reg,lockfile)`, `compute_checksum(content)->"sha256:\|fnv1a:"`, `manifest(path)` and `install(dir,reg)` (filesystem). |
| **Capability split** | `manifest`/`install` are `uses filesystem`; everything else is pure. `json_decode` (used by `manifest`) is `uses panic` — avoided by only reading manifests that exist. |
| **`OMNISYS.fs`** | `file_exists(path)->bool` confirmed; panics in the browser lane (no `require`), which the program absorbs via `try`/`on error`. |
| **`OMNISYS.collections`** | `map_set` is the only legal map write (`m["k"]=v` is a syntax error); used for every result-map build. |
| **`OMNISYS.serde`** | `json_encode(any)->Text` is pure and rounds the whole result maps into the `show` lines. |

### Language Findings
| Aspect | Finding |
|--------|---------|
| **Pure registry ops** | Building a registry, listing deps, semver checks, resolution and checksumming all compose as `pure` functions — the whole demo core is provably side-effect free. |
| **Typed struct** | `type PackageInfo = { name: Text, version: Text, status: Text }` compiles to a JSDoc interface; specs returned by `create`/`registry_get` are untyped Maps consumed via omnisys calls. |
| **Map writes** | Only `omnisys.collections.map_set` writes maps; literal maps (`{"core": "^1.0.0"}`) are fine as constructor expressions. |
| **try/on error** | `try:` / `on error:` blocks let capability calls degrade without `uses panic`; the app block calls the `uses filesystem` wrapper directly (app block inherits no callee effects). |
| **`is` operator** | `cs1 is cs2` emits `===`; safe for two checksum strings (deterministic equality test). |

### Compiler Findings
| Aspect | Finding |
|--------|---------|
| **E-CALL-003** | The checker enforces omnisys call arity against the registry (3 args for `create`/`registry_add`/`registry_get`/`resolve`, etc.); all arities verified in MIR. |
| **Symbol table** | `analyze()` + `inspect_symbol()` expose `declared_effects.uses` and `pure` per function — used to assert `filesystem` on the two fs functions and `pure`/no-uses on the five pure helpers. |
| **MIR normalization** | `OMNISYS.*` is lowered to `omnisys.*` (`_normalize_call_name`); MIR call nodes carry `{op:"call", name, args}` for static arity collection. |
| **`verify`** | Emits `omni.verify.batch`; functions without `require`/`ensure` are `no-contracts` (exit 0). |
| **App block** | Calls user wrappers with capabilities freely (no inherited effects at the app block edge). |

### Diagnostic Findings
| Code | Scenario |
|------|----------|
| `E-CALL-003` | Would fire if any `omnisys.pkg.*` call used the wrong arity (e.g. legacy `registry_add(reg, spec, version)` shape). |
| `E-SYNTAX-001` | Trailing comma in a type struct literal is rejected — keep struct fields comma-terminated cleanly. |
| `E-IMPORT-003` | Every consumed module (`pkg`/`fs`/`serde`/`collections`) must be imported even when its JS is pulled in transitively via `js_deps` (`pkg` → `core, serde, fs`). |

### Backend Findings
| Backend | Status |
|---------|--------|
| **JS lane (emitted HTML)** | Fully functional for `OMNISYS.pkg` when `require` is bound in the harness: fs lane active, `manifest` can read a real file, checksums are `sha256:` (Node crypto). |
| **`omni run`** | Works and exits 0, but never binds `global.require`; the Node fs lane stays inactive (FNV-1a checksums, synthetic manifest via `try`/`on error`). Graceful, but the "Node fs available" premise from the brief is not true under `omni run`. |
| **`resolve`/`compute_checksum`** | Both fixed bugs (constraint-aware resolution, synchronous checksum) hold in both lanes. |

### Positive Discoveries
1. Constraint-aware resolution works end-to-end: `app` → `core 1.1.0` (best
   semver match for `^1.0.0`, not the highest `2.0.0`) → `parser 1.0.0`,
   deterministic across lanes.
2. `compute_checksum` is deterministic in both the Node-crypto lane and the
   pure-JS FNV-1a fallback (`cs1 == cs2` asserted at runtime).
3. `try`/`on error` gives a genuine graceful-degradation story for fs: the same
   program runs identically with or without a real manifest.
4. The pure core (registry build, version checks, resolution, checksums) is
   testable without any capability mocking.

### Proposed Changes
| Priority | Change | Rationale |
|----------|--------|-----------|
| **HIGH** | Keep `registry_add` contract consistent between `omnisys_registry.py` and `omnisys/pkg.js` (now fixed); add a runtime-consistency test to the compiler suite | The silent signature drift produced a `null` registry read under the declared contract. |
| **MEDIUM** | `compute_checksum` must stay synchronous per its declared `fn(Text) -> Text` pure type (now fixed) | Async implementations are invisible to `json_encode` (`{}`) and break equality. |
| **MEDIUM** | `resolve` must be constraint-aware via semver (now fixed) | Exact-key lookups silently returned partial resolutions. |
| **MEDIUM** | Document (or bind) `require` in `scripts/run-omnisys.js` | The Node fs lane is never active under `omni run`, contradicting the brief; document it so future runs do not rediscover it. |
| **LOW** | Document flat `sim.*` vs `omnisys.sim` binding in `run-omnisys.js` if relevant | Avoids confusion between the two runtime shapes. |

---

## Verification Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| `omni check` passes | ✅ | Exit 0 |
| `omni build` succeeds | ✅ | JS target → `package_inspector.html` |
| `omni verify` passes | ✅ | 7 functions, all `no-contracts` |
| Registry build (6 specs) | ✅ | core/parser/app/analytics |
| Semver constraints (exact/caret/tilde/range) | ✅ | `sat_fail` correctly `false` |
| Deterministic topological resolution | ✅ | app → core 1.1.0 → parser |
| Checksum determinism | ✅ | `"match":"true"` in both lanes |
| Graceful manifest parsing | ✅ | synthetic manifest via `try`/`on error` |
| `omni run` exits 0 with markers | ✅ | ends `=== Inspection Complete ===` |
| Tests pass | ✅ | 18/18 passing |

---

## Files Produced

```
RUN_001_DEEPSEEK_V4_FLASH_FREE/
├── BENCHMARK_REASONING.md   # Continuous investigation ledger
├── RESULTS.md               # This summary
├── source/
│   ├── package_inspector.omni  # Multi-package inspector (~150 lines)
│   ├── omni.pkg.json           # Sample manifest (read when at the cwd)
│   └── test_minimal.omni       # Tiny validation snippet
├── tests/
│   └── test_package_inspector.py  # 18 tests (compiler + language + runtime)
└── packages/                  # Empty (reserved for the OMNISYS.pkg reference impl)
```