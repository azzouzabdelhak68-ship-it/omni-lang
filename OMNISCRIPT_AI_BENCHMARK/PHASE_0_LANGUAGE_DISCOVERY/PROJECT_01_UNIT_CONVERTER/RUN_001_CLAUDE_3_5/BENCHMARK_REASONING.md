# BENCHMARK_REASONING.md

## Observable Research Ledger for Multi-Unit Conversion Engine (Benchmark Task 0.1)

**Model**: Claude 3.5 (nemotron-3-ultra-free)
**Task**: Implement Multi-Unit Conversion Engine in OmniScript
**Date**: 2026-08-18

---

## Phase 1: Initial Investigation (2026-08-18 05:35)

### Questions Being Investigated
1. What is the exact OmniScript syntax for functions, contracts, and types?
2. How do `require`/`ensure` contracts work with the SMT verifier?
3. What are the supported comparison operators in contracts?
4. How does the `generate` CLI command work for test templates?
5. What is the proper structure for the main entry point (`when app starts:`)?
6. How to define structured result types for conversion outputs?

### Initial Hypotheses and Assumptions
- OmniScript uses `fn name(params) -> ReturnType:` syntax for functions
- Pure functions are declared with `pure` keyword
- Contracts use `require` for preconditions and `ensure` for postconditions
- `result` is the special variable for return value in `ensure` clauses
- Custom types defined with `type Name = { field: Type, ... }`
- `when app starts:` is the main entry point
- `show` displays output
- Comparison operators: `is`, `is not`, `greater than`, `less than`

### Files Inspected
- `tests/fixtures/valid/01_basic.omni` - Basic syntax
- `tests/fixtures/valid/02_function_with_effects.omni` - Functions, effects, pure
- `tests/fixtures/valid/05_custom_types.omni` - Type definitions
- `tests/fixtures/valid/06_show_output.omni` - Show statement
- `tests/test_smt.py` - Contract syntax (require/ensure)
- `tests/test_ai_tools.py` - Generate test functionality
- `tests/test_cli.py` - CLI verification commands

### Discovered Language Rules
1. **Function Declaration**: `fn name(param: Type, ...) -> ReturnType:` ... `end`
2. **Pure Functions**: `pure` keyword after function signature
3. **Contracts**: `require condition` (precondition), `ensure condition` (postcondition)
4. **Result Variable**: `result` refers to return value in `ensure`
5. **Comparisons**: `is` (equality), `is not` (inequality), `greater than`, `less than`, `greater or equal`, `less or equal`
6. **Types**: `Number`, `Text`, `Boolean`, `List`, custom record types
7. **Entry Point**: `when app starts:` ... `end`
8. **Output**: `show expression`
9. **Structured Types**: `type Name = { field: Type, ... }`
10. **Conditionals**: `if condition:` ... `end`, optional `else:` ... `end`
11. **Logical Operators**: `and`, `or` in contract expressions

### Compiler Commands Tested
- `python -m omni_compiler.cli check tests/fixtures/valid/01_basic.omni` → exit code 0 ✓
- `python -m omni_compiler.cli run tests/fixtures/valid/06_show_output.omni` → outputs "42" ✓

---

## Phase 2: Implementation Design (2026-08-18 05:40)

### Design Decisions

#### Conversion Result Type
```omni
type ConversionResult = {
    value: Number,
    source_unit: Text,
    target_unit: Text,
    status: Text
}
```

#### Temperature Conversions
- Celsius ↔ Fahrenheit: F = C × 9/5 + 32, C = (F - 32) × 5/9
- Celsius ↔ Kelvin: K = C + 273.15, C = K - 273.15
- Kelvin cannot be negative (require >= 0)

#### Length Conversions
- Meters ↔ Feet: 1 m = 3.28084 ft
- Meters ↔ Inches: 1 m = 39.3701 in
- Meters ↔ Kilometers: 1 km = 1000 m
- All values must be non-negative

#### Weight Conversions
- Kilograms ↔ Pounds: 1 kg = 2.20462 lb
- Kilograms ↔ Ounces: 1 kg = 35.274 oz
- All values must be non-negative

#### Contract Strategy (Initial)
- Each conversion function: `pure`, `require input >= 0` (where applicable), `ensure result.value matches formula`
- Temperature: Special handling for Kelvin (absolute zero boundary)
- All functions return `ConversionResult` struct

---

## Phase 3: Implementation (2026-08-18 05:45 - 06:15)

### Probe 1: Initial Implementation with Struct Returns
Created `source/unit_converter.omni` with 22 conversion functions returning `ConversionResult` structs directly.

**Error 1 - Syntax**: `greater than or equal to 0` not recognized
- **Fix**: Changed to `greater or equal 0` (from SMT source: `_ARITH` dict keys)

**Error 2 - SMT Verification**: All functions `unsupported` with "division by a literal zero is not defined"
- **Cause**: `require x is not 0 / 0` parsed as division by literal zero
- **Fix**: Removed all `require x is not 0 / 0` preconditions

**Error 3 - SMT Verification**: Still `unsupported` with "struct construction is not yet supported" / "struct field access is not yet supported"
- **Cause**: Verifier doesn't support `StructConstruct` or `FieldAccess` (see `smt.py:210-211`)
- **Fix**: Restructured pure functions to return `Number` only; added `make_result` helper (no contracts) for struct construction in main entry point

### Probe 2: Restructured Implementation
- 22 pure conversion functions returning `Number`
- Each with `require input greater or equal 0` (for length/weight/Kelvin) and `ensure result is formula`
- `make_result(value, source, target)` pure helper (no contracts) constructs `ConversionResult`
- Main entry point calls conversions, wraps with `make_result`, displays via `show`

### Compiler Commands Executed

```bash
# Check - passed on first try after syntax fix
python -m omni_compiler.cli check source/unit_converter.omni
# → "omni check: OK ✓ unit_converter.omni"

# Verify - passed after removing struct returns and 0/0 checks
python -m omni_compiler.cli verify source/unit_converter.omni
# → All 22 conversion functions: "verified", make_result: "no-contracts"

# Run - executed cleanly
python -m omni_compiler.cli run source/unit_converter.omni
# → Displays all 3 categories with correct values, boundary test for 0 Kelvin

# Generate - produced valid pytest template
python -m omni_compiler.cli generate source/unit_converter.omni celsius_to_fahrenheit
# → Valid Python with compile check, contract presence test, sample inputs, Hypothesis property test
```

### Errors Encountered and Corrections

| Error | Location | Correction |
|-------|----------|------------|
| `E-SYNTAX-001: Unexpected token 'or'` | Line 55: `greater than or equal to` | Use `greater or equal` |
| `division by a literal zero is not defined` | All `require x is not 0 / 0` | Remove NaN checks; rely on type system |
| `struct construction is not yet supported` | `ConversionResult(...)` in ensure | Return `Number` from pure functions; construct structs in non-verified code |
| `struct field access is not yet supported` | `result.value` in ensure | Verify on primitive return values only |

### Alternative Approaches Considered and Rejected

1. **Tuple Returns**: OmniScript doesn't support tuple/multiple return values
2. **Global State for Results**: Would violate `pure` declaration
3. **String Encoding**: Return formatted text instead of struct — loses structured access
4. **Omitting Struct Type**: Would not satisfy "structured result representation" requirement — kept type definition and `make_result` for runtime construction

---

## Phase 4: Verification (2026-08-18 06:20)

### Verification Commands Results

| Command | Exit Code | Result |
|---------|-----------|--------|
| `omni check source/unit_converter.omni` | 0 | ✅ PASS |
| `omni verify source/unit_converter.omni` | 0 | ✅ 22 verified, 1 no-contracts |
| `omni run source/unit_converter.omni` | 0 | ✅ Clean execution, correct output |
| `omni generate source/unit_converter.omni celsius_to_fahrenheit` | 0 | ✅ Valid pytest template |

### Test Suite Results
```
32 passed in 7.64s
- TestCompilerChecks: 4/4 passed
- TestTemperatureConversions: 6/6 passed
- TestLengthConversions: 10/10 passed
- TestWeightConversions: 6/6 passed
- TestBoundaryValidation: 3/3 passed
- TestPureFunctions: 1/1 passed
- TestStructuredResults: 2/2 passed
```

---

## Unresolved Questions (Resolved)

1. **Can `require`/`ensure` use arithmetic expressions?** → Yes, full arithmetic supported (`+`, `-`, `*`, `/`, grouping)
2. **Does the verifier support floating-point arithmetic?** → Yes, uses Z3 Reals; renders counterexamples as Python float/int
3. **How to handle multiple conversion functions in generate command?** → `generate` takes single function name; run multiple times for each

---

## Summary of Discovered Language Rules (Complete)

### Contracts & Verification
- `require` preconditions: `require expr` (multiple allowed, implicitly ANDed)
- `ensure` postconditions: `ensure expr` (multiple allowed, implicitly ANDed)
- `result` variable: refers to return value in `ensure`
- Supported operators: `is`, `is not`, `greater than`, `less than`, `greater or equal`, `less or equal`, `and`, `or`
- Arithmetic: `+`, `-`, `*`, `/`, unary `-`, grouping `(expr)`
- Division by symbolic denominator: adds `denominator != 0` path condition
- Literal division by zero (`0 / 0`, `x / 0`): rejected as unsupported
- Struct construction/access: unsupported in verifier (runtime only)
- Function calls in contracts: unsupported
- Loops in verified functions: unsupported

### Pure Functions
- Declared with `pure` after signature
- Effect checker enforces no side effects
- SMT verifier only analyzes pure functions

### Types
- Primitive: `Number`, `Text`, `Boolean`
- Composite: `List`, custom records `type Name = { field: Type, ... }`
- Struct construction: `Type(field=value, ...)`
- Field access: `expr.field`

### Control Flow
- `if condition:` ... `end`, optional `else:` ... `end`
- `for var in iterable:` ... `end`
- `break`, `continue` in loops
- Boolean conditions: comparison exprs, identifiers, `not` operator

### Entry Point & Output
- `when app starts:` ... `end` — main entry
- `show expr` — output with string interpolation `{var}`

### CLI Commands
- `check` — type/effect check, exit code 0 on success
- `verify` — SMT contract verification, JSON batch results
- `run` — compile to JS, execute with Node.js
- `generate` — produce pytest test template for function
- `inspect` — symbol information
- `build` — emit JS/WASM/C/Rust
- `explain` / `suggest` / `trace` — debugging aids