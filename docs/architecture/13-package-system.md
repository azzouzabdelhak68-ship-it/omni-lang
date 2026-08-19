# OMNISYS Package / Module System

**Deliverable §14N.** How OMNISYS packages, the `import` model, the registry,
and dependency resolution work together.

---

## 1. The Two Meanings of "Module"

1. **Language module** — an `import OMNISYS[.sub]` namespace, resolved by the
   compiler registry (`omni_compiler/omnisys_registry.py`) and carried through
   the MIR. See [`14-import-behavior.md`](14-import-behavior.md).
2. **Package** — a distributable unit of code in the monorepo
   (`packages/omnisys-*`), with its own `src/`, `tests/`, and research doc.

## 2. Monorepo Layout

```
packages/
├── omnisys-core/          # OMNISYS.core (+ collections/serde/error)
├── omnisys-collections/
├── omnisys-async/
├── omnisys-fs/
├── omnisys-serde/
├── omnisys-error/
├── omnisys-test/
├── omnisys-ui/
├── … (one per module, phases 1–6)
```

Each package is self-contained: `src/` (Python/OmniScript implementation),
`tests/` (unit + property + conformance), and a research doc produced before
implementation (spec §17.8).

## 3. Runtime Files

The JS runtime lives under `omnisys/*.js` (one file per module), inlined by
the JS emitter in dependency order (`js_files_for`). They are UMD-style
IIFEs attaching to the global `omnisys` namespace, so the same file works
inlined in a browser bundle or `require()`d in Node.

## 4. Dependency Resolution

- The registry's `js_deps` declares module dependencies.
- `js_files_for(imports)` returns implementation files **in dependency order,
  deduplicated** — deps first.
- The umbrella `import OMNISYS` inlines only `core`; sub-imports pull their
  transitive closure.

## 5. Lazy Loading & Dead-Code Elimination

The umbrella import MUST NOT force compilation of all subsystems (spec §17.2).
Unused subsystems do not increase binary size, startup time, or build cost.
The emitter inlines only the modules actually imported, in order.

## 6. `omni pkg` (v6 Phase 6)

The package manager (`omnisys-pkg`) adds registry + git dependency handling,
resolution, and installation on top of this foundation — the language
`import` model stays unchanged.

## 7. Quality Gates Per Package

Every package ships with:

- unit + property-based tests (hypothesis)
- conformance tests against the registry contract
- mutation score ≥ 90%, branch coverage ≥ 95%, mypy `--strict`, ruff clean

See [`19-quality-gates.md`](19-quality-gates.md).