# BENCHMARK_REASONING.md

## State-Machine Adventure Engine - Research Ledger

### Initial Investigation (2026-08-18)

**Questions Being Investigated:**
1. What are the exact OmniScript syntax rules for custom types, functions, and control flow?
2. How do effect declarations (`pure`, `uses`, `reads`, `writes`) work and what are the enforcement rules?
3. How do `require`/`ensure` contracts work for state transition validation?
4. What are the build patterns for JS, C, and WASM targets?
5. How to represent game state (rooms, inventory, transitions) using custom types?

**Initial Hypotheses & Assumptions:**
- OmniScript uses `type Name = { field: Type, ... }` for custom data structures
- Functions declared with `fn name(params) -> ReturnType:` and effects
- State transitions can be validated with `require`/`ensure` clauses
- The CLI builds HTML for JS target, .c for C target, and HTML wrapper for wasm-browser target
- Module-scope variables persist across function calls (important for game state)

**Files Inspected:**
- `omni_compiler/lexer.py` - Token types and keywords
- `omni_compiler/parser.py` - AST node definitions and parsing logic
- `omni_compiler/checker.py` - Semantic analysis, effect enforcement, type checking
- `omni_compiler/emitter.py` - JS emitter
- `omni_compiler/c_emitter.py` - C emitter
- `omni_compiler/wasm_emitter.py` - WASM emitter
- `omni_compiler/mir.py` - MIR conversion
- `tests/test_emitter.py`, `tests/test_c_emitter.py`, `tests/test_types.py`, `tests/test_checker.py` - Test patterns

**Discovered Language Rules:**
1. **Custom Types**: `type Room = { name: Text, description: Text, locked: Boolean, connections: List, items: List }`
2. **Functions**: 
   ```
   fn move(direction: Text) -> Boolean:
       require current_room is not none
       ensures result is true or result is false
       writes current_room
       writes inventory
       ...
   end
   ```
3. **Control Flow**: `if condition: ... else: ... end`, `for item in list: ... end`
4. **Variables**: Assignment with `name = expr`, struct construction `Type(field=value)`, field access `obj.field`
5. **Effects**: 
   - `pure` - no side effects
   - `uses network/filesystem/database/secrets` - capabilities
   - `reads var_name` - reads module-scope variable
   - `writes var_name` - writes module-scope variable
6. **Contracts**: `require condition`, `ensure condition` on functions
7. **Built-ins**: `join(list, separator)`, `show expr` (print)
8. **Literals**: Numbers, Text (quoted strings), Boolean (true/false), None, Lists `[...]`

**Architectural Decisions for Adventure Engine:**
1. Define custom types for `Room`, `GameState`, `Item`
2. Module-scope variables for current room, inventory, game metrics
3. Navigation functions with `require`/`ensure` for valid transitions
4. Item interaction functions for pickup/use
5. Assertion contracts on locked room entry (require key in inventory)

---

### Implementation Log

#### Step 1: Creating source/adventure.omni
- Define custom types for game entities
- Implement module-scope state variables
- Implement navigation, item interaction functions
- Add require/ensure contracts for state validation
- Add app entry point for demonstration

#### Step 2: Creating tests/test_adventure.py
- Test state transitions
- Test inventory management
- Test locked room enforcement
- Test cross-backend builds

#### Step 3: Running verification commands
- `omni check source/adventure.omni` → exit code 0
- `omni build source/adventure.omni --target js` → valid JS output
- `omni build source/adventure.omni --target c` → valid C output
- `omni build source/adventure.omni --target wasm-browser` → valid WASM wrapper output

#### Step 4: Creating CONFORMANCE_RESULTS.md and RESULTS.md