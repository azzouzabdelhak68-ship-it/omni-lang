# 🌌 OmniScript

**A programming language designed for AI-generated software that can be statically checked before execution.**

[Try it](docs/getting-started.md) · [Documentation](docs/INDEX.md) · [Specification](OMNI_SPEC.md) · [Architecture](docs/architecture/README.md)

---

## Why OmniScript?

AI can generate code quickly. The problem is knowing whether that code is actually safe, correct, and executable.

OmniScript puts verification into the language itself: side effects are explicitly declared, contracts are proved before compilation, and code is lowered to a typed intermediate representation (OMNI MIR) before targeting multiple runtimes.

```text
.omni
  ↓
Parser + Type Checker
  ↓
Effect & Contract Analysis
  ↓
OMNI MIR
  ↓
JavaScript · C · WASM · Rust
```

---

## Example

One `.omni` file describes logic, declared effects, and contracts:

```omni
# Declares pure calculation: compiler guarantees zero side effects
fn calculate_tax(subtotal: Number) -> Number:
    pure
    require subtotal >= 0
    return subtotal * 0.15
end

# Declares network capability access explicitly
fn sync_invoice(id: Text) -> Text:
    uses network
    return http_get("https://api.example.com/invoices/{id}")
end
```

---

## What is actually working?

* **JavaScript**: ✅ Shipping (`omni build app.omni --target js`)
* **C99 (Native)**: ✅ Shipping (`omni build app.omni --target c`)
* **WebAssembly**: ⚠️ Experimental (requires `clang`)
* **Rust / Bevy**: 🚧 Stub
* **Python**: 📋 Specification only

> **Test Suite**: 622 passed, 3 skipped · 90.44% branch coverage

---

## Why it is different

* **Checked Effects**: Functions explicitly declare `network`, `file`, or `pure` constraints. Undeclared side effects trigger compile errors.
* **Unified Intermediate Representation (OMNI MIR)**: A single canonical AST/IR feeds web, native, and embedded emitters.
* **AI-Oriented Language Design**: Strict, unambiguous grammar designed for high-precision model generation and static verification.
* **Multiple Compilation Targets**: Write once in `.omni`, compile to JavaScript, native C, or WebAssembly.

---

## Documentation & deep dives

* [Getting Started Guide](docs/getting-started.md)
* [Language Specification](OMNI_SPEC.md)
* [Architecture Overview](docs/architecture/README.md)
* [Wiki & Project Story](https://github.com/azzouzabdelhak68-ship-it/omni-lang/wiki)
* [Language Comparisons](https://github.com/azzouzabdelhak68-ship-it/omni-lang/issues/10)

---

*OmniScript is an experimental research project.*
