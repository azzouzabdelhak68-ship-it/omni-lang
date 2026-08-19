# Benchmark Reasoning: Meta-Benchmark — Testing & Self-Test Suite

## Run Directory
`RUN_001_DEEPSEEK_V4`

## Target Project Selection
Selected **Unit Converter (Phase 0 Project 0.1)** as the prior project to test. This is a clean, well-scoped domain with:
- Pure mathematical functions (temperature, length, weight conversions)
- Clear boundary contracts (non-negative constraints for Kelvin, length, weight)
- Structured data representation for conversion results
- No external dependencies (no filesystem, network, database effects)

## Investigation Log

### 2026-08-17: Initial Repository Exploration
- Explored `omni_compiler/` structure: lexer, parser, checker, emitter, omnisys_registry, ai_tools, cli
- Discovered OMNISYS.test module provides: `assert_true`, `assert_eq`, `assert_throws`, `property`, `bench`, `fail`
- All test functions are pure (no capabilities required)
- Property testing uses deterministic LCG with fixed seed (12345) for reproducibility
- Benchmarking uses `Date.now()` with iteration count

### Language Rules Discovered

#### Syntax (from lexer.py & parser.py)
- Functions: `fn name(param: Type) -> ReturnType:` followed by effect clauses, then body, ending with `end`
- Effect clauses: `pure`, `uses <capability>`, `reads <module>`, `writes <module>`
- Contracts: `require <expr>`, `ensure <expr>`
- Types: `Number`, `Text`, `Boolean`, `List`, custom `type Name = { field: Type, ... }`
- Struct construction: `TypeName(field1 = value1, field2 = value2)`
- Field access: `obj.field`
- Control flow: `if condition: ... else: ... end`, `for var in iterable: ... end`
- Lists: `[item1, item2, ...]`
- String interpolation in show: `"text {expr} more text"`

#### Effect System (from checker.py & omnisys_registry.py)
- Pure functions: declare `pure`, cannot call effectful functions
- Effectful functions: declare `uses <capability>` (network, filesystem, database, GPU, process, secrets, camera, microphone)
- OMNISYS modules have declared effects per function
- Checker enforces: pure functions cannot use capabilities; all used capabilities must be declared

#### OMNISYS.test Module (from omnisys_registry.py & test.js)
```javascript
// Assertions
assert_true(cond: Boolean, msg: Text) -> None
assert_eq(actual: any, expected: any) -> None
assert_throws(fn: fn) -> Boolean

// Property-based testing
property(prop: fn(Number) -> Boolean, samples: Number) -> Boolean
// Uses LCG with seed 12345, generates values 0-999

// Benchmarking
bench(fn: fn() -> None, iterations: Number) -> Number
// Returns elapsed milliseconds

// Failure
fail(msg: Text) -> None
```

### Target: Unit Converter Implementation
Based on PROJECT_01_UNIT_CONVERTER TASK.md requirements:
1. Temperature: Celsius, Fahrenheit, Kelvin
2. Length: Meters, Feet, Inches, Kilometers
3. Weight: Kilograms, Pounds, Ounces
4. Boundary contracts: Kelvin >= 0, length >= 0, weight >= 0
5. Result struct: value, source_unit, target_unit, status

### Test Suite Design Plan

#### Unit Tests (using assert_eq, assert_true)
- Every public conversion function
- Boundary cases: zero, negatives (where valid), edge values
- Round-trip properties (C→F→C, etc.)

#### Property-Based Tests (using property)
- Conversion invariants across generated inputs
- Commutativity/associativity where applicable
- Round-trip identity properties

#### Mocking/Isolation
- Pure functions don't need mocking (no side effects)
- For effectful functions (if any), would use parameterized test inputs

#### Performance/Benchmark (using bench)
- Core conversion computational paths
- Repeatable timing with fixed iterations

#### Tooling Integration
- Use `omni generate` to create pytest templates
- Validate generated tests compile and run

## Implementation Steps

1. Create `source/unit_converter.omni` - the target implementation
2. Create `source/self_test.omni` - the meta-test suite using OMNISYS.test
3. Create `tests/test_self_test.py` - pytest runner that validates the .omni test program
4. Verify with: `omni check`, `omni run`, `pytest tests/`
5. Document results in `RESULTS.md`

## Open Questions
- Can `property` test function capture external variables? (test.js shows it only receives a single Number value)
- How to test multi-parameter properties with single-arg property function?
- Does `bench` function need to be pure? (test.js shows it calls fn() directly)
- Can we use `assert_throws` for contract violation testing?

## Decisions
- Implement Unit Converter with pure functions only (no effects needed)
- Use `property` with wrapper functions for multi-parameter tests
- Use `bench` on core conversion loops
- Structure self_test.omni as a test runner that executes all test categories and reports results