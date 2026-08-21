# Install OmniScript and run your first .omni program

This tutorial takes you from zero to a running program: you'll install the compiler from GitHub Releases, write a small `.omni` file, pass static checking, and generate JavaScript from OMNI MIR. You need Python 3.11 or newer, plus [Node.js](https://nodejs.org) if you want to execute the result.

## 1. Install the compiler

Download the wheel for the latest release and install it with pip. No source build required:

```bash
pip install https://github.com/azzouzabdelhak68-ship-it/omni-lang/releases/download/v0.1.0/omni_compiler-0.1.0-py3-none-any.whl
```

Confirm the `omni` command is on your path:

```bash
omni --version
```

## 2. Write your first program

Create a file named `hello.omni`. One `.omni` file is a complete application: logic, contracts, and UI live together.

```text
# Hello OmniScript: your first .omni program.
# Every function declares its effect set. `pure` means no side effects:
# if this body touched the network or files, the compiler would reject it.

fn greet(name: Text) -> Text:
    pure
    return "Hello, {name}! OmniScript compiled you."
end

when app starts:
    message = greet("world")
    show message
end

UI:
<div class="card">
    <h1>{message}</h1>
</div>
end
```

The `pure` line declares this function's effect set. In OmniScript every side effect (network, file system, panic) must be declared; the compiler rejects undeclared ones as compile errors. That's the effect system at work, and it's why AI-generated or hand-written code can be checked before it ever runs.

## 3. Check it statically

Run the checker. It type-checks the program, verifies declared effects against actual calls, and reports diagnostics with suggested fixes:

```bash
omni check hello.omni
```

You should see a single OK line. If something's wrong, the diagnostic names the span and often proposes a fix you can apply directly.

## 4. Generate JavaScript

Build the program for a target. The compiler lowers your code to OMNI MIR, its typed intermediate representation, then an emitter generates target code from that IR:

```bash
omni build hello.omni --target js
```

This writes `hello.html`, a self-contained page with your compiled app and live-link UI bindings. The same MIR feeds other backends (`--target c`, WASM), which is how one `.omni` source reaches browser, server, and native targets without rewrites.

## 5. Run it

Execute the program directly. This compiles to JavaScript and runs it under Node.js:

```bash
omni run hello.omni
```

Expected output:

```text
Hello, world! OmniScript compiled you.
```

## Where to go next

- **Prove contracts**: add `require`/`ensure` assertions and run `omni verify`, which discharges proof obligations with the Z3 SMT solver.
- **Borrow capabilities**: read about `borrows` clauses in [the spec](../OMNI_SPEC.md), the capability-system mechanism for granting network access for exactly one call.
- **See the language in full**: [OMNI_SPEC.md](../OMNI_SPEC.md) defines grammar, effects, MIR, and each backend.
- **Browse bigger programs**: [examples/actors.omni](../examples/actors.omni) demonstrates actor-style distributed messaging.
