# BENCHMARK_REASONING.md

## Investigation Log: Project 1.4 — Error Handling/Recovery Pipeline

### Initial Questions & Hypotheses

**Q1: What error handling primitives does OmniScript provide?**
- Hypothesis: The language has `require`/`ensure` contracts, `OMNISYS.error` for structured errors, and `OMNISYS.core` for Result/Option types.

**Q2: How do effects interact with error handling?**
- Hypothesis: Functions declare `uses` capabilities; errors are pure values (no effects needed to create/propagate them).

**Q3: What is the syntax for function contracts?**
- Hypothesis: `require` and `ensure` clauses appear after the function signature colon, before the body.

**Q4: Can we simulate try/catch or do we use Result types?**
- Hypothesis: No try/catch in language; must use Result types (ok/err) and explicit pattern matching via `is_ok`/`is_err`.

### Files Inspected

1. **`omni_compiler/parser.py`** — FunctionDef has `requires: list[Any]`, `ensures: list[Any]`, `effects: dict`. Parsing logic at lines 267-308.
2. **`omni_compiler/checker.py`** — SemanticAnalyzer validates `requires`/`ensures` expressions at lines 320-323. Effect enforcement at lines 549-556.
3. **`omni_compiler/omnisys_registry.py`** — `error` module (lines 124-137): `error`, `error_code`, `error_message`, `error_code_of`, `error_with_context`, `error_has_context`, `error_to_dict`, `throw_error`, `is_error`. All pure.
4. **`omnisys/error.js`** — Runtime implementation: error objects are `{tag: "error", message, code, context}`.
5. **`omnisys/core.js`** — `ok`, `err`, `is_ok`, `is_err`, `panic`, `option`, `some`, `none`, `is_some`, `is_none`.
6. **`examples/chaos.omni`**, **`tests/fixtures/valid/*.omni`** — Syntax examples.

### Key Language Rules Discovered

| Rule | Evidence |
|------|----------|
| Function syntax: `fn name(params) -> Ret: requires ... ensures ... uses ... reads ... writes ... pure ... body end` | parser.py:243-308 |
| `require`/`ensure` expressions are arbitrary boolean expressions | checker.py:320-323 |
| Effects: `uses` (capabilities), `reads`/`writes` (state), `pure` (no effects) | checker.py:541-648 |
| OMNISYS.error functions are all `pure` (no capabilities needed) | omnisys_registry.py:124-137 |
| Result type: `omnisys.core.ok(val)` / `omnisys.core.err(err)` | omnisys_registry.py:58-61, core.js:40-51 |
| Custom types: `type Name = { field: Type, ... }` | parser.py:348-365, finance_dashboard.omni:24 |
| List literals: `[item1, item2, ...]` | tests/fixtures/valid/03_loops_and_lists.omni:21 |
| String interpolation: `"{var}"` in Text literals | finance_dashboard.omni:183 |

### Experimental Probes

**Probe 1: Basic error creation and context enrichment**
```omni
import OMNISYS
import OMNISYS.error
import OMNISYS.core

fn test_error() -> Text:
    e = omnisys.error.error("test message")
    e2 = omnisys.error.error_with_context(e, "stage", "validation")
    return omnisys.error.error_message(e2)
end
```
→ Checked: OK. Works as expected.

**Probe 2: Result type usage**
```omni
fn divide(a: Number, b: Number) -> any:
    if b is 0:
        return omnisys.core.err(omnisys.error.error("division by zero"))
    end
    return omnisys.core.ok(a / b)
end
```
→ Checked: OK. `any` return type works for union-like returns.

**Probe 3: Contract enforcement**
```omni
fn safe_divide(a: Number, b: Number) -> Number:
    require b is not 0
    ensure result is not 0
    return a / b
end
```
→ Checked: OK. Contracts are parsed and stored in MIR (mir.py:226-227).

### Architectural Decisions

1. **Pipeline Structure**: Four stages — `validate_input`, `transform`, `aggregate`, `format_output`. Each returns `Result` (ok/err).
2. **Error Classification**: Three categories encoded in error `code`:
   - `E-EXPECTED` — Recoverable, input-driven (skip and continue)
   - `E-TRANSIENT` — Recoverable, retryable (retry once, then escalate)
   - `E-FATAL` — Abort pipeline immediately
3. **Context Enrichment**: Each stage wraps errors with `error_with_context` adding `stage`, `input`, `timestamp`.
4. **Recovery Strategy**: 
   - Expected errors: log, collect in `failures` list, continue to next input
   - Transient errors: retry once, if persists → treat as fatal
   - Fatal errors: abort, return final report with all collected context
5. **Contracts**: Each stage declares `require` on inputs, `ensure` on outputs.

### Alternative Approaches Considered

| Approach | Rejected Because |
|----------|------------------|
| Throw exceptions via `omnisys.error.throw_error` | No try/catch in language; would terminate program |
| Use `Option` type instead of `Result` | `Option` lacks error payload; `Result` carries structured error |
| Single error type with severity field | Error `code` field is idiomatic per OMNISYS.error design |
| Global error handler | No global state; pipeline must be self-contained |

### Failed Approaches & Corrections

**Initial attempt**: Used `omnisys.core.panic` for fatal errors.
**Correction**: `panic` throws JS exception — crashes the runtime. Use `err` with `E-FATAL` code and let caller decide to abort.

**Initial attempt**: Tried to use `and`/`or` in `require` clauses.
**Correction**: Parser doesn't support `and`/`or` in expressions (finance_dashboard.omni:14). Use nested `if` instead.

### Unresolved Questions

1. **SMT Verification**: `omni verify` uses Z3 — can it verify our error propagation contracts? → Test after implementation.
2. **Effect of `throw_error`**: Declared `pure` but throws at runtime. Is this sound? → Documented as gap in ECOSYSTEM_RESULT.
3. **Stack traces**: OMNISYS.error doesn't capture stack traces. TASK.md confirms this is missing until v6.

### Verification Results (To Be Filled)

- `omni check source/recovery_pipeline.omni` → 
- `omni run source/recovery_pipeline.omni` → 
- `pytest tests/test_recovery_pipeline.py` → 

---