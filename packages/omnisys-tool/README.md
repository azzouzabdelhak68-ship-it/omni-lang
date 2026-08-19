# OMNISYS.tool

Python reference implementation of the OMNISYS `tool` module: language-service
tooling — lightweight lexer helpers plus a bridge to the `omni` compiler CLI
for real diagnostics.

- **Registry**: `OMNISYS_MODULES["tool"]` — 5 functions. `check` and `explain`
  declare the `process` capability (they spawn the compiler CLI); the rest are
  pure. `js_deps` = `("core",)`.
- **Import**: `from omnisys_tool import tokenize, check, explain, line_count,
  identifier_count` — add `packages/omnisys-tool/src` to `PYTHONPATH`, or rely
  on the monorepo `packages/conftest.py` bootstrap.
- **Semantics**: mirrors `omnisys/tool.js` — `tokenize` emits
  `{"value", "kind": keyword|number|text|identifier}` dicts (whitespace
  skipped, keyword set is the OmniScript reserved list); `line_count` = number
  of newline-separated lines; `identifier_count` counts identifier-kind
  tokens. `check`/`explain` run `python -m omni_compiler.cli check|explain
  <path>` (15s timeout) and return
  `{"path", "ok", "diagnostic", "stderr"}` where `diagnostic` is the compiler's
  JSON diagnostic when the command fails, else `None`.
- **Note**: the browser lane of the JS reference cannot run the CLI; the
  Python lane can, because Python is the compiler host. Subprocess failure
  (missing interpreter, timeout) is surfaced as `ok: False` with the error in
  `stderr`.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.