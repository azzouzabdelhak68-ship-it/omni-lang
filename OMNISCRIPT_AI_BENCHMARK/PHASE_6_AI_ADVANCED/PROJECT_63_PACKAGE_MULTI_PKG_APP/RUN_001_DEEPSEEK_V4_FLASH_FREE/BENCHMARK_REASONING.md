# Benchmark Reasoning Log — Project 6.3: Multi-Package Application & Dependency System

**Model:** DeepSeek V4 Flash Free  
**Run Directory:** `RUN_001_DEEPSEEK_V4_FLASH_FREE`  
**Start Time:** 2026-08-19

---

## Phase 1: Investigation & Environment Setup

### Repository Structure Analysis
- OmniScript compiler located at `E:\simualtion\omni_compiler\`
- OMNISYS modules registered in `omni_compiler\omnisys_registry.py`
- `OMNISYS.pkg` module defined with 11 functions:
  - `manifest` (filesystem)
  - `create` (pure)
  - `resolve` (pure)
  - `install` (filesystem)
  - `registry_add` (pure)
  - `registry_get` (pure)
  - `list_dependencies` (pure)
  - `parse_version` (pure)
  - `satisfies` (pure)
  - `resolve_versions` (pure)
  - `compute_checksum` (pure)
- JS implementation at `omnisys/pkg.js`
- Python reference implementation at `packages/omnisys-pkg/src/omnisys_pkg/__init__.py`

### CLI Commands Available
- `omni check` — type-check and effect-check
- `omni build --target js` — build to JavaScript
- `omni verify` — SMT verification
- `omni run` — execute via Node.js

### Key Language Facts Discovered
1. `import OMNISYS` model: importing alone consumes no capability; only calling `omnisys.*` functions requires the JS lane
2. Map index WRITE = SYNTAX ERROR; must use `map_set`
3. Keywords to avoid: `box`, `end`, `on`, `error`, `try`, `while`, `global`, `result`, `package`
4. App block calls wrappers with `uses filesystem` capability for fs/manifest/install
5. Effect system: functions declare capabilities in `uses` (filesystem, network, database, etc.)

---

## Phase 2: Design Decisions

### Package Layout (3 packages)
1. **`core`** — Foundation utilities, no dependencies
2. **`parser`** — Depends on `core`, provides parsing utilities
3. **`app`** — Main application, depends on `core` and `parser`

### Dependency Graph
```
core (1.0.0)
  ↑
parser (1.0.0) → depends on core ^1.0.0
  ↑
app (1.0.0) → depends on core ^1.0.0, parser ^1.0.0
```

### Dead-Code Elimination Strategy
- Create an "unused" package `analytics` that is declared in registry but NOT imported by `app`
- Demonstrate that building `app` does not include `analytics` in the output
- Use `omnisys.pkg.resolve_versions` to show resolution excludes unused packages

### Test Strategy
- Use `subprocess` to call `omni check/build/verify` on the source file
- Test manifest parsing, dependency resolution, dead-code elimination, checksum verification
- All tests run from the run directory as cwd

---

## Phase 3: Implementation Plan

### Source File: `source/package_inspector.omni`
- Import OMNISYS.pkg and other needed modules
- Define package specs for core, parser, app, analytics
- Build registry with multiple versions
- Demonstrate:
  1. Manifest parsing (read a manifest file)
  2. Dependency resolution (transitive, deterministic)
  3. Version constraint satisfaction (caret, tilde, ranges)
  4. Dead-code elimination (analytics not pulled in)
  5. Checksum verification
  6. Lockfile generation

### Test File: `tests/test_package_inspector.py`
- Subprocess calls to `omni check/build/verify`
- Validate CLI exit codes
- Parse and assert on outputs

---

## Phase 4: Implementation — Step by Step

### Step 1: Create test manifest file