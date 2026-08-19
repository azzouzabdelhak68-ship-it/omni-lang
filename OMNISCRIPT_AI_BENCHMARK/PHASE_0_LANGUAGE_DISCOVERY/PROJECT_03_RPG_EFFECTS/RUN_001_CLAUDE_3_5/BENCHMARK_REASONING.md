# Benchmark Reasoning Log: RPG Action & Effect Engine (Task 0.3)

## Run Directory: RUN_001_CLAUDE_3_5

---

## Initial Investigation (2026-08-18)

### Questions Being Investigated
1. What is the OmniScript syntax for function definitions with effect declarations?
2. How do pure functions, capability declarations (uses/reads/writes), and capability inheritance work?
3. What are the exact diagnostic output schemas for `omni check`, `omni explain`, and `omni suggest`?
4. How should the RPG engine model character stats, HP, MP, status effects with proper effect declarations?

### Initial Hypotheses
- Functions can declare `pure` for pure mathematical computations
- Functions can declare `uses <capability>` for capabilities like `network`, `filesystem`, `database`, `secrets`
- Functions can declare `reads <variable>` and `writes <variable>` for module-scope data access
- Higher-level functions calling lower-level ones must inherit/declare the same capabilities
- The `invalid_effect.omni` fixture demonstrates a pure function calling `write_file` (filesystem capability) which should fail

### Files Inspected
- `E:\simualtion\omni_compiler\checker.py` - Semantic analyzer with effect enforcement
- `E:\simualtion\omni_compiler\parser.py` - Parser for OmniScript syntax
- `E:\simualtion\omni_compiler\cli.py` - CLI commands (check, explain, suggest)
- `E:\simualtion\tests\test_checker.py` - Test patterns for effect system
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_0_LANGUAGE_DISCOVERY\PROJECT_03_RPG_EFFECTS\TASK.md` - Task requirements
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_0_LANGUAGE_DISCOVERY\PROJECT_03_RPG_EFFECTS\invalid_effect.omni` - Invalid fixture

### Compiler Commands Executed & Raw Outputs

#### `omni check invalid_effect.omni`
```json
{
  "schema": "omni.diagnostic",
  "version": "1.0",
  "code": "E-EFFECT-001",
  "category": "effect",
  "severity": "error",
  "message": "Function declared 'pure' but uses ['filesystem']",
  "details": "save_player is declared pure, but its implementation performs effectful work.",
  "span": {"start": 0, "end": 0},
  "location": {"line": 1, "column": 1},
  "context": {"function": "save_player"},
  "fixes": [
    {
      "id": "remove-pure",
      "kind": "replace_span",
      "applicability": "suggested",
      "description": "Declare the capabilities actually used, or remove the pure markers from the effectful function.",
      "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
    }
  ]
}
```

#### `omni explain invalid_effect.omni`
```json
{
  "schema": "omni.diagnostic",
  "version": "1.0",
  "code": "E-EFFECT-001",
  "category": "effect",
  "severity": "error",
  "message": "Function declared 'pure' but uses ['filesystem']",
  "details": "save_player is declared pure, but its implementation performs effectful work.",
  "span": {"start": 0, "end": 0},
  "location": {"line": 1, "column": 1},
  "context": {"function": "save_player"},
  "fixes": [...],
  "hint": "Function declared 'pure' but uses ['filesystem']"
}
```

#### `omni suggest invalid_effect.omni`
```json
{
  "schema": "omni.suggest",
  "version": "1.0",
  "fixes": [
    {
      "id": "remove-pure",
      "kind": "replace_span",
      "applicability": "suggested",
      "description": "Declare the capabilities actually used, or remove the pure markers from the effectful function.",
      "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""},
      "rank": 1,
      "confidence": 0.7,
      "code": "E-EFFECT-001",
      "message": "Function declared 'pure' but uses ['filesystem']",
      "location": {"line": 1, "column": 1}
    }
  ]
}
```

### Discovered Language Rules
1. **Function Definition Syntax**:
   ```
   fn name(param: Type, ...) -> ReturnType:
       require <condition>
       ensure <condition>
       uses <capability>
       reads <variable>
       writes <variable>
       pure
       <body>
   end
   ```

2. **Built-in Capabilities** (from checker.py):
   - `network`: fetch, http_get, http_post, http_request
   - `filesystem`: open_file, read_file, write_file
   - `database`: db_query
   - `secrets`: read_secret

3. **Effect Enforcement**:
   - `pure` functions cannot use any capabilities
   - Functions using capabilities must declare them with `uses`
   - Module-scope variable reads/writes must be declared with `reads`/`writes`
   - Capability inheritance: when function A calls function B, A must declare B's capabilities

4. **Diagnostic Codes**:
   - `E-EFFECT-001`: Pure function uses capabilities
   - `E-EFFECT-003`: Capability used without declaration
   - `E-EFFECT-004`: Module data accessed via reads/writes without declaration

### Architectural Decisions for RPG Engine
1. **Pure Functions** (mathematical calculations):
   - Damage calculation
   - Hit probability
   - Stat modifiers
   - Status effect duration/stacking calculations

2. **Effectful Functions** (state persistence, I/O):
   - Save/load character state (uses filesystem)
   - Apply damage/healing to character (writes character HP)
   - Apply status effects (writes character status)
   - Use mana for abilities (writes character MP)

3. **Capability Inheritance**:
   - High-level action functions (e.g., `attack`, `cast_spell`) must declare capabilities used by lower-level functions they call
   - Pure helper functions can be called from anywhere

---

## Implementation Plan

### Phase 1: Create source/rpg_engine.omni
- Define Character type with stats, HP, MP, status effects
- Implement pure calculation functions
- Implement effectful action functions with proper capability declarations
- Ensure capability inheritance

### Phase 2: Create tests/test_rpg_engine.py
- Test pure function calculations
- Test effect enforcement
- Test capability inheritance

### Phase 3: Verify with omni check
- `omni check source/rpg_engine.omni` should exit 0
- `omni check invalid_effect.omni` should fail with E-EFFECT-001

### Phase 4: Create RESULTS.md

---

## Running Log

### 2026-08-18 05:35 - Starting Implementation
Created run directory and began investigating compiler behavior.

### 2026-08-18 05:40 - Compiler Analysis Complete
Analyzed invalid_effect.omni diagnostic outputs. Now implementing rpg_engine.omni.