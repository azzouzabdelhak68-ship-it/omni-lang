# Benchmark Reasoning Log — Project 1.2 Filesystem File Organizer

## Run Directory
`E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_1_FOUNDATIONS\PROJECT_12_FILESYSTEM_FILE_ORGANIZER\RUN_001_DEEPSEEK_V4\`

## Model
DeepSeek V4 (via opencode/nemotron-3-ultra-free)

---

## Phase 1: Investigation & Language Discovery

### Initial Questions & Hypotheses

**Q1: What is the OmniScript syntax for filesystem operations?**
- Hypothesis: Based on `omnisys_registry.py`, OMNISYS.fs functions are called as `omnisys.fs.read_file(path)`, `omnisys.fs.write_file(path, text)`, etc.
- All I/O functions require `uses filesystem` effect declaration.
- Path helpers (`join_path`, `basename`, `dirname`) are pure and don't require effects.

**Q2: How do I declare effects in OmniScript?**
- From test fixtures: `uses network`, `reads cache`, `writes cache`, `pure`
- Filesystem operations need `uses filesystem` (or possibly `reads filesystem` / `writes filesystem` based on docs)

**Q3: What are the available OMNISYS.fs functions?**
From registry and Python implementation:
- I/O (all declare `filesystem` effect): `read_file`, `write_file`, `append_file`, `delete_file`, `file_exists`, `file_size`, `list_dir`, `make_dir`, `remove_dir`, `rename_file`, `copy_file`
- Pure path helpers: `join_path`, `basename`, `dirname`

**Q4: How to import OMNISYS.fs?**
- `import OMNISYS.fs` (confirmed from test_imports.py)

**Q5: What is the type system?**
- Basic types: `Text`, `Number`, `Boolean`, `List`, `Map`, `Option`, `Result`, `Error`
- Function types: `fn(Text) -> Text`, `fn(Text, Text) -> Text`, etc.
- Custom types via `type Name = { ... }`

**Q6: How to structure the file organizer?**
Requirements from TASK.md:
1. Path & Directory Model - represent filesystem paths and directory trees in memory
2. Sync Planning - compare two directory trees, compute change plan (create, update, delete, skip)
3. Safe Write Operations - stage changes before commit, atomic writes
4. Organization Rules - naming/extension-based rules to sort files into categorized subdirectories
5. Capability Policy - declare all filesystem capabilities at function boundaries; pure planning functions must remain side-effect-free

### Files Inspected

1. `E:\simualtion\omni_compiler\omnisys_registry.py` - OMNISYS module registry with effects
2. `E:\simualtion\packages\omnisys-fs\src\omnisys_fs\__init__.py` - Python reference implementation
3. `E:\simualtion\omnisys\fs.js` - JavaScript runtime implementation
4. `E:\simualtion\tests\test_imports.py` - Effect enforcement tests
5. `E:\simualtion\tests\fixtures\valid\02_function_with_effects.omni` - Effect declaration syntax
6. `E:\simualtion\omni_compiler\cli.py` - CLI commands (check, run, build)
7. `E:\simualtion\tests\test_checker.py` - Effect enforcement patterns

### Key Language Rules Discovered

1. **Import syntax**: `import OMNISYS.fs` at module level
2. **Effect declarations**: Inside function body, before any statements:
   - `uses filesystem` - for functions that perform I/O
   - `pure` - for pure functions (no side effects)
   - `reads X`, `writes X` - for state effects (UI, cache, etc.)
3. **Function syntax**: `fn name(params) -> ReturnType: ... end`
4. **Type annotations**: `param: Type`, `-> ReturnType`
5. **Control flow**: `if condition: ... end`, `for item in list: ... end`
6. **Entry point**: `when app starts: ... end`
7. **Variables**: `name = value` (type inferred)
8. **String interpolation**: `"{variable}"` in strings
9. **List literals**: `[1, 2, 3]`, `["a", "b"]`
10. **Map/Record literals**: `{ key: value, ... }`
11. **Custom types**: `type Name = { field: Type, ... }`

### Capability Gaps Identified (from TASK.md)

The TASK.md notes these APIs are missing/unlocked with OMNISYS.fs v6:
- `Path`, `File`, `Dir`, `Watch`, `Temp`, atomic write APIs

**Current available APIs (confirmed working):**
- `read_file(path: Text) -> Text`
- `write_file(path: Text, text: Text) -> Text`
- `append_file(path: Text, text: Text) -> Text`
- `delete_file(path: Text) -> Boolean`
- `file_exists(path: Text) -> Boolean`
- `file_size(path: Text) -> Number`
- `list_dir(path: Text) -> List`
- `make_dir(path: Text) -> Boolean`
- `remove_dir(path: Text) -> Boolean`
- `rename_file(old_path: Text, new_path: Text) -> Boolean`
- `copy_file(src: Text, dst: Text) -> Boolean`
- `join_path(a: Text, b: Text) -> Text` (pure)
- `basename(path: Text) -> Text` (pure)
- `dirname(path: Text) -> Text` (pure)

**Missing APIs (need to simulate in data structures):**
- `Path` type - will represent as Text strings
- `File` type - will represent as Map `{ path: Text, size: Number, exists: Boolean }`
- `Dir` type - will represent as Map `{ path: Text, children: List }`
- `Watch` - not available, will skip
- `Temp` - not available, will simulate with temporary directory paths
- Atomic write - will simulate by writing to temp file then rename

---

## Phase 2: Design Decisions

### Architecture

The file organizer will have these components:

1. **Pure Planning Functions** (no effects):
   - `build_dir_tree(path: Text) -> Map` - Build in-memory directory tree
   - `compute_sync_plan(source_tree: Map, target_tree: Map) -> List` - Compute diff
   - `compute_org_plan(source_path: Text, rules: List) -> List` - Compute organization moves
   - `order_operations(plan: List) -> List` - Topological sort for safe execution order

2. **Effectful Execution Functions** (`uses filesystem`):
   - `execute_sync_plan(plan: List) -> Boolean` - Apply sync operations
   - `execute_org_plan(plan: List) -> Boolean` - Apply organization moves
   - `atomic_write_file(path: Text, content: Text) -> Boolean` - Write via temp + rename

3. **Data Structures**:
   - Directory Tree: `{ path: Text, type: "dir", children: List<FileNode|DirNode> }`
   - File Node: `{ path: Text, type: "file", size: Number, hash: Text }`
   - Sync Operation: `{ op: "create"|"update"|"delete"|"skip", src: Text, dst: Text }`
   - Org Rule: `{ pattern: Text, target_dir: Text }` (e.g., `*.jpg` -> `Images/`)

### Effect Boundary Strategy

- **Pure functions** (planning, computation): No `uses filesystem`, only operate on in-memory data structures
- **Effectful functions** (execution): `uses filesystem` declared, call `omnisys.fs.*` functions
- **Main entry point**: `when app starts:` - can call effectful functions but must not declare effects itself

---

## Phase 3: Implementation Plan

### Step 1: Create `source/file_organizer.omni`

Structure:
```omni
import OMNISYS.fs
import OMNISYS.core
import OMNISYS.collections

# Type definitions
type FileNode = { path: Text, type: Text, size: Number }
type DirNode = { path: Text, type: Text, children: List }
type SyncOp = { op: Text, src: Text, dst: Text }
type OrgRule = { pattern: Text, target_dir: Text }
type Plan = List

# Pure planning functions
fn join_path(a: Text, b: Text) -> Text:
    pure
    return omnisys.fs.join_path(a, b)
end

fn basename(path: Text) -> Text:
    pure
    return omnisys.fs.basename(path)
end

fn dirname(path: Text) -> Text:
    pure
    return omnisys.fs.dirname(path)
end

fn build_dir_tree(root_path: Text) -> Map:
    pure
    # ... recursive tree building using omnisys.fs.list_dir, file_exists, file_size
    # Wait - these are effectful! Need to separate.
end

# Actually, the planning functions CANNOT call omnisys.fs.* because they're pure.
# So we need to pass filesystem data as parameters, or have a separate effectful
# "scan" phase that returns data structures to pure planning functions.

# Revised design:
# 1. scan_directory(path: Text) -> Map (uses filesystem) - reads actual FS
# 2. build_tree_from_listing(listing: List, root: Text) -> Map (pure) - builds tree from scan results
# 3. compute_diff(tree1: Map, tree2: Map) -> List (pure) - computes sync plan
# 4. compute_org_moves(tree: Map, rules: List) -> List (pure) - computes org plan
# 5. execute_plan(plan: List) -> Boolean (uses filesystem) - applies changes
```

### Step 2: Create `tests/test_file_organizer.py`

Test the Python-side logic that mirrors the OmniScript implementation, or test the compiled output.

---

## Phase 4: Implementation (In Progress)

### Probe 1: Test basic OMNISYS.fs import and effect declaration

Let me create a minimal test file to verify the compiler accepts the syntax.

---

## Verification Log

### Test 1: Minimal OMNISYS.fs usage