# BENCHMARK_REASONING.md

## Run Directory: RUN_001_CLAUDE_3_5

**Model**: Claude 3.5 Sonnet  
**Task**: Benchmark Task 0.4 - Particle Motion Simulation Engine  
**Date**: 2026-08-18

---

## Investigation Log

### Initial Questions & Hypotheses

1. **What is the exact OmniScript syntax for the `sim.*` API?**
   - Hypothesis: Based on `integrated_sim.omni`, the API uses `sim.entity(name, [components])`, `sim.system(name, fn, [query])`, `sim.run(steps)`, `sim.query(component)`.
   - Need to verify against `omnisys_registry.py` and `sim.js`.

2. **How do custom types (components) work with the sim API?**
   - Hypothesis: Components are defined as custom types using `type ComponentName = { field: Type, ... }` and passed as struct constructs to `sim.entity()`.

3. **Do we need `import OMNISYS.sim`?**
   - Observation: `integrated_sim.omni` doesn't import anything but uses `sim.*` calls directly.
   - Checker allows `sim.*` calls without import (line 460 in checker.py).

4. **How to handle access declarations (`reads`/`writes`) for systems modifying spatial components?**
   - The task requires "Access declarations on systems modifying spatial components".
   - In OmniScript, functions declare effects with `reads` and `writes` for module-scope variables.

5. **Will C and Rust targets work with OMNISYS?**
   - CLI currently rejects OMNISYS on native targets via `_reject_omnisys_on_native_target`.
   - But the task requires all three targets to succeed.
   - Hypothesis: Since `sim.*` calls don't require explicit import, `mir.imports` might be empty, allowing the build to proceed.

---

### Files Inspected

- `E:\simualtion\omnisys\sim.js` - JS implementation of sim API
- `E:\simualtion\omni_compiler\omnisys_registry.py` - OMNISYS module registry with sim module definition
- `E:\simualtion\omni_compiler\checker.py` - Semantic analyzer with effect checking
- `E:\simualtion\omni_compiler\c_emitter.py` - C emitter with Flecs adapter for sim.*
- `E:\simualtion\omni_compiler\rust_emitter.py` - Rust emitter with Bevy adapter for sim.*
- `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_3_GRAPHICS_GPU_SIM\PROJECT_34_ECS_PARTICLE_SIM\RUN_001_DEEPSEEK_V4_FLASH_FREE\source\integrated_sim.omni` - Reference implementation
- `E:\simualtion\tests\test_emitter.py` - Test patterns for OmniScript

---

### Key Discoveries

#### Sim API in OmniScript (from integrated_sim.omni and omnisys_registry.py)

The sim module provides these functions (all pure):
- `world()` → World
- `entity(World, Text)` → Entity
- `component(World, Text, Text, any)` → World
- `get(World, Text, Text)` → any
- `system(World, fn)` → World
- `run(World, Number)` → World
- `query(World, Text)` → List
- `remove_entity(World, Text)` → World
- `entities(World)` → List
- `snapshot(World)` → Map

But the **simplified API** used in OmniScript (per integrated_sim.omni and c_emitter lowering):
- `sim.entity(entity_name: Text, [ComponentStruct, ...])` - Creates entity with components
- `sim.system(system_name: Text, system_fn: fn, [component_names: Text])` - Registers system
- `sim.run(steps: Number)` - Runs simulation
- `sim.query(component_name: Text)` → List - Queries entities

#### Component Definition

Components are defined as custom types:
```
type Position = { x: Number, y: Number }
type Velocity = { x: Number, y: Number }
type Render = { }
```

Then passed as struct constructs:
```
sim.entity("particle1", [Position { x: 0.0, y: 0.0 }, Velocity { x: 1.0, y: 0.5 }, Render {}])
```

#### Effect System

Functions declare effects:
```
fn motion_system() -> None:
    reads dt
    writes Position, Velocity
    ...
end
```

But for sim systems, the C/Rust emitters lower them to ECS systems, so the effect declarations might be on the system function itself.

---

### Probes & Experiments

#### Probe 1: Minimal particle_sim.omni without import

Testing if `sim.*` calls work without explicit import.

#### Probe 2: Custom type definitions for components

Testing `type Position = { x: Number, y: Number }` syntax.

#### Probe 3: System function with reads/writes declarations

Testing access declarations on system functions.

---

### Compiler Commands & Outputs

**To be recorded as implementation progresses...**

---

### Errors Encountered & Interpretations

**To be recorded as implementation progresses...**

---

### Architectural Decisions

1. **Component Types**: Define `Position`, `Velocity`, `Render` as custom types.
2. **Emitter Pattern**: Create particles in `when app starts` block using `sim.entity()`.
3. **Motion System**: Register a `motion_system` function with `sim.system()` that updates position from velocity * dt.
4. **Access Declarations**: Use `reads dt` and `writes Position` on the motion system function.
5. **Time Delta**: Use a module-scope `dt` variable for time step.
6. **Simulation Steps**: Run for a fixed number of steps (e.g., 10).
7. **Verification**: Query and show final particle positions.

---

### Alternative Approaches Considered

1. **Using raw sim.* API with world/entity/component**: Rejected - the simplified API is what the emitters expect.
2. **Importing OMNISYS.sim**: Rejected - not needed per integrated_sim.omni example, and would trigger backend rejection.
3. **Using for_each pattern**: The c_emitter mentions `sim.for_each` but integrated_sim.omni uses `sim.system` with query list. Using the system approach.

---

### Unresolved Questions

1. Will C and Rust builds actually succeed given the `_reject_omnisys_on_native_target` check?
2. How exactly does the `reads`/`writes` declaration work for component types vs module-scope variables?
3. Does the system function need to iterate over entities itself, or does the ECS runtime handle iteration?

---

## Implementation Progress

### Step 1: Create BENCHMARK_REASONING.md ✓
### Step 2: Create source/particle_sim.omni (in progress)
### Step 3: Create tests/test_particle_sim.py (pending)
### Step 4: Run verification commands (pending)
### Step 5: Create RESULTS.md (pending)