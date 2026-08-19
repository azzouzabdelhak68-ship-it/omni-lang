# OMNISYS.ui

Python reference implementation of the OMNISYS `ui` module: a portable
semantic UI model (SwiftUI/WPF/Qt/web principles synthesized, never wrapped).
Elements are JSON-friendly trees that render to HTML.

- **Registry**: `OMNISYS_MODULES["ui"]` — 13 pure functions. The `screen` /
  `input` capabilities in `docs/omnisys/ui` are future backend escapes; the
  pure value-model surface here needs no capability.
- **Import**: `from omnisys_ui import element, text, button, row, column,
  input, render, bind, state, ...` — add `packages/omnisys-ui/src` to
  `PYTHONPATH`, or rely on the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: Element = `{"tag": "element", "kind": str, "attrs": {},
  "children": []}`; Text = `{"tag": "text", "content": str}`; State =
  `{"tag": "state", "value": any}`. `button` stores its action callback under
  the `action` key (dropped by `bind`'s JSON deep-copy, exactly like
  `JSON.stringify` drops functions).
- **Semantics**: mirrors `omnisys/ui.js` exactly — `render`/`to_html` escape
  `& < > "` in text and in the whitelisted attributes (`value`, `placeholder`,
  `class`, `id`); `row`/`column` render as flex divs; unknown kinds default to
  a `div`; `bind` deep-copies and sets one attribute; `state*` mutate one
  cell.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.