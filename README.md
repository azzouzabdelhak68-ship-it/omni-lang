# OmniScript

> An **AI-first** programming language defined by a single spec, compiled through an intermediate representation (OMNI MIR) to four back-ends: JavaScript, Native (C + Flecs ECS), WebAssembly, and Python.

[![CI](https://github.com/azzouzabdelhak68/omniscript-lang/actions/workflows/ci.yml/badge.svg)](https://github.com/azzouzabdelhak68/omniscript-lang/actions)
[![Docs](https://github.com/azzouzabdelhak68/omniscript-lang/actions/workflows/docs.yml/badge.svg)](https://github.com/azzouzabdelhak68/omniscript-lang/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%252B-blue.svg)](https://www.python.org/downloads/)

---

## 🌟 Core Philosophy

OmniScript is designed from first principles to be **bulletproof for AI agents** and **delightful for humans**:
1. **Unified Syntax & Universal Blocks**: Every block (conditionals, functions, UI, 3D scenes) follows the exact same rule: header, standalone colon (`:`), body, and `end`. Zero indentation ambiguity.
2. **Checked Effects (MANDATORY)**: Functions explicitly declare capabilities (`uses network`, `reads file`, `pure`). The compiler enforces these as truth—side effects cannot slip past unnoticed.
3. **Reactive Live-Link UI (`UI:`)**: A single `.omni` file is a complete app. Logic variables bind to HTML slots automatically and batch-update at the end of blocks.
4. **Built-in 3D Engine (`scene:`)**: Three.js powered 3D scenes out of the box with live-linked attributes (`box`, `sphere`, `light`, `camera`).
5. **Multi-Backend Compilation**: Write once, compile and run across JS (Node/Bun/browser), Native (C + Flecs ECS), WebAssembly (WASI/browser), and Python (CPython/Pyodide).
6. **The `omni` Compiler API**: Machine-readable diagnostics (`omni.diagnostic`) and symbol interrogation (`omni inspect symbol`) built specifically for AI tool use.

---

## 🚀 Quick Example (`app.omni`)

```omni
# A complete OmniScript app with logic, UI, and state

when app starts:
    count = 0
end

fn increment() -> None:
    pure
    count = count + 1
end

UI:
<div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
    <h1>Counter App</h1>
    <p>Current count: <strong>{count}</strong></p>
    <button click="increment">Increment</button>
</div>
end
```

---

## 🛠️ The `omni` CLI Tool

```bash
# Check syntax, types, and effects
omni check app.omni

# Run the app (via JS / Node runtime)
omni run app.omni

# Interrogate symbols for AI agents / tooling
omni inspect symbol app.omni increment

# Verify assertion contracts statically via Z3 SMT solver
omni verify app.omni

# Build for specific target backends (native, web, js, python, wasm)
omni build app.omni --target js
```

---

## 📂 Repository Structure

```
omniscript-lang/
├── omni_compiler/     # Compiler frontend, MIR, type checker, effect analyzer, emitters
│   ├── lexer.py       # Universal colon tokenizer
│   ├── parser.py      # EBNF-compliant block parser
│   ├── checker.py     # Name resolution, type checking & effect enforcement
│   ├── mir.py         # OMNI MIR serializable representation
│   ├── c_emitter.py   # C99 + Flecs ECS emitter
│   ├── rust_emitter.py# Rust + Bevy ECS emitter
│   ├── wasm_emitter.py# WebAssembly emitter
│   ├── smt.py         # Z3 SMT contract verification
│   ├── ai_tools.py    # AI tooling (suggest fix, generate test, trace execution)
│   └── cli.py         # The `omni` CLI tool
├── packages/          # OMNISYS modular standard library
├── docs/              # Comprehensive architecture and module documentation
├── examples/          # Sample .omni applications
├── tests/             # Test suite (pytest + hypothesis property tests)
├── OMNI_SPEC.md       # The single official language specification
└── OMNI_HISTORY.md    # The story of how OmniScript was created
```

---

## 📖 Documentation & Spec

- **Language Specification**: Read [OMNI_SPEC.md](OMNI_SPEC.md) for the complete normative definition.
- **Story & Origins**: Read [OMNI_HISTORY.md](OMNI_HISTORY.md) for how the language came to be.
- **Documentation Index**: Browse [docs/INDEX.md](docs/INDEX.md) for architecture, decisions, and OMNISYS module guides.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.
