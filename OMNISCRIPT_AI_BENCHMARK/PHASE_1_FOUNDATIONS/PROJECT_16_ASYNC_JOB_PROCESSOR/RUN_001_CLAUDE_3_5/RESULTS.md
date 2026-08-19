# RESULTS.md

## MODEL_RESULT

### Task Completion Status
**COMPLETED** — The synchronous job processor has been implemented and verified.

### Execution Efficiency
- **omni check**: PASS (0 errors)
- **omni run**: PASS (produces aggregated job report)
- **Python tests**: 8/8 PASS

### Invalid Assumptions Encountered
1. **Async module availability**: Initially assumed `import OMNISYS.async` would not work based on task description. Investigation revealed the async module IS recognized by the checker when imported, but returns Promise objects that cannot be awaited in the synchronous OmniScript runtime.
2. **Struct construction syntax**: Used `{field=value}` syntax initially, but OmniScript requires `TypeName(field=value, ...)` for struct construction.
3. **Type system limitations**: No `any` type for struct fields; must use built-in types (Text, Number, Boolean, List, None).
4. **No `while` loops**: Only `for` loops supported; had to rewrite algorithms using `for` with manual counters.
5. **No `else if` chains**: Must use separate `if` statements.
6. **No array indexing**: `list[index]` not supported; must use `omnisys.collections.list_get(list, index)`.
7. **No higher-order functions**: Function values cannot be stored in lists and called dynamically.
8. **No `range()` builtin**: Had to implement `make_range()` manually.
9. **Parameter names**: `class` is a JS reserved word; causes SyntaxError in emitted code.
10. **Bare expressions in if blocks**: `if condition: 100 end` creates a Literal statement that the MIR converter doesn't handle; must use assignments.
11. **Effect enforcement**: Pure functions cannot call effectful functions; `omnisys.platform.sleep_ms` requires `uses process`.
12. **Field access on loop variables**: Checker doesn't infer types for loop variables; must use helper functions with typed parameters.

### What Was Implemented Synchronously
1. **Job Model**: `Job`, `JobResult`, `SchedulerConfig`, `AggregatedReport` types with all required fields
2. **Priority Scheduling**: `dispatch_jobs` simulates concurrent dispatch with priority-based sorting and round-robin worker distribution
3. **Timeout Classification**: `execute_with_timeout` classifies jobs as "timeout" when `expected_duration > timeout_ms`
4. **Cancellation**: `cancel_jobs` marks jobs as "cancelled" by ID
5. **Fan-out/Fan-in**: `fan_out` applies function to each input; `fan_in` aggregates results
6. **Race Pattern**: `race_first` returns first result (simulated)
7. **Aggregated Reporting**: `aggregate_results` produces summary with counts by status
8. **Effect Declarations**: All functions declare `pure` or `uses process` appropriately
9. **Entry Point**: `when app starts:` drives the scheduler and prints report

### What Would Be Needed for True Concurrency (Compiler Changes)
1. **Await/async syntax** in parser and type checker
2. **Promise unwrapping** in JS emitter — convert `omnisys.async.task` calls to `await` expressions
3. **Runtime support** for Promise resolution in entry point (make `when app starts:` async)
4. **Channel select/race** primitives with synchronous blocking semantics
5. **Effect system extension** to track async boundaries (`uses async` capability)
6. **Higher-order function support** — function values as first-class citizens
7. **Type inference** for loop variables and function call results

---

## ECOSYSTEM_RESULT

### API Findings
- **OMNISYS.async module**: Exists in registry and JS implementation (`omnisys/async.js`), provides `task`, `delay`, `all`, `race`, `any`, `timeout`, `channel`, `channel_send`, `channel_recv`, `is_promise`. All declared `pure` in registry.
- **Async behavior**: Returns Promise objects; OmniScript runtime is synchronous with no `await` — Promises are opaque and never resolve in the language surface.
- **OMNISYS.core**: Provides `type_of`, `none`, `panic`, math functions, Option/Result types. `none` is a keyword, not callable as function.
- **OMNISYS.collections**: List, Map, Set, Deque, Heap, RingBuffer operations. No `list_insert` in JS implementation despite registry declaration.
- **OMNISYS.platform**: Provides `now`, `sleep_ms`, `info`, `os`, `arch`, `env`, `capabilities`. `sleep_ms` requires `uses process`.

### Language Findings
- **Struct syntax**: `TypeName(field=value, ...)` for construction; `{field: Type}` for type declarations only.
- **Type system**: Built-in types: `Number`, `Text`, `Boolean`, `List`, `None`. No `any`, `Object`, or generics.
- **Control flow**: `if`/`else` (no `else if`), `for` loops only (no `while`), `break`/`continue` in loops.
- **Expressions**: No array indexing (`list[i]`), no higher-order functions, no ternary operator.
- **Function literals**: Not supported in expressions; only top-level `fn` declarations.
- **Reserved words**: `class`, `none`, `true`, `false` are keywords; avoid as parameter names.

### Compiler Findings
- **Checker**: Validates imports against OMNISYS_MODULES registry; enforces effect declarations (`uses`, `reads`, `writes`, `pure`).
- **MIR converter**: Fails on bare Literal statements (e.g., `if x: 100 end`). Requires all expression statements to be handled.
- **JS emitter**: Emits ES6 code inlined in HTML; `class` parameter name causes SyntaxError.
- **Effect enforcement**: Tracks capabilities transitively; pure functions cannot call effectful functions.

### Diagnostic Findings
- **Error codes**: E-SYNTAX-001, E-TYPE-001/002/003/004/005, E-NAME-001, E-IMPORT-001/002/003, E-EFFECT-001/003/004, E-INTERNAL-001.
- **Error messages**: Include location, context, and suggested fixes.
- **Internal errors**: MIR converter crashes on unhandled AST nodes (e.g., Literal as statement).

### Documentation Findings
- **Syntax reference**: No formal language spec; must infer from parser/lexer source and examples.
- **OMNISYS modules**: Registry in `omnisys_registry.py` is source of truth for available modules and functions.
- **Examples**: `examples/actors.omni`, `examples/chaos.omni` show `sim.*` usage patterns.

### Capability/Effect Findings
- **Capabilities**: `network`, `filesystem`, `database`, `camera`, `microphone`, `GPU`, `process`, `secrets`.
- **Effect declarations**: Required for any function using capabilities; enforced at function boundaries.
- **Pure functions**: Cannot perform any effects; enforced by checker.
- **Module-scope data**: `reads`/`writes` declarations required for global variable access.

### Backend Findings
- **JS backend**: Reference implementation; emits self-contained HTML with inlined OMNISYS runtime.
- **Node.js required**: `omni run` uses Node.js to execute emitted HTML.
- **Native backends**: C, Rust, WASM targets reject OMNISYS imports (E-BACKEND-001).

---

## Positive Discoveries
1. **OMNISYS.async module is fully specified** in registry and implemented in JS — ready for when async syntax lands.
2. **Effect system works well** — catches missing capability declarations at compile time.
3. **Struct construction with named args** — clean syntax for record creation.
4. **SMT verification** — `omni verify` can prove require/ensure contracts (though not used here).
5. **Pure functions** — strong guarantee for referential transparency.

---

## Proposed Changes
1. **Add `await`/`async` syntax** to parser and checker for true async support.
2. **Fix MIR converter** to handle Literal expression statements (or reject them with clear error).
3. **Implement `list_insert`** in `omnisys/collections.js` to match registry.
4. **Add `range()` builtin** or `List.range` method.
5. **Support `else if`** syntactic sugar.
6. **Add type inference** for loop variables and function call results.
7. **Allow `any` type** for struct fields (or `Object` type).
8. **Reserve `class` keyword** in parameter position or auto-rename in JS emitter.
9. **Document language syntax** formally (BNF or similar).
10. **Add `list[index]` syntax** for array access (desugar to `list_get`).