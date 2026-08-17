# Self-Hosted Compiler (v5.1)

An OmniScript compiler written in OmniScript.

`compiler.omni` is a structured-AST code generator: it consumes a `List` of
`Stmt`/`Expr` records and emits ES6 JavaScript text (function declarations,
entry statements, `renderUI`/`batchUpdate` scaffolding). Because the OmniScript
core has no string-processing builtins beyond `join`, the structured AST is the
boundary between the front-end of the compiler and this emitter half — which is
written in the language itself.

## Language subset handled

The structured records carry already-rendered JS text for expressions and
conditions, so `compile_program` is a pure text generator. Supported statement
kinds:

| kind       | emitted JS                                      |
|------------|-------------------------------------------------|
| `fn`       | `function name(params) { body }`                |
| `assign`   | `name = value;`                                 |
| `return`   | `return value;`                                 |
| `show`     | `console.log(value);`                           |
| `call`     | `value;`                                        |
| `break`    | `break;`                                        |
| `continue` | `continue;`                                     |
| `if`       | `if (cond) { body } else { other }`             |
| `for`      | `for (const var of iterable) { body }`          |

Struct field shapes are defined by the `Stmt` and `Expr` custom types. All
functions are declared `pure`.

## Brace handling

The JS emitter of the reference compiler treats `{...}` pairs inside text
literals as interpolation slots, so literal braces are emitted through the
`lb()`/`rb()` helpers (which return single-character `{`/`}` strings).

## Bootstrap proof (the compiler compiles itself)

1. `compiler.omni` is valid OmniScript and compiles through the reference
   pipeline (`tokenize -> parse -> analyze -> to_mir -> emit_js`).
2. The emitted JS, run in Node, exposes `compile_program`.
3. The `when app starts:` block embeds a structured description of this file's
   own `emit_expr` function and compiles it at startup into `compiled_self` —
   the compiler compiles (a description of) itself into working JavaScript.

## Layout

- `compiler.omni` — the self-hosted emitter (written in OmniScript).
- `tests/test_self_hosted.py` — source validity, bootstrap, and generated-code
  tests (Node is used when available; tests skip gracefully otherwise).

## Usage

```python
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse
from omni_compiler.checker import analyze
from omni_compiler.mir import to_mir
from omni_compiler.emitter import emit_js

ast = parse(tokenize(open("self_hosted/compiler.omni", encoding="utf-8").read()))
symbols = analyze(ast)
js = emit_js(to_mir(ast, symbols))
```

Run the generated HTML's `<script>` body under Node: it defines
`compile_program(program)` and assigns `compiled_self` at startup.