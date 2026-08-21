# OmniScript Tutorial

Welcome to OmniScript! This tutorial will guide you through writing your first OmniScript programs, from a simple "Hello, World!" to a complete application with effects, UI, and compilation to JavaScript.

## Prerequisites

- Python 3.11+
- Node.js (for running compiled programs)

Install the compiler:

```bash
pip install -e ".[dev]"
```

Verify installation:

```bash
omni --help
```

## 1. Hello, World!

Create a file `hello.omni`:

```omni
when app starts:
    show "Hello, World!"
end
```

Run it:

```bash
omni run hello.omni
```

Output:
```
Hello, World!
```

**Key concepts:**
- `when app starts:` — the entry point of every OmniScript program
- `show` — prints to the console (like `console.log` in JS)

---

## 2. Variables and Types

OmniScript is statically typed. Create `variables.omni`:

```omni
when app starts:
    name = "OmniScript"
    version = 1
    is_awesome = true
    show name
    show version
    show is_awesome
end
```

Run it:
```bash
omni run variables.omni
```

**Types:** `Text`, `Number`, `Boolean`, `None`

---

## 3. Text Interpolation

Use `{...}` inside strings to interpolate expressions:

```omni
when app starts:
    name = "World"
    show "Hello, {name}!"           # "Hello, World!"
    show "2 + 2 = {2 + 2}"          # "2 + 2 = 4"
    show "Is it awesome? {true}"    # "Is it awesome? true"
end
```

---

## 4. Functions

Define reusable functions with `fn`:

```omni
fn greet(name: Text) -> Text:
    pure
    return "Hello, {name}!"
end

fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    show greet("OmniScript")
    show add(10, 20)
end
```

**Key points:**
- `pure` — declares no side effects (no I/O, no state mutation)
- Type annotations on parameters and return type
- `return` exits the function

---

## 5. Conditionals

```omni
fn max(a: Number, b: Number) -> Number:
    pure
    if a > b:
        return a
    else:
        return b
    end
end

when app starts:
    show max(5, 10)   # 10
    show max(15, 3)   # 15
end
```

---

## 6. Loops

```omni
when app starts:
    total = 0
    for i in range(5):
        total = total + i
    end
    show total          # 10 (0+1+2+3+4)
end
```

---

## 7. Effects and Capabilities

OmniScript tracks side effects through **capabilities**. Any function that performs I/O, uses timers, accesses the filesystem, etc., must declare its effects:

```omni
fn read_config(path: Text) -> Text:
    uses filesystem
    # ... read file ...
    return "config"
end

fn fetch_data(url: Text) -> Text:
    uses network
    # ... HTTP request ...
    return "data"
end
```

Available capabilities:
- `filesystem` — file read/write
- `network` — HTTP requests
- `database` — SQLite access
- `timer` — setTimeout/setInterval
- `dom` — browser DOM access
- `panic` — program termination

The `pure` keyword means **no capabilities** (no side effects).

---

## 8. UI Blocks

Build interactive web UIs with the `UI:` block:

```omni
when app starts:
    count = 0

    UI:
        div:
            h1 "Counter: {count}"
            button "Increment":
                click:
                    count = count + 1
                end
            end
        end
    end
end
```

This compiles to a self-contained HTML file with live reactivity!

---

## 9. Compiling to JavaScript

Compile your program to a standalone HTML file:

```bash
omni build hello.omni --target js
```

This creates `hello.html` that you can open in any browser!

---

## 10. Type Checking

Check your program for type and effect errors without running:

```bash
omni check hello.omni
```

---

## 11. Complete Example: Actor System

Here's a complete example using the actor system (`examples/actors.omni`):

```omni
import omnisys.async

when app starts:
    cluster = async.cluster_create("demo")
    async.cluster_add_node(cluster, "node1")

    counter = async.spawn(cluster, "node1", "counter", counter_behavior, 0)
    async.send(counter, "inc")
    async.send(counter, "inc")
    async.send(counter, "get")
    async.run(cluster)
end

fn counter_behavior(state: Number, msg: Text, ctx) -> Number:
    pure
    if msg is "inc":
        return state + 1
    end
    if msg is "get":
        show "Count: {state}"
        return state
    end
    return state
end
```

Run it:
```bash
omni run examples/actors.omni
```

---

## 12. Next Steps

- Read the full specification: `OMNI_SPEC.md`
- Explore the standard library: `docs/omnisys/`
- Check out more examples in `examples/`
- Learn about the 3D scene system: `docs/omnisys/scene/README.md`

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `omni check file.omni` | Type-check and effect-check |
| `omni run file.omni` | Compile and run (requires Node.js) |
| `omni build file.omni --target js` | Compile to HTML |
| `omni fmt file.omni` | Format source code |
| `omni verify file.omni` | Prove contracts with SMT solver |
| `omni explain file.omni` | Explain an error |
| `omni lsp` | Start Language Server |

---

Happy coding with OmniScript! 🚀