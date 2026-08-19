# OMNISYS.fs — filesystem access and path helpers (Python lane)

Python reference implementation of the OMNISYS `fs` module, mirroring the JS
lane (`omnisys/fs.js`) semantics locked by the compiler registry
(`OMNISYS_MODULES["fs"]`).

- **Purpose** — read/write/append/delete/inspect files, list/create/remove
  directories, rename/copy files, and three pure path helpers.
- **Dependency** — `omnisys_core` (the implicit root module, per the registry's
  `js_deps`). No runtime import is required; the contract is the registry.
- **Capabilities** — the 11 I/O functions declare `uses filesystem`; the 3 path
  helpers (`join_path`, `basename`, `dirname`) are pure.
- **API** — all functions accept `str` or `pathlib.Path` and return
  Python-native types. Path helpers use `pathlib` internally (ruff `PTH`).
- **Errors** — I/O failures raise Python-native `OSError`/`FileNotFoundError`
  where the JS lane throws, and return `False`/`-1` where the JS lane swallows
  (see `RESEARCH.md`). A non-path argument panics with `TypeError`.
- **Stdlib only** — `shutil`, `pathlib`. No third-party dependencies.

See `RESEARCH.md` for the research gate, design decisions, and deviations.