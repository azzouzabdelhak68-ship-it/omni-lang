# Benchmark Reasoning Log - Task 0.2: Task Management & Todo Engine

## Model: Claude 3.5 (Sonnet)
## Run Directory: RUN_001_CLAUDE_3_5
## Started: 2026-08-18

---

## Initial Investigation

### Questions Being Investigated
1. What is the exact OmniScript syntax for custom type definitions?
2. How do List collections work in OmniScript?
3. What are the iteration constructs (for loops)?
4. How does state mutation work (reads/writes)?
5. What built-in functions are available for string manipulation, list operations?
6. How do functions work with `pure` vs `uses` effects?
7. What is the `when app starts` entry point syntax?

### Initial Hypotheses
- OmniScript uses `type` keyword for custom type definitions (like `type Task = { ... }`)
- Lists are created with `[]` or `omnisys.collections.list_push`
- For loops use `for item in list:` syntax
- Functions use `fn name(params) -> ReturnType:` with `end`
- `pure` functions have no side effects, `uses` declares effects
- Module-level state is declared in `when app starts` block

---

## Investigation Steps

### Step 1: Examining Existing OmniScript Examples
Examined `file_organizer.omni` and `inventory.omni` from previous benchmarks.

**Discovered Language Rules:**
- `type Name = { field: Type, ... }` for custom types
- `import OMNISYS.collections` for list/map operations
- `fn name(params) -> ReturnType:` function definition
- `pure` keyword for pure functions (no effects)
- `uses effect_name` for effectful functions
- `reads var1 var2` and `writes var1 var2` for module state access
- `for item in list:` iteration
- `if condition:` / `else if` / `else` / `end` for conditionals
- `show "text"` for output
- `when app starts:` entry point
- `is` for equality comparison
- `less than`, `greater or equal` for comparisons
- String concatenation with `+`
- Map access with `map[key]` syntax
- `omnisys.collections.list_push(list, item)` to add to list
- `omnisys.collections.list_slice(text, start, end)` for substring
- `omnisys.core.length(list)` for length

### Step 2: Testing Basic Syntax with Compiler
Let me create a minimal probe to verify syntax.

---

## Probe 1: Basic Type and List Operations

Creating test file to verify:
- Custom type definition
- List creation and manipulation
- For loop iteration
- Function definitions
- String operations

---

## Errors Encountered and Corrections

### Error: Module state declaration
In `inventory.omni`, module state variables are declared in `when app starts` block but also need to be initialized. The pattern is:
1. Declare variables at module level (implicitly by assignment in `when app starts`)
2. Use `reads`/`writes` in functions that access them
3. Setter functions defined first (analyzer processes in source order)

### Error: Row field access
Row field access (`row.field`) only works on function parameters typed as custom types, inside predicates/capture functions.

### Error: List operations
Lists use `omnisys.collections.list_push(list, item)` to append, not `.push()` method.

---

## Architectural Decisions

### Data Structure Design
```omniscript
type Task = {
    title: Text,
    completed: Boolean,
    priority: Number,    // 1=high, 2=medium, 3=low
    category: Text
}
```

### Function Plan
1. `create_task(title, priority, category) -> Task` - pure factory
2. `add_task(tasks: List, task: Task) -> List` - pure, returns new list
3. `filter_completed(tasks: List) -> List` - pure
4. `filter_active(tasks: List) -> List` - pure
5. `search_by_category(tasks: List, category: Text) -> List` - pure
6. `search_by_title(tasks: List, substring: Text) -> List` - pure
7. `completion_percentage(tasks: List) -> Number` - pure
8. `high_priority_remaining(tasks: List) -> Number` - pure
9. `toggle_task_completion(tasks: List, index: Number) -> List` - pure
10. `format_task_report(tasks: List) -> Text` - pure

### State Management
Since the requirements mention "update individual task completion states cleanly across list collections", I'll use a module-level task list that gets mutated through functions, demonstrating both pure and effectful approaches.

---

## Implementation Plan

1. Create `source/todo_engine.omni` with:
   - Type definitions
   - Pure functions for all operations
   - Module state for task list
   - Effectful functions for state mutation
   - `when app starts` demo

2. Create `tests/test_todo_engine.py` with pytest tests

3. Run verification commands

---

## Next Steps

Create the todo_engine.omni file with the implementation.