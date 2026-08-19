# OMNISYS.graphics

Python reference implementation of the OMNISYS `graphics` module: a portable
2D canvas model that records a deterministic list of draw operations on a
plain dict value, with `render`/`to_json` producing serializable output for
any backend.

- **Registry**: `OMNISYS_MODULES["graphics"]` — all eleven functions
  (`canvas`, `clear`, `line`, `rect`, `circle`, `polygon`, `text`, `fill`,
  `stroke`, `render`, `to_json`) are declared `_pure` (zero effects; registry
  deps `("core",)`). The `_pure` marker is metadata only: every function is a
  plain synchronous Python function.
- **Import**: `from omnisys_graphics import canvas, line, render, ...` — add
  `packages/omnisys-graphics/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Canvas = `{"tag": "canvas", "width": ..., "height": ...,
  "ops": [], "fillColor": None, "strokeColor": None}`; each draw call appends
  exactly one op dict (`{"op": "line", ...}`, `{"op": "rect", ...}`, ...);
  `render`/`to_json` return shallow copies of the op list.
- **Semantics**: mirrors `omnisys/graphics.js` exactly — mutating draw calls
  return the SAME canvas value; `line` falls back to the current stroke color
  and `rect`/`circle`/`polygon`/`text` fall back to the current fill color
  when the passed color is falsy (`None` or `''`), matching JS
  `color || canvas.strokeColor` / `color || canvas.fillColor`; `text`
  stringifies its content with `str`, matching JS `String(x)` for str/int.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.