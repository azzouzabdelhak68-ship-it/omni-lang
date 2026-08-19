# OMNISYS.pkg

Python reference implementation of the OMNISYS `pkg` module: package
manifests, version resolution, and install — a portable in-process package
manager over a registry map.

- **Registry**: `OMNISYS_MODULES["pkg"]` — 7 functions. `manifest` and
  `install` declare the `filesystem` capability; the rest are pure.
  `js_deps` = `("core", "serde", "fs")`.
- **Import**: `from omnisys_pkg import manifest, create, resolve, install,
  registry_add, registry_get, list_dependencies` — add
  `packages/omnisys-pkg/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: Spec = `{"tag": "package", "name", "version",
  "dependencies"}`; Registry = `{name: {version: spec}}`; `resolve` returns a
  list of specs; `install` returns `{"tag": "install", "dir", "count"}`.
- **Semantics**: mirrors `omnisys/pkg.js` — `registry_add` writes a versioned
  spec and optionally aliases the whole version map; `registry_get` falls back
  to the first registered version when `version` is falsy; `resolve` is a BFS
  with a `name@version` visited set (diamonds dedupe, unknown deps skipped,
  default version `"latest"`); `manifest` reads a JSON file via OMNISYS.fs and
  decodes it; `install` writes `<name>-<version>.pkg.json` per spec into `dir`.
- **Note**: remote registries and git deps are documented escapes; the
  registry is an in-process map.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every deviation
from the JS reference.