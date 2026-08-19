# OMNISYS.tool — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/tool.js` and the compiler registry
`OMNISYS_MODULES["tool"]`.

## 1. Ecosystems studied

- **LSP (Language Server Protocol)** — the standard for in-editor language
  services. Kept conceptually: `check`/`explain` return the compiler's own
  structured diagnostics, the LSP's core value.
- **rustc / ruff / flake8 diagnostics** — error-first, machine-readable
  (JSON) output. Mirrored: the compiler CLI prints JSON diagnostics on error.
- **Lexer/tokenizer practice (Python `tokenize`, JS lexers)** — the 
  `tokenize` helper's keyword/identifier/number/text/operator split.

## 2. What was adopted

- The OmniScript keyword set (35 reserved words) verbatim from the JS lane.
- The JS token regex `[A-Za-z_][A-Za-z0-9_]*|"[^"]*"|'[^']*'|\d+(?:\.\d+)?|=>|>=|<=|[<>=:+*/,.\[\]{}()-]|\s+` ported to `re`.
- Token `kind` classification in the JS precedence order: keyword → number →
  text → identifier.
- `check`/`explain` bridging to `python -m omni_compiler.cli` via
  `subprocess.run` with a 15s timeout — the compiler's own diagnostics, not a
  re-implementation.

## 3. Strengths / weaknesses of the studied ecosystems

- LSP: rich, interactive; heavyweight (server protocol, lifecycle).
- Compiler diagnostics (rustc/ruff): precise, structured; tied to a CLI
  boundary.
- stdlib `tokenize`: Python-specific; not the OmniScript grammar.

## 4. Performance

- `tokenize` is a single regex `finditer` pass — O(n). `line_count` is a
  split — O(n). `check`/`explain` spawn a subprocess (~compiler startup
  cost), matching the JS spawnSync model.

## 5. Type-system interaction / portability

- Registry types: `fn(Text) -> List`, `fn(Text) -> Map`, `fn(Text) -> Number`.
  Python uses `Token = dict[str, str]` and a result dict with `path`/`ok`/
  `diagnostic`/`stderr` keys.

## 6. Lifecycle / error / concurrency model

- Pure helpers + subprocess calls. `_run_omni` swallows `OSError` and
  `TimeoutExpired` into `{status: 1, stderr: msg}` so `check`/`explain` never
  raise; non-zero compiler exit codes are encoded in `ok: False`.

## 7. AI usability

- An agent can tokenize any snippet for structural reasoning, count lines and
  identifiers, and ask the real compiler for a diagnostic (`check`) or an
  explanation (`explain`) — all machine-readable JSON.

## 8. Interop requirements

- Future escapes: a full LSP server, richer diagnostics (hints, quick-fixes),
  per-project config — all consume the compiler CLI bridge.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/tool.js`) | Python (this package) | Reason |
|---|------------------------|-----------------------|--------|
| 1 | `process.env.OMNI_PYTHON \|\| "python"` for the interpreter | `sys.executable` | The Python lane's own interpreter is guaranteed valid |
| 2 | `spawnSync` with `encoding: "utf8"` | `subprocess.run(..., text=True)` | Same semantics |
| 3 | no browser-lane panic needed (`core.panic("tool: ...")`) | n/a | Python is always the compiler host; no browser lane |
| 4 | error string when CLI missing is `''` + status | `str(exc)` in `stderr` | More informative; shape preserved |

## 10. Verification

- `python -m pytest packages/omnisys-tool/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-tool/src` **100% branch**.
- `mypy --strict packages/omnisys-tool/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-tool` — clean.