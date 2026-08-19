# BENCHMARK_REASONING — Task 4.4: Native System Utility with Portable Fallbacks

## Run identifier: RUN_001_CLAUDE_3_5

## 2026-08-18 Session — Initial Investigation

### Q1. What is the compiler invocation & target surface?

Investigated from `cli.py`, `checker.py`, `emitter.py`:
- `python -m omni_compiler.cli check <file.omni>` -> exit 0 on success.
- `python -m omni_compiler.cli build <file.omni> --target {js,c,rust} -o <artifact>`.
- Default target for `omni check` is `js`.
- `omni check` runs: tokenize -> parse -> analyze (type + effect checking) -> MIR generation.
- `omni build` with `--target c` or `--target rust` rejects any `import OMNISYS.*` via `_reject_omnisys_on_native_target`.
- `omni build` with `--target js` allows OMNISYS imports and inlines the JS runtime.

### Q2. What OMNISYS modules are available?

Inspected `omnisys_registry.py`:
- `OMNISYS.core`: `is_empty`, `identity`, `panic`, `is_some`, `is_none`, `ok`, `err`, etc. (pure, no capability)
- `OMNISYS.collections`: `map_set`, `map_remove`, `list_push`, `list_pop`, `list_get`, etc. (pure, no capability)
- `OMNISYS.serde`: `json_encode`, `json_decode` (pure, no capability)
- `OMNISYS.net`: `server`, `start`, `request`, `get`, `post`, `response`, `status_of`, `body_of` (uses `network` capability)
- `OMNISYS.platform`: `info`, `os`, `arch`, `env`, `now`, `sleep_ms`, `capabilities` (uses `process` capability)
- `OMNISYS.test`: `assert_true`, `assert_eq`, `property`, `bench` (pure, no capability)
- `OMNISYS.fs`: `read_file`, `write_file`, `delete_file`, etc. (uses `filesystem` capability)
- `OMNISYS.process`: `check`, `explain`, `line_count`, `identifier_count` (uses `process` capability)

### Q3. What are the key language rules discovered?

From `checker.py`:
- **E-EFFECT-001**: `pure` function cannot use effectful capabilities.
- **E-EFFECT-003**: Capability used without declaration -> error.
- **E-EFFECT-004**: Module data (`reads`/`writes`) accessed without declaration -> error.
- `uses` declares effectful I/O a function performs.
- `reads` declares module-scope variables a function reads.
- `writes` declares module-scope variables a function writes.
- `pure` functions cannot have `uses`, `reads`, or `writes` (except empty sets).
- `import OMNISYS.<module>` adds module name to `imported_modules` set; used by `check_identifier` to allow OMNISYS calls.
- `sim.*` functions are available without imports (recognized by `name.startswith("sim.")` in `check_identifier` line 460).
- Built-in functions (`join`, etc.) and built-in capabilities (`fetch`, `http_get`, etc.) are pre-registered.

From `emitter.py`:
- `_omnisys_runtime(mir)` inlines JS sources for imported OMNISYS modules.
- Module-scope `let` declarations for names assigned in entry point.
- Function params and locals are emitted as JS params.
- Capability effects are emitted as comments: `// capability: network`.

From `cli.py`:
- `omni check` -> `_compile()` -> tokenize -> parse -> analyze -> MIR -> success.
- `omni build --target c/rust` -> `_reject_omnisys_on_native_target` -> exit 1 if OMNISYS imports present.
- `omni build --target js` -> `emit_js(mir)` -> self-contained HTML with embedded JS.

### Q4. What platform capabilities does `OMNISYS.platform` provide?

From `omnisys_registry.py` lines 349-360:
- `info()` -> `Map` — general platform info, capability: `process`
- `os()` -> `Text` — OS name, capability: `process`
- `arch()` -> `Text` — architecture, capability: `process`
- `env(Text)` -> `Text` — environment variable value, capability: `process`
- `now()` -> `Number` — current time (ms?), pure function
- `sleep_ms(Number)` -> `Number` — sleep, capability: `process`
- `capabilities()` -> `List` — declared capabilities, capability: `process`

### Q5. Design decisions for the system utility

**Decision: Use `import OMNISYS.platform` with `process` capability declarations.**
- `omni check` defaults to `--target js`, which allows OMNISYS imports.
- The portable abstraction will use `OMNISYS.platform` functions.
- Native escape hatch will use direct OS access where portable API is insufficient (but since we're targeting JS, the escape hatch will be conditional).

**Decision: Design portable interface with fallback behavior.**
- Portable `system_info()` function declares `uses process` and returns OS/arch/env.
- Runtime detection via `OMNISYS.platform.info()` and `OMNISYS.platform.capabilities()`.
- Graceful degradation when features are unavailable.

**Decision: No `import OMNISYS.collections` needed.**
- The task design avoids list-index-based state; use scalar variables instead (as discovered in Phase 3 reference).

### Q6. Files created so far

- `E:\simualtion\test_platform.omni` — minimal test confirming `import OMNISYS.platform` passes `omni check`.

### Q7. Unresolved questions

- How to design "implementation across multiple platform backends" within a single `.omni` file that passes `omni check`?
- Whether the test suite needs to target Node.js execution (`omni run`) or just type-checking.
- What the "native escape hatch" looks like when the JS emitter inlines OMNISYS.platform JS that may not exist at runtime.

### Next steps

1. Create `source/system_utility.omni` with the system utility implementation.
2. Create `tests/test_system_utility.py` with automated tests.
3. Verify `omni check source/system_utility.omni` exits 0.
4. Verify all tests pass.
5. Create `RESULTS.md` with dual-dimension benchmark summary.