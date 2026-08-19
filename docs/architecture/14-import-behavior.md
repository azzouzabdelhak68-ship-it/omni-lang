# `import OMNISYS` Behavior

**Deliverable §14O.** The exact semantics of the OMNISYS import model, as
enforced by the compiler.

---

## 1. Syntax

```omni
import OMNISYS                    # umbrella → resolves to core
import OMNISYS.ui                 # modular sub-import
import OMNISYS.db
```

Imports are ordinary statements at the top of a file. They are parsed into the
AST, carried into the MIR (`mir.imports`), and survive MIR JSON round-trips.

## 2. Resolution Rules

`resolve_import(path)` in `omnisys_registry.py`:

| Import path | Result |
|-------------|--------|
| `import foo` | `E-IMPORT-001` — unknown root |
| `import OMNISYS` | `core` (umbrella) |
| `import OMNISYS.core` | `core` |
| `import OMNISYS.<module>` | that module (18 registered names) |
| `import OMNISYS.wat` | `E-IMPORT-002` — unknown module |

`core` is the implicit root: `collections`, `serde`, `error` are internal
submodules, never separate top-level imports.

## 3. Enforcement

- **Use-before-import** — calling `omnisys.collections.list_join` without an
  import yields `E-IMPORT-003`.
- **Effect inheritance** — a call to an OMNISYS function inherits its declared
  capabilities transitively; undeclared effects yield `E-EFFECT-003`, and a
  `pure` function touching an effectful module yields `E-EFFECT-001`.
- **Backend gate** — building for native/WASM targets rejects OMNISYS imports
  with `E-BACKEND-001` until the runtime lands on those lanes; `--target js`
  inlines it.

## 4. Emitter Inlining

The JS emitter:

1. collects the imported modules and their transitive `js_deps`,
2. returns implementation files in dependency order (deps first,
   deduplicated),
3. inlines the file **contents** (no path leaks), wrapped as the "OMNISYS
   runtime".

A file with no imports emits no runtime.

## 5. Lazy & Minimal

The umbrella import inlines only `core`, never the whole platform — unused
subsystems add no bytes (spec §17.2). Sub-imports pull only their closure.

## 6. Tests

`tests/test_imports.py` locks all of the above: resolution, diagnostics,
effect enforcement, emitter inlining, MIR round-trip, and the CLI per-backend
gate.