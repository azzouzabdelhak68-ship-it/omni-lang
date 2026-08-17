# OMNISCRIPT SPECIFICATION v1.0

> Status: Draft
> This document is the **single official definition** of the OmniScript language.
> Every engine that claims to run OmniScript MUST behave identically per this spec.
> Normative words: **MUST**, **MUST NOT**, **SHOULD**, **MAY**.

---

## 0. Core Philosophy

OmniScript is an **AI-first** programming language defined entirely by THIS
spec. Its logic core is OmniScript itself (see Section 13 — one front-end, one
OMNI MIR, three back-ends). HTML/CSS/WebGL is its interface. A single `.omni`
file is a complete app.

```
LANGUAGE_NAME = "OmniScript"
FOUNDATION    = ["OmniScript spec + OMNI MIR", "HTML/CSS/WebGL (UI & 3D Graphics)"]
```

Core features:
1. **Unified syntax** — OmniScript logic at the top, UI/3D layout at the bottom under `UI:`.
2. **Reactive data binding** — logic variables update the UI instantly (live links).
3. **Built-in 3D engine** — Three.js powered out of the box via a `scene:` block.

Purpose:
- Simple personal tools and mini-apps (no server setup).
- A learning tool with instant visual results.
- Big serious applications.
- Written, verified, and maintained by AI agents better than existing languages.

---

## 1. Overview

OmniScript's logic core is the OmniScript language itself, defined by this
spec (English-like, block-structured). HTML/CSS/WebGL is its interface.
A single `.omni` file is a complete app.

The two parts of a program:
1. **Logic part** — statements and functions (English-like, block-structured).
2. **Screen part** — HTML markup with value slots and click actions, marked by `UI:`.

---

## 2. File Format

- File extension: `.omni`
- Encoding: UTF-8
- Line endings: LF or CRLF (MUST both be accepted)
- One file = one app (MUST). No import of other `.omni` files in v1.0.

---

## 3. Lexical Structure

### 3.1 Whitespace
Whitespace (spaces, tabs) is **NOT significant** for structure. Blocks are
delimited by keywords, never by indentation. Consecutive spaces/tabs are
collapsed before parsing. Blank lines are ignored.

### 3.2 Comments
- Line comment: `#` to end of line
```
# this is a comment
```

### 3.3 Identifiers
- Names of variables and functions.
- MUST start with a letter or underscore.
- MAY contain letters, digits, underscores.
- Are case-sensitive: `name` and `Name` are different.
```
name
_private_var
total2
```

### 3.4 Keywords
The following words are reserved and MUST NOT be used as identifiers:

```
when  end  if  else  then  fn  return  show  uses  reads
writes  pure  UI  scene  require  ensure  and  or  not
is  true  false
```

The colon `:` is ALWAYS a separate token — it is never fused into a keyword.
`UI`, `scene`, `when`, `if`, `fn`, and every other block opener are ordinary
keywords followed by a standalone `:` token (see Section 4).

### 3.5 Literals
- **Number**: `0`, `42`, `3.14`, `-7`, `1e3`
- **Text**: double quotes `"hello"` or single quotes `'hello'`; a Text literal
  MAY contain `{expression}` slots (see Section 6.5)
- **Boolean**: `true`, `false`
- **List**: `[1, 2, 3]`
- **Empty value**: `none`

---

## 4. Blocks

A block opens with a block header, a standalone `:` token, and closes with the
keyword `end`. The `:` is a separate token — it is never fused into the header
keyword. The grammar has exactly ONE block production:

```
block_header ':' statement* 'end'
```

There are zero exceptions: `when`, `if`, `fn`, `UI`, `scene`, and every other
block opener all follow this same rule.

```
when app starts:
    # body
end

fn add(a: Number, b: Number) -> Number:
    return a + b
end

UI:
<h1>Hello</h1>
end
```

Rules:
- Every block MUST have exactly one matching `end`.
- `end` MUST be on its own line.
- Nesting is allowed. The `end` closes the most recently opened block.

---

## 5. Statements

### 5.1 Variable assignment
```
name = value
```
- Assigns value to name.
- `=` is assignment. `is` is equality comparison (see 6.2).

### 5.2 App entry point
```
when app starts:
    ...
end
```
- MUST appear at most once per file.
- Runs once when the app launches.

### 5.3 Conditional
```
if condition:
    ...
end

if condition:
    ...
else:
    ...
end
```
- `else` binds to the nearest open `if`.
- Conditions use comparison operators (section 6.2).

### 5.4 Function definition
```
fn name(param: Type, ...) -> ReturnType:
    uses capability1 capability2
    reads resource
    writes resource
    return value
end
```
- Parameters MUST have a type.
- Return type is required after `->`.
- A trailing `:` is required after the signature (one block rule, Section 4).
- The body MUST end with `end`.

### 5.5 Function call
```
name(arg1, arg2)
```
- Function calls are expressions.

### 5.6 Return
```
return value
```
- Returns from the enclosing function.
- MUST appear inside a `fn` block.

### 5.7 Show (screen output)
```
show expression
```
- Pushes `expression` value into the current screen slot context.
- Behavior is engine-consistent: `show "hi"` always displays `hi`.

---

## 6. Expressions

### 6.1 Arithmetic (uses normal symbols)
- `+` addition, `-` subtraction, `*` multiplication, `/` division
- Operators MUST be non-overloaded: each operator has exactly ONE meaning
  regardless of operand types.

### 6.2 Comparison (uses words)
- `is` — equality
- `is not` — inequality
- `greater than`, `less than`, `greater or equal`, `less or equal`

### 6.3 Logic (uses words)
- `and`, `or`, `not`

### 6.4 Precedence
1. `not`
2. `*` `/`
3. `+` `-`
4. comparison (`is`, `greater than`, ...)
5. `and`
6. `or`
7. `=` (assignment, lowest)

### 6.5 Text interpolation (string building)
The ONLY way to build a string is interpolation: a Text literal may contain
`{expression}` slots, which are replaced with the value of the expression at
evaluation time.

```
message = "Hello, {name}"          # identifier
total   = "Sum: {a + b}"           # arbitrary expression (statically checked)
```

- `{...}` accepts ANY expression, not only identifiers. It is statically
  type-checked; the result MUST be a value that renders as text.
- `+` is NEVER overloaded: it is Number-only (Section 6.1). Text building is
  always interpolation — one way, one meaning.
- UI slots (Section 9.2) and logic interpolation share the SAME `{...}`
  mechanism — one "insert value" idiom across the whole language.
- Runtime-accumulated strings (building a string across a loop/List) require a
  builtin function, not an operator. `join(list: List, sep: Text) -> Text` is
  RESERVED for this and MUST be provided once loops ship (Section 16).

---

## 7. Types

### 7.1 Built-in types
| Type | Example |
|------|---------|
| `Number` | `42`, `3.14` |
| `Text` | `"hello"` |
| `Boolean` | `true` |
| `List` | `[1, 2]` |
| `None` | `none` |

### 7.2 Declared types
- Parameters and returns MUST be typed.
- Type checking is performed by the compiler (static), not deferred to runtime.

---

## 8. Checked Effects / Capabilities (MANDATORY)

### 8.1 Declaration
Every function MUST declare the capabilities it uses, using keyword lines
after the function signature and before the body statements:

```
uses <capability> ...      # capabilities it may invoke
reads <resource> ...       # resources it may read
writes <resource> ...      # resources it may write
```

`pure` is a shorthand for "uses nothing, reads nothing, writes nothing".

### 8.2 Capability vocabulary
`network`, `filesystem`, `database`, `camera`, `microphone`, `GPU`, `process`, `secrets`

### 8.3 Per-back-end capability check (MANDATORY)
Each back-end declares which capabilities it can provide (see Section 13.3).
A program compiles for a target back-end ONLY IF every capability it declares
is provided by that target:
- Example: `process` is not available in the browser lane. A program targeting
  the browser that declares `uses process` MUST fail to compile, with a
  friendly explanation and a suggested fix (e.g. "target the native back-end").
- A capability may be declared in the source but excluded from a target at
  compile time, producing a clear, actionable error rather than a runtime crash.
- The capability set actually available is determined by the target back-end
  selected at build time, never guessed at runtime.

### 8.4 Enforcement (MUST)
- If a function's implementation performs an action not covered by its
  declarations, the compiler MUST reject the program with an error.
- The declaration is **truth**, not documentation. A `pure` function that
  performs network I/O MUST fail to compile.
- A function that calls another function inherits (transitively) the callee's
  capabilities for the purpose of enforcement.

### 8.5 Assertion contracts (v1.0 — runtime tier)
"Contracts" are split into two tiers. THIS tier ships in v1.0; the SMT tier is
reserved for future versions (Section 16).

- `require <boolean-expression>` — a precondition checked at function entry.
- `ensure <boolean-expression>` — a postcondition checked at function exit.

```
fn divide(a: Number, b: Number) -> Number:
    require b is not 0
    pure
    return a / b
end
```

Rules:
- `require` MUST appear before the function body statements.
- `ensure` MAY appear after the body, before `end`.
- On violation, the program panics with a friendly error naming the failed
  assertion and the function.
- These are runtime assertions (checked per-call), NOT static proofs. They are
  cheap: equivalent to an `if not condition: error(...)` inserted at the
  function boundary, so they are trivial across all four back-ends.

### 8.6 SMT-style verification (reserved)
Static, proof-based verification of contracts (proving `require`/`ensure`
hold BEFORE runtime) is research-grade and NOT in v1.0. It remains reserved
(Section 16). The naming collision is resolved by tier, not by renaming: the
v1.0 tier is "assertion contracts" (§8.5), the future tier is "SMT
verification" (§16).

---

## 9. The Screen Part (UI)

### 9.1 Marker
The screen part is a `UI:` block (the `UI` keyword, a standalone `:` token,
HTML content, then `end`):

```
UI:
<h1>{greeting}</h1>
end
```

- The logic part MUST precede `UI:`.
- Everything between `UI:` and its `end` is HTML.
- `UI` follows the single block rule (Section 4) — no special lexing.

### 9.2 Value slots
- Syntax: `{expression}` inside HTML text or attributes.
- At render time the slot is replaced with the current value of the expression.
- Slots are live links (section 9.4).
- The SAME `{...}` mechanism as logic interpolation (Section 6.5) — one idiom.

### 9.3 Click actions
- Syntax: `click="function_name"` attribute on an element.
- Clicking the element calls the named function in the logic part.
- The function MUST exist, else a compile-time error.

### 9.4 Live links (MUST)
- When a logic variable referenced by a slot changes, the screen MUST update
  automatically without reload.
- The tool MUST be able to report which code line feeds which slot.

### 9.4a Live-link batching (MUST)
The screen re-renders **once, at the end of each top-level block** (a function
call or a `when app starts:` block). Mid-block partial states are never shown.

- Example: a function that sets `count`, then `label`, then `total` causes ONE
  screen update after all three assignments — never three flashes.
- AI: one update point per block — easy to reason about ordering and verify.
- Learners: calm, flicker-free, predictable UI.
- Devs: one batched render per action; no micro-stutters in loops.

### 9.5 HTML rules
- Any valid HTML is allowed.
- The UI is defined by HTML/CSS/WebGL and runs wherever the target back-end runs
  it: in a browser (no server required), as a native window, or in a server/edge
  runtime. The browser is a **feature** of OmniScript, not a requirement.

---

## 10. 3D Graphics (Built-in Three.js)

### 10.1 Marker
An optional 3D scene is a `scene:` block (the `scene` keyword, a standalone
`:` token, scene object declarations, then `end`). The scene block MUST appear
after `UI:` (or instead of it, alone). It follows the single block rule
(Section 4) — no special lexing.

### 10.2 Scene objects
Objects are declared with keyword lines inside a `scene:` block:

```
scene:
    box    size="2"    color="#e11d48"
    sphere size="1.5"  color="#ffffff" pos="0,2,0"
    light  type="directional" intensity="2"
end
```

- Built-in shapes: `box`, `sphere`, `cylinder`, `plane`, `light`, `camera`.
- Supported attributes: `size`, `color`, `pos`, `rotation`, `scale`, `type`,
  `intensity`, `texture`, `click`.
- Values may reference logic variables: `color={my_color}` (live link).

### 10.3 Consistency (MUST)
- A 3D scene MUST behave identically on every engine (same rule as 9.4).

---

## 11. Errors

### 11.1 Friendly explanation (MUST)
Every error MUST include a plain-language explanation of what went wrong.

### 11.2 Fix suggestion (MUST)
Every error MUST include at least one suggested fix.

### 11.3 Machine-readable form (MUST)
Every error MUST also be produced in the `omni.diagnostic` JSON schema so the
`omni` API and AI agents can consume them reliably. This is the LOCKED
diagnostic contract — v1.0:

```json
{
  "schema": "omni.diagnostic",
  "version": "1.0",

  "code": "E-EFFECT-003",
  "category": "effect",
  "severity": "error",

  "message": "Network capability used without declaration.",
  "details": "fetch_data calls network I/O but declares no capability for it.",

  "span": {
    "start": 412,
    "end": 438
  },

  "location": {
    "line": 14,
    "column": 3
  },

  "context": {
    "function": "fetch_data",
    "capability": "network",
    "related_symbols": ["http_get"]
  },

  "fixes": [
    {
      "id": "declare-network",
      "kind": "add_declaration",
      "applicability": "automatic",
      "description": "Add the missing capability declaration.",

      "edit": {
        "operation": "insert",
        "span": {
          "start": 318,
          "end": 318
        },
        "text": "    uses network\n"
      }
    },

    {
      "id": "replace-network-call",
      "kind": "replace_span",
      "applicability": "suggested",
      "description": "Replace the network call with a pure alternative, if available.",

      "edit": {
        "operation": "replace",
        "span": {
          "start": 412,
          "end": 438
        },
        "text": "safe_fetch()"
      }
    }
  ]
}
```

Field semantics:
- `code` — stable, versioned error code (e.g. `E-EFFECT-003`). Tests and AI
  agents assert on this, never on message text.
- `span` — absolute character offsets for precise source slicing (start
  inclusive, end exclusive). Preferred by tools over line/column.
- `location` — human-oriented line/column (1-based).
- `context` — the symbols and values involved.
- `fixes` — one or more ranked corrective actions. `applicability` is either
  `automatic` (safe to apply mechanically, machine-checkable) or `suggested`
  (needs judgment). `edit` is a single structured operation —
  `insert` / `replace` / `delete` — with its span and text, so an agent can
  apply it without parsing prose.
- Friendly rules still apply: `message` is plain-language (§11.1), and at
  least one fix is always present (§11.2).

---

## 12. The `omni` Compiler API (MUST)

The compiler MUST expose the following stable commands:

| Command | Meaning |
|---------|---------|
| `omni inspect symbol` | Typed symbol record: name, kind (var/fn/entity), type, declared effects, source span, resolved dependencies |
| `omni explain error` | Plain-language explanation of a failing error |
| `omni find dependency` | What does this depend on; what depends on it |
| `omni generate test` | Draft a test for a function |
| `omni verify contract` | Check that all `require`/`ensure` assertions are syntactically present and well-typed (NOT static proof — SMT is future) |
| `omni trace execution` | Step through what actually runs |
| `omni suggest fix` | Propose a fix for an error |
| `omni summarize module` | What does this file do, in short |

Stability: the output format of these commands MUST be versioned and stable.

### 12.1 `omni inspect symbol` output (LOCKED — v1.0)

`omni inspect symbol` returns a **typed symbol record** — the interrogation
contract the AI-first identity is built on. This is the v1.0 shape:

```json
{
  "schema": "omni.symbol",
  "version": "1.0",
  "name": "fetch_data",
  "kind": "function",
  "type": "fn(Text) -> Text",
  "declared_effects": { "uses": ["network"], "reads": [], "writes": [] },
  "span": { "start": 96, "end": 210 },
  "location": { "line": 7, "column": 1 },
  "dependencies": ["http_get", "parse_body"],
  "exported": true
}
```

Field semantics:
- `kind` — `variable` | `function` | `entity` | `parameter`.
- `type` — the resolved static type (as declared or inferred).
- `declared_effects` — the enforced capability declarations (Section 8).
- `span`/`location` — absolute offsets and human line/column, same convention
  as diagnostics (Section 11.3).
- `dependencies` — the symbols this one references (resolved, not textual).
- `exported` — whether UI slots / click actions may reference it.

Effects:
- **AI**: one predictable schema to plan, verify, and fix against — the core
  interrogation contract.
- **Learners**: "what is this thing" is answered plainly, without reading code.
- **Devs**: IDE-grade data without an IDE.

---

## 13. Architecture (MANDATORY)

OmniScript uses **one front-end, one shared middle representation (OMNI MIR),
and four back-end lanes**. The front-end and the MIR are 100% ours. The
back-ends are borrowed (Clang/LLVM/GCC/MSVC, browsers/Wasmtime, Node/Bun/Deno,
CPython/Pyodide, Flecs ECS). We never write a machine-code generator — and we
never write an ECS either.

```
                        OMNISCRIPT (.omni)
                              │
                              ▼
             ┌─────────────────────────────┐
             │        OUR FRONT-END        │
             │  Tree-sitter parse          │
             │  Name resolution            │
             │  Type checking              │
             │  Effect/capability checking │
             │  Assertion checking         │
             └─────────────┬───────────────┘
                           │
                           ▼
             ┌─────────────────────────────┐
             │         OMNI MIR            │
             │  typed · effect-aware       │
             │  versioned · serializable   │
             │  language-defined           │
             └─────────────┬───────────────┘
                           │
              ┌────────────┼──────────────────┬──────────────┐
              ▼            ▼                  ▼              ▼
         Native/      Web (WASM/JS)      Dynamic       Dynamic
         Systems       back-end          (JS)          (Python)
              │            │                  │              │
              ▼            ▼                  ▼              ▼
        Simulation      C                  JS            Python
        API + model   clang --target         │              │
              │      =wasm32 (browser)       │              │
              │      =wasm32-wasi            │              │
              │      (server/edge)           │              │
              │                             Node/Bun/    CPython/
        ┌─────┴─────┐                       Deno         Pyodide
        ▼           ▼                    (web/server)   (learning)
   Flecs (C)    Bevy (Rust)
   adapter      adapter
   [first]      [future]
        │           │
        └─────┬─────┘
              ▼
           native
```

**The Simulation API and Omni semantic model are a distinct, spec-defined
layer** (Section 13.5). Game code is written in normal OmniScript through the
`sim.*` standard library — NOT new keywords. The model is portable; concrete
ECS runtimes are implementations behind adapters. **Flecs is the FIRST adapter
(its C API binds directly to our C emitter, no extra toolchain). Bevy is the
FUTURE adapter** (needs a Rust lane). Future adapters (Unreal Mass, Unity
DOTS, a custom runtime) must each implement the same model.

### 13.1 Front-End (ours — the only mandatory custom part)

Stages, in order:
1. **Parse** — Tree-sitter grammar turns `.omni` source into a syntax tree.
2. **Name resolution** — every identifier is bound to its definition.
3. **Type checking** — static, per section 7; not deferred to runtime.
4. **Effect/capability checking** — enforcement per section 8.
5. **Assertion checking** — `require`/`ensure` assertions are present and
   well-typed (the runtime tier, Section 8.5). NOT SMT proof — that is future
   (Section 16).

Output: a **checked** OMNI MIR. No untyped, unresolved, effect-violating, or
ill-asserted program may reach MIR.

### 13.2 OMNI MIR (ours — published spec)

- **Typed** — carries the resolved types from step 13.1.3.
- **Effect-aware** — carries the verified capability/effect annotations.
- **Versioned** — a versioned format; changes are backward-compatible or use
  explicit version gates (per section 15).
- **Serializable** — emitted as a stable structured form (e.g. JSON/CBOR) that
  ANY tool in ANY language can read.
- **Language-defined** — the MIR format itself is part of this spec, so third
  parties can build their own back-ends against it.

The MIR is the linchpin: every back-end reads it, and the `omni` API
(section 12) is built on it.

### 13.3 Back-ends

Four lanes. **Native and Web share the SAME C emitter.** The Simulation API +
Omni semantic model (Section 13.5) sits on top of the native lane — it is a
library layer, not a separate emitter.

| Back-end | Emitter | Reaches | Effort |
|----------|---------|---------|--------|
| **Native / Systems** | C (with optional `sim.*` + adapter) | Flecs (first adapter, C API), Bevy (future, Rust lane) → GCC / Clang / MSVC → native binaries. LLVM is INSIDE Clang, not a sibling emitter | one C emitter + thin per-ECS adapters |
| **Web** | C (same) | `clang --target=wasm32` (browser) + `wasm32-wasi` (server/edge) | reuses C |
| **Dynamic (JS)** | JS | Node / Bun / Deno (web + server) | text-to-text |
| **Dynamic (Python)** | Python | CPython / Pyodide (learning mode) | text-to-text |

Capabilities provided per back-end (used by the Section 8.3 check):

| Capability | Native | Portable (WASM/WASI) | JS | Python |
|-----------|:------:|:------:|:--:|:------:|
| `network` | yes | yes (WASI) | yes | yes |
| `filesystem` | yes | WASI yes / browser no | yes (Node) | yes |
| `database` | yes | WASI yes / browser no | yes | yes |
| `camera` | yes | no | no | browser only |
| `microphone` | yes | no | yes (browser) | browser only |
| `GPU` | yes | yes (WebGPU) | yes (WebGPU) | no |
| `process` | yes | no | no | no |
| `secrets` | yes | WASI yes / browser no | yes | yes |

A target back-end is fixed at build time (`omni build --target <name>`), and
capability provision is checked against this matrix at compile time.

Rules:
- The front-end MUST produce the SAME MIR regardless of target back-end.
- The emitted code is ALREADY verified by the front-end. Static typing may
  "evaporate" in the dynamic (JS/Python) back-ends — this is expected and
  correct, because checks happened at MIR time.
- Any difference in observable behavior between back-ends is a bug
  (per section 14).

### 13.4 Execution Model

The browser is one deployment option among several — never a requirement:

- **Native desktop**: compiled binary via C → GCC / Clang / MSVC. (Default for
  high-performance, OS-access, and game targets.)
- **Browser (feature, not requirement)**: WASM or JS output → single
  self-contained HTML page, no server. The zero-install sharing option.
- **Server/edge**: WASI via `clang --target=wasm32-wasi`, or JS via Node/Bun/Deno.
- **Learning**: Python output → Pyodide in-browser, or CPython locally.
- How to run/check: **BOTH** — a friendly app window for humans AND one command
  (`omni run` / `omni check`) for AI agents.

### 13.4a Implementation sequencing (JS first, then C)

Back-end build order is a project decision, not a language decision — but it is
locked: **the JS lane is built first, the C lane second.** Both consume the
SAME MIR.

Why:
- The MIR is the unstable foundation during design. Both emitters read it, so
  MIR changes cost double if both exist during churn. JS-first lets the MIR
  stabilize through real apps; C then costs less because the foundation is
  proven.
- The JS lane delivers live links and the `UI:` block with zero toolchain,
  which proves the signature features earliest.

Sequencing effects:
- **AI**: one debug surface at a time; a fast verify loop on Node/Bun before
  native toolchains are involved.
- **Learners**: see the language working in a browser immediately; live links
  free.
- **Devs**: a clickable demo fast; native binaries arrive with the C lane.

### 13.4b v1.0 feature freeze & v2-v5 roadmap (LOCKED)

- **v1.0 Core MVP Scope**: JS-first core language, `UI:` block, live links (end of block), interpolation (§6.5), runtime assertions (`require`/`ensure`), and the `omni inspect`/`explain` API.
- **v2 Roadmap** (3 sub-phases):
  - **v2.1 — Loops + `join`**: `for x in List:` blocks with `break`/`continue` + `join(list, sep)` string-accumulation builtin. Property-based tests for loops.
  - **v2.2 — 3D Primitives**: `scene:` block with `box`, `sphere`, `cylinder`, `plane`, `light`, `camera`. Attributes: `size`, `color`, `pos`, `rotation`, `scale`, `texture`, `click`. Three.js emitter.
  - **v2.3 — Custom Types**: `type Person = { name: Text, age: Number }`. Struct types with field access, checker validates field access, emitter emits TypeScript-like types for JS.
- **v3 Roadmap** (4 sub-phases):
  - **v3.1** — C emitter + Flecs ECS adapter (C API, components, queries, systems, schedules).
  - **v3.2** — Rust emitter + Bevy ECS adapter (Rust toolchain, Bevy ECS integration).
  - **v3.3** — WASM target (`clang --target=wasm32` browser, `wasm32-wasi` server/edge).
  - **v3.4** — Integration + v3 quality gates (95% coverage, 90% mutation, perf budgets).
- **v4 Roadmap** — SMT Verification + AI Tooling:
  - Static proof that `require`/`ensure` hold before runtime (`omni verify contract`).
  - AI tooling gates: `omni suggest fix` (adversarial tests), `omni generate test`, `omni trace execution` (LSP compliance).
- **v5 Roadmap** — Distributed + Self-hosting + Visual:
  - Self-hosting compiler (OmniScript in OmniScript).
  - Visual editor (blocks → OmniScript) with E2E tests.
  - Distributed systems support (actors, message passing, clustering) with chaos testing.

Delivery is incremental per §13.4a:
1. **v1.0 JS-first MVP ships first** — core + `UI:` + live links + interpolation + `omni inspect`/`explain` + diagnostics.
2. **v2 ships next** — v2.1 loops, v2.2 3D primitives, v2.3 custom types (incremental delivery).
3. **v3 ships next** — v3.1 C+Flecs, v3.2 Rust+Bevy, v3.2 WASM, v3.4 integration.
4. **v4 ships next** — SMT verification + AI tooling.
5. **v5 ships last** — self-hosting, visual editor, distributed systems.

### 13.5 Simulation API + Omni semantic model (MANDATORY)

The simulation feature is TWO spec-defined things, in the **simulation layer**
— never in the core grammar:

1. **The Simulation API** — a standard library (`sim.*`) written in normal
   OmniScript. Game code calls `sim.entity(...)`, `sim.system(...)`, etc.
   There are NO `entity`/`system`/`component` keywords in the language.
   (Effect on learners/devs: nothing new to memorize — it reads like any
   library call. Effect on AI: ONE grammar to learn, higher correctness.)
2. **The Omni semantic model** — the portable, versioned, serializable
   description of entities, components, systems, and queries that the API
   produces. Adapters translate this model onto concrete ECS runtimes.

**Rule: OmniScript defines the model; ECS runtimes implement it.**

- OmniScript is NOT a Flecs frontend nor a Bevy frontend. Flecs is the FIRST
  adapter (its C API binds directly to our C emitter — no extra toolchain),
  and Bevy is the FUTURE adapter (requires a Rust lane).
- The model semantics are written in THIS spec and are runtime-agnostic.
  Unreal Mass, Unity DOTS, or a custom runtime must each implement the SAME
  semantics.
- No concrete ECS's scheduling, query, borrowing, command-buffer, or world
  semantics leak into the spec. If a runtime cannot express the model, the
  runtime is at fault — the model is authoritative.

Model contents (defined by this spec):
- **Entities** — typed, ID-based simulation objects.
- **Components** — typed data attached to entities.
- **Systems** — functions over sets of components, run per schedule step.
- **Queries** — declarative selection of entities by component set.
- **Schedules** — deterministic ordering of systems per frame/tick.
- **Determinism** — fixed, reproducible execution order; no data races; the
  same inputs produce the same state (required for networking/replay).
  Determinism is guaranteed per fixed backend, not bit-identical across
  backends (float rounding may differ).
- **Parallelism** — systems MAY run in parallel when the model proves they
  cannot conflict; ordering is spec-defined, not runtime-defined.
- **Data-oriented layouts** — the model expresses structure-of-arrays /
  cache-friendly storage as the first-class layout; the runtime chooses the
  physical layout, the spec defines the observable semantics.

Example source, expressed through the Simulation API (defined in Section 17):

```
when app starts:
    sim.entity("player", [position(0, 0, 0), velocity(1, 0, 0)])
end

system move:
    every frame
    sim.for_each(position, velocity):    # a query
        position = position + velocity * dt
    end
end
```

The `omni` API (Section 12) reports against the Omni semantic model, so
`omni inspect` and `omni trace` understand entities/systems/queries as
first-class concepts.

---

## 14. Engine Consistency (MANDATORY)

- The behavior of every feature is defined by THIS spec and MUST be identical
  across all engines.
- Any difference between engines is a bug.
- The spec is the authority; engines are implementations of it.
- Engine philosophy: **Frankenstein multi-engine** — borrow the best parts from
  multiple engines, but every engine follows THIS spec.

---

## 15. Versioning

- Spec version: `1.0`
- File may declare a required version:
  `omni version 1.0`
- Engines MUST reject files whose required version they do not support.

---

## 16. Reserved for Future Versions

- Multi-file apps / imports
- Custom types
- **SMT-style verification** — static proof that `require`/`ensure` assertions
  hold before runtime. Distinct from the v1.0 runtime assertion tier (Section
  8.5). This is the research-grade tier.
- **Loops / iteration over Lists** — `for item in <List>:` blocks. When these
  ship, the `join(list: List, sep: Text) -> Text` builtin (Section 6.5) MUST
  be provided for runtime-accumulated strings.
- Concurrency primitives (beyond the Omni semantic model's system parallelism)
- Additional 3D primitives and physics

---

## 17. Simulation API (standard library, not syntax)

The data-oriented simulation model (Section 13.5) is exposed through the
`sim.*` **standard library** — written in normal OmniScript. There are NO
`entity`/`system`/`component` keywords in the language grammar. The core
grammar stays general; simulation lives in the library layer.

### 17.1 Entity creation
```
sim.entity(name, [component_value, ...]) -> Entity
```
- Creates an entity with the given components.
- Components are ordinary typed values (e.g. `position(0,0,0)`).

### 17.2 System registration
```
sim.system(name, fn_body, "every frame")
```
- Registers a function to run every simulation tick (`"every frame"`).
- Schedules may also be `"every <n> ticks"` or `"on <event>"`.
- Systems are ordinary functions passed to the API — no special syntax.

### 17.3 Query
```
sim.for_each(component_a, component_b):
    <statements>
end
```
- Iterates entities having ALL listed components (a query).
- The `end` closes the loop body; the block rule (Section 4) still applies.

### 17.4 Determinism (MUST)
- Within one simulation tick, systems execute in a spec-defined order.
- Two systems that both write the same component MUST NOT run in parallel;
  the compiler MUST reject the schedule otherwise.
- The same inputs and same tick count MUST always produce the same state
  (per fixed backend — see Section 13.5).

### 17.5 Access declarations
- A system function MAY declare `reads <component>` / `writes <component>`
  (Section 8 declarations) to make its access explicit and verifiable.

### 17.6 Example
```
fn move_system:
    writes position
    sim.for_each(position, velocity):
        position = position + velocity * dt
    end
end

when app starts:
    sim.entity("player", [position(0,0,0), velocity(1,0,0)])
    sim.system("move", move_system, "every frame")
end
```

---

## 18. Detailed Step-by-Step Engineering Plan (v1.0 JS-First MVP)

This is the granular, module-by-module engineering blueprint for building the
v1.0 JS-first MVP. Each module is structured to maximize AI correctness,
learner simplicity, and dev ergonomics.

### Module 1: Lexer & Tokenizer
- **Step 1.1**: Define token types (keywords, identifiers, literals, symbols, operators).
- **Step 1.2**: Implement tokenizer enforcing the universal `:` delimiter token (no fused `UI:` or `scene:` literals).
- **Step 1.3**: Handle whitespace collapse, comments (`#`), and line endings (LF/CRLF).
- *Impact*: **AI**: Simple token stream without special-case lexing. **Learners**: Clean syntax rules. **Devs**: Predictable tokenization.

### Module 2: Parser (Front-End AST)
- **Step 2.1**: Implement the universal block parser: `block_header ':' statement* 'end'`.
- **Step 2.2**: Parse logic statements (`when app starts`, `if`/`else`, `fn` with trailing colon, assignment, `show`, `return`, `require`/`ensure`).
- **Step 2.3**: Parse the `UI:` block as a raw HTML block bounded by `end`.
- **Step 2.4**: Parse Text literal interpolation `{expression}`.
- **Step 2.5**: Build the Abstract Syntax Tree (AST).
- *Impact*: **AI**: One parser rule for all blocks makes generation reliable. **Learners**: Consistent `end` delimiters prevent indentation bugs. **Devs**: Zero ambiguous grammar.

### Module 3: Semantic Analysis & Symbol Table
- **Step 3.1**: Name resolution pass (bind every identifier to its definition).
- **Step 3.2**: Scope management (module scope vs function scope).
- **Step 3.3**: Exported symbol table generation for the `omni inspect` API.
- *Impact*: **AI**: Accurate dependency tracking for `omni inspect`. **Learners**: Catches undefined variables instantly. **Devs**: Clear symbol boundaries.

### Module 4: Static Type Checker
- **Step 4.1**: Static type checking for built-in types (`Number`, `Text`, `Boolean`, `List`, `None`).
- **Step 4.2**: Enforce typed function signatures (`fn name(param: Type) -> ReturnType:`).
- **Step 4.3**: Enforce non-overloaded arithmetic (`+` is Number-only).
- **Step 4.4**: Type-check Text interpolation expressions `{...}`.
- *Impact*: **AI**: Types are explicit and checkable without running code. **Learners**: Catches type mismatches at compile time with friendly errors. **Devs**: Predictable type semantics.

### Module 5: Effect & Assertion Checker
- **Step 5.1**: Parse and validate capability declarations (`uses`, `reads`, `writes`, `pure`).
- **Step 5.2**: Transitive capability inference (calls inherit callee effects).
- **Step 5.3**: Check `require`/`ensure` assertion expressions are boolean-typed.
- **Step 5.4**: Produce structured `omni.diagnostic` JSON diagnostics on failure (with spans and structured `edit` fixes).
- *Impact*: **AI**: Machine-actionable JSON diagnostics enable auto-fixing. **Learners**: Clear explanation of side-effect violations. **Devs**: Guaranteed safe-by-default execution.

### Module 6: OMNI MIR Generator
- **Step 6.1**: Lower checked AST into serializable OMNI MIR (JSON/CBOR format matching spec).
- **Step 6.2**: Attach resolved types, declared effects, and symbol metadata.
- *Impact*: **AI**: Clean, stable intermediate representation. **Learners**: Transparent compilation. **Devs**: Decouples front-end from back-ends.

### Module 7: JS Emitter (Back-End)
- **Step 7.1**: Translate OMNI MIR statements into clean ES6 JavaScript.
- **Step 7.2**: Generate runtime boilerplate (reactive data store, live-link batching at block `end`, DOM patcher).
- **Step 7.3**: Wrap emitted JS + HTML into a self-contained single HTML output file.
- *Impact*: **AI**: Instant execution environment in Node/Bun. **Learners**: Zero-install browser experience. **Devs**: Clickable demo with zero setup.

### Module 8: CLI Tool (`omni`)
- **Step 8.1**: Implement `omni check <file.omni>` (syntax, types, effects, diagnostics).
- **Step 8.2**: Implement `omni run <file.omni>` (compile + execute via Node/Bun or browser).
- **Step 8.3**: Implement `omni inspect symbol <file.omni> <symbol>` (returns `omni.symbol` JSON record).
- **Step 8.4**: Implement `omni explain error <file.omni>` (outputs machine-readable `omni.diagnostic`).
- *Impact*: **AI**: Single command toolchain for agents. **Learners**: Friendly terminal tutor. **Devs**: Professional CLI developer workflow.

---

## 18. Bulletproof Engineering Specification & Compiler Manual (v1.0 JS-First MVP)

> **Goal for older models**: This section is written with zero implicit assumptions. Every file structure, grammar rule, data schema, algorithm step, and model warning is explicitly spelled out so that models with limited context (GPT-3, DeepSeek-3, Gemini-2) can execute implementation without guessing.

---

### 18.1 File & Module Directory Structure
Every compiler module MUST be placed in this exact directory tree:
```
omni_compiler/
├── __init__.py
├── lexer.py         # Tokenizer & whitespace collapsing
├── parser.py        # EBNF-compliant recursive descent parser
├── checker.py       # Name resolution, type checking, effect checking
├── mir.py           # OMNI MIR data classes and JSON serialization
├── emitter.py       # ES6 JS + HTML runtime wrapper generator
└── cli.py           # Click/Argparse CLI (`omni check`, `run`, `inspect`)
```

---

### 18.2 Formal EBNF Grammar
Older models MUST use this exact grammar to build the parser (`parser.py`):

```ebnf
program        ::= statement* ui_block?
statement      ::= assignment | app_block | fn_block | if_block | return_stmt | show_stmt
assignment     ::= IDENTIFIER '=' expression
app_block      ::= 'when' 'app' 'starts' ':' NEWLINE statement* 'end'
fn_block       ::= 'fn' IDENTIFIER '(' parameter_list? ')' '->' TYPE ':' NEWLINE effect_clause* statement* 'end'
if_block       ::= 'if' condition ':' NEWLINE statement* ('else' ':' NEWLINE statement*)? 'end'
return_stmt    ::= 'return' expression
show_stmt      ::= 'show' expression
ui_block       ::= 'UI' ':' NEWLINE RAW_HTML 'end'

effect_clause  ::= ('uses' | 'reads' | 'writes') IDENTIFIER+ | 'pure'
parameter_list ::= parameter (',' parameter)*
parameter      ::= IDENTIFIER ':' TYPE
type           ::= 'Number' | 'Text' | 'Boolean' | 'List' | 'None'

expression     ::= comparison
comparison     ::= term (('is' 'not'?) | comparison_op) term
term           ::= factor (('+' | '-') factor)*
factor         ::= primary (('*' | '/') primary)*
primary        ::= NUMBER | TEXT | BOOLEAN | LIST | IDENTIFIER | function_call | interpolated_text
```
*Warning to models*: `:` is ALWAYS a separate token. Never group `UI:` or `scene:` into single lexemes.

---

### 18.3 Exact Data Schemas (JSON / Python Data Classes)

#### A. OMNI MIR Node Schema (`mir.py`)
```json
{
  "schema": "omni.mir",
  "version": "1.0",
  "functions": [
    {
      "name": "add",
      "params": [{"name": "a", "type": "Number"}, {"name": "b", "type": "Number"}],
      "return_type": "Number",
      "effects": {"uses": [], "reads": [], "writes": [], "pure": true},
      "body": [{"op": "return", "expr": {"op": "add", "left": "a", "right": "b"}}]
    }
  ],
  "entry_point": [...],
  "ui_template": "<h1>{greeting}</h1>"
}
```

B. Diagnostic Schema (`omni.diagnostic` — Section 11.3)
C. Symbol Schema (`omni.symbol` — Section 12.1)
*(Both schemas are fully defined in their respective spec sections above and MUST be generated as valid JSON matching those exact keys).*

---

### 18.4 Step-by-Step Implementation Algorithms

#### Algorithm 1: Effect Enforcement (`checker.py`)
```python
def check_effects(func_node, call_graph):
    declared_uses = set(func_node.effects.get("uses", []))
    declared_pure = func_node.effects.get("pure", False)
    
    actual_uses = set()
    for stmt in func_node.body:
        if stmt.is_network_call: actual_uses.add("network")
        if stmt.is_file_call: actual_uses.add("filesystem")
        # Transitive inference:
        if stmt.is_function_call:
            callee = call_graph.get(stmt.callee_name)
            actual_uses.update(callee.inferred_effects)

    if declared_pure and actual_uses:
        raise DiagnosticError("E-EFFECT-001", f"Function declared 'pure' but uses {actual_uses}")
    
    undeclared = actual_uses - declared_uses
    if undeclared and not declared_pure:
        raise DiagnosticError("E-EFFECT-003", f"Capability {undeclared} used without declaration.")
```
*Warning to models*: Do not skip transitive capability inference. If `fn a()` calls `fn b()` which uses `network`, `a()` inherits `network`.

#### Algorithm 2: Live-Link Batching Emitter (`emitter.py`)
```javascript
// Runtime boilerplate generated by emitter.py for JS target:
let state = { greeting: "Hello" };

function batchUpdate(fn) {
    fn(); // Execute user function (mutates state)
    renderUI(); // Re-render ONCE at end of block
}

function renderUI() {
    document.getElementById("app").innerHTML = 
        `<h1>${state.greeting}</h1>`;
}
```
*Warning to models*: Never re-render on every individual variable assignment. Always batch renders at the end of top-level blocks.

---

### 18.5 Strict Warnings & Anti-Patterns (Read Before Coding)
1. **NO string concatenation with `+`**: If a model writes `"Hello, " + name`, **reject it**. Arithmetic `+` is strictly Number-only. Force string building to use Text Interpolation (`"Hello, {name}"`).
2. **NO fused colons**: Do not tokenize `UI:` or `scene:` as single tokens. Tokenize `UI` then `:`, and `scene` then `:`.
3. **NO implicit types**: Every function parameter and return type MUST be explicitly typed (`fn foo(x: Number) -> Number:`). If types are missing, fail at parser/typecheck stage.
4. **NO un-declared side effects**: If a function touches network/filesystem/database without `uses`, fail with `omni.diagnostic` JSON.

---

## 19. The Execution & Agent Guardrail Protocol (The 99% Bulletproof Harness)

> **Mandatory Rule for All Executing Agents**: To prevent context degradation, testing apathy, state blindness, and cascading failure loops, any agent executing this specification MUST adhere to the following three ironclad mechanical rules.

---

### 19.1 Rule 1: The TDD Mandate (Test-Driven Enforcement)
- **Constraint**: The agent is **strictly forbidden** from writing implementation code for any module in `omni_compiler/` until it has first written a failing unit test in `tests/test_<module>.py`.
- **Workflow**:
  1. Write `tests/test_lexer.py` expecting specific token outputs.
  2. Run `pytest` and verify it **fails**.
  3. Write `omni_compiler/lexer.py`.
  4. Run `pytest` and verify it **passes**.
- *Why*: Prevents "testing apathy" and forces the agent to define correctness *before* writing code.

---

### 19.2 Rule 2: The 3-Strike Git Reset Rule
- **Constraint**: If an agent introduces a compilation error or failing test and fails to fix it within **3 consecutive tool attempts**, the agent MUST immediately execute:
  ```powershell
  git checkout .
  git clean -fd
  ```
  (Hard reset to the last known green commit).
- *Why*: Prevents "forward momentum suicide" where an agent piles 20 successive broken patches onto a corrupted file tree. Wiping the slate clean forces root-cause re-evaluation.

---

### 19.3 Rule 3: The Persistent Scratchpad (`TODO.md`)
- **Constraint**: At the root of the workspace, the agent MUST maintain and update a file named `TODO.md` tracking the completion status of every step in Section 18.
- **Format**:
  ```markdown
  # OmniScript v1.0 Execution Ledger
  - [x] Module 1: Lexer & Tokenizer
  - [ ] Module 2: Parser (In progress - working on block rule)
  - [ ] Module 3: Semantic Analysis & Symbol Table
  ...
  ```
- *Why*: Eliminates "state blindness" and attention drift. The agent reads `TODO.md` at the start of every tool call to maintain persistent meta-cognitive memory across long multi-file builds.

---

## 20. Quality Gate Protocol (Mandatory CI Gates)

> **Rule**: Every phase in Section 18 MUST pass ALL automated quality gates below before the phase is marked complete in `TODO.md`. A human or agent may **not** manually check off a phase if any gate fails.

### 20.1 Test Coverage & Quality Gates
| Gate | Tool / Threshold | Enforcement |
|---|---|---|
| **Unit Test Pass Rate** | `pytest` — 100% pass | Required to check off phase |
| **Branch Coverage** | `pytest --cov=omni_compiler --cov-branch --cov-fail-under=90` | ≥ 90% branch coverage on modified modules |
| **Mutation Testing** | `mutmut` — ≥ 80% mutation score | Run after Phase 4 (Checker); optional for earlier phases |
| **Property-Based Tests** | `hypothesis` for parser round-trip & type soundness | Required for Parser (Module 2) & Checker (Module 4) |

### 20.2 Static Analysis & Code Quality Gates
| Gate | Tool / Threshold | Enforcement |
|---|---|---|
| **Type Checking** | `mypy --strict --no-implicit-optional` | Zero errors required before phase check-off |
| **Linting** | `ruff --select=ALL` | Zero warnings; `ruff format` must pass |
| **Cyclomatic Complexity** | `radon cc --min B` | No function > 15 complexity; file avg < 10 |
| **Security Scan** | `bandit -r omni_compiler` | Zero HIGH/MEDIUM findings |

### 20.3 Correctness & Property Gates
| Gate | Requirement |
|---|---|
| **Parser Round-Trip** | Every valid `.omni` file parsed → MIR → emitted JS → re-lexed must preserve semantics (verified by `hypothesis` property tests). |
| **Effect Soundness** | No function with declared `pure` effect may transitively call a function with `uses network/filesystem/...`. |
| **Deterministic Batching** | JS emitter must batch DOM updates exactly once per top-level block (verified by snapshot test). |

### 20.4 Performance Regression Gate (Phase 6+)
| Metric | Threshold |
|---|---|
| `omni check` latency (100-line file) | < 200ms on Apple M1 / Ryzen 5 |
| `omni run` startup (cold) | < 500ms |
| Bundle size (emitted JS) | < 50 KB gzipped |

---

### 20.5 Gate Enforcement Rules
1. **No Manual Override**: No human or agent may tick a phase checkbox in `TODO.md` unless `pytest`, `mypy`, `ruff`, `bandit`, and `mutmut` all pass.
2. **CI Pipeline**: A `.github/workflows/ci.yml` (or local `pre-commit` hook) MUST enforce these gates on every commit.
3. **Nightly Mutation Run**: A scheduled job runs `mutmut` on `main` branch; if mutation score drops below 80%, the build fails.

---

---
## 17. v6 — OMNISYS: The Omni-Native Platform

> OmniScript is the language. **OMNISYS** is the platform — the official application framework and standard ecosystem.
> 
> **Mission**: Consolidate the maturity, capabilities, lessons, and engineering patterns of the best existing software ecosystems into one coherent, Omni-native platform.

---

### 17.1 Architectural Principle

The OmniScript language core remains small. Capabilities belong in OMNISYS modules, not language keywords.

Module tree:
```
OMNISYS.ui          // Cross-platform UI (SwiftUI/WPF/Qt/web principles)
OMNISYS.db          // Data platform (SQL, query builder, migrations, transactions)
OMNISYS.graphics    // Rendering abstraction (Vulkan/Metal/DX/WebGPU)
OMNISYS.gpu         // GPU compute (CUDA/Metal/Vulkan/WebGPU)
OMNISYS.net         // Networking (HTTP/WS/RPC, client/server, middleware)
OMNISYS.http        // High-level HTTP client/server
OMNISYS.audio       // Audio I/O, synthesis, processing
OMNISYS.video       // Video decode/encode, streaming
OMNISYS.fs          // Filesystem (Path, File, Dir, Watch, Atomic write)
OMNISYS.crypto      // Hash, encrypt, sign, KDF, TLS
OMNISYS.auth        // AuthZ/AuthN, OAuth, JWT, sessions
OMNISYS.sim         // ECS, physics, simulation
OMNISYS.ai          // Tensors, autograd, inference, tool use
OMNISYS.test        // Assertions, property testing, mocking, bench
OMNISYS.async       // Task, Future, Stream, Channel, Select, Timeout
OMNISYS.platform    // Native platform APIs
OMNISYS.scene       // 3D scene graph (Vulkan/Metal/DX/WebGPU)
```

The architecture preserves the existing OmniScript compilation pipeline:
```
OmniScript source
      ↓
   Frontend
      ↓
   OMNI MIR
      ↓
backend/runtime
      ↓
native / JS / WASM / future targets
```

---

### 17.2 The OMNISYS Import Model

```omni
import OMNISYS                    // Canonical umbrella import
import OMNISYS.ui                 // Modular sub-imports
import OMNISYS.db
```

The umbrella import must not force compilation of all subsystems. Implementations MUST use dependency analysis, lazy loading, and package boundaries so unused subsystems do not increase binary size, startup time, or build cost.

---

### 17.3 Do Not Wrap — Design Native

Do not create: `OmniScript → wrapper → existing framework → abstraction`

Instead, for each major ecosystem:
1. What problem is it solving?
2. Which concepts survived because they're genuinely useful?
3. Which exist due to historical constraints?
4. Which APIs are awkward due to host language?
5. Which abstractions are hard for AI agents?
6. Which concepts become first-class Omni concepts?
7. Which remain libraries?
8. Which map to the effect/capability system?
9. What belongs in the portable semantic layer?
10. What must remain backend-specific?
11. What is the escape hatch?

**Example**: Not "OmniSwiftUI" — study SwiftUI, extract principles, design `OMNISYS.ui` from first principles for OmniScript.

---

### 17.4 Portable Core + Powerful Escapes

`OMNISYS.gpu` provides portable GPU concepts. But backend-specific capabilities (CUDA, Metal, Vulkan, DirectX, WebGPU) MUST remain accessible. The capability system makes platform differences explicit.

---

### 17.5 Effects and Capabilities Integration

OMNISYS integrates with OmniScript's effect/capability architecture:

| Operation | Capability |
|---|---|
| Database read | `reads database` |
| Database write | `writes database` |
| Network I/O | `uses network` |
| Filesystem read | `reads filesystem` |
| Filesystem write | `writes filesystem` |
| GPU compute | `uses GPU` |
| Camera access | `uses camera` |
| Microphone access | `uses microphone` |
| Process spawn | `uses process` |

One coherent effect model — no independent permission systems per module.

---

### 17.6 Module Architecture Highlights

#### 17.6.1 Database — `OMNISYS.db`
Study: SQL, query builders, ORMs, migrations, transactions, connection pools, prepared statements, relationships, indexes, caching, serialization, validation, schema management, introspection.

Design for both high-level ergonomics AND low-level SQL access. Do not assume ORM is always correct.

#### 17.6.2 UI — `OMNISYS.ui`
Study: SwiftUI, WPF, Qt, modern web UI, retained/immediate mode, accessibility, native controls, layout engines, animation.

Design semantic UI model first, then map to: Windows, Linux, macOS, browser, mobile, future targets.

#### 17.6.3 Graphics/GPU/3D — `OMNISYS.graphics`, `OMNISYS.gpu`, `OMNISYS.scene`, `OMNISYS.sim`
Study: CUDA, Vulkan, DirectX, Metal, WebGPU, modern renderers, ECS, physics.

Separate: semantic rendering model, GPU abstraction, renderer, platform backend, simulation, ECS.

Do not make OMNISYS a frontend for one existing engine.

#### 17.6.4 AI-Native Design (All Modules)
Every OMNISYS API MUST be designed for both humans AND AI coding agents:

- Discoverable, typed, structurally inspectable
- Deterministic where appropriate, machine-readable
- Easy to test, diagnose, with no undocumented conventions
- Required capabilities, I/O types, side effects, dependencies, lifecycle, errors explicit

---

### 17.7 Development Phases

| Phase | Modules | Focus |
|---|---|---|
| **1. Foundations** | `core`, `collections`, `async`, `fs`, `serde`, `error`, `test` | Core utilities, collections, async/concurrency, filesystem, serialization, errors, testing |
| **2. App Foundations** | `ui`, `db`, `net`, `http` | UI, database, networking, HTTP |
| **3. Graphics/GPU/Sim** | `graphics`, `gpu`, `scene`, `sim` | Rendering, GPU compute, 3D scene, ECS/physics |
| **4. Media/Platform** | `audio`, `video`, `camera`, `microphone`, `platform` | Media, device access, native APIs |
| **5. Security/Tooling** | `crypto`, `auth`, `observability`, `tool` | Security, auth, logging/metrics/tracing, dev tools |
| **6. AI/Advanced** | `ai`, `async` (advanced), `pkg` | Tensors, autograd, distributed actors, package manager |

---

### 17.8 Research Requirement

For every module, produce a research document before implementation:

- Capabilities, architectural patterns, strengths, weaknesses
- Performance characteristics, developer ergonomics
- Type-system interaction, portability constraints
- Lifecycle model, error model, concurrency model
- AI usability, interoperability requirements

Then synthesize an Omni-native design.

---

### 17.9 Required Deliverables

Per §14 of the OMNISYS charter, the project MUST produce:

- A. OMNISYS Master Architecture
- B. OMNISYS Module Tree
- C. Capability Matrix
- D. Backend Matrix
- E. API Design Principles
- F. UI Architecture
- G. Database Architecture
- H. Graphics/GPU Architecture
- I. Networking Architecture
- J. Media Architecture
- K. Simulation/ECS Architecture
- L. Security Architecture
- M. AI-Native Tooling Architecture
- N. Package/Module System
- O. `import OMNISYS` Behavior
- P. Performance Model
- Q. Cross-Backend Conformance Model
- R. Escape-Hatch / Native Interop Model
- S. Development Roadmap
- T. Testing/Quality Gates
- U. Example Applications (CRUD SaaS, desktop GUI, web app, 3D app, game, GPU compute, networking server, multimedia, AI)

---

### 17.9 The Golden Rule

> **Do not ask**: "How do we put existing libraries into OmniScript?"
> 
> **Ask**: "If we had all accumulated engineering knowledge today, and were designing a unified platform for OmniScript, AI agents, portability, safety, performance, and ergonomics — what would we build?"

That is OMNISYS.

---

## Appendix A: Minimal Example

```
when app starts:
    name = "World"
    greeting = "Hello, {name}"
end

fn change_greeting:
    writes name
    writes greeting
    name = "OmniScript"
    greeting = "Hello, {name}"
end

UI:
<h1>{greeting}</h1>
<button click="change_greeting">Change it</button>
end
```

## Appendix B: 3D Example

```
when app starts:
    color = "#e11d48"
end

scene:
    sphere size="1.5" color={color} pos="0,0,0"
    light type="directional" intensity="2"
end
```