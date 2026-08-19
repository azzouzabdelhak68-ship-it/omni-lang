# OMNISYS.pkg — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6. Grounded in the
JS reference `omnisys/pkg.js` and the compiler registry
`OMNISYS_MODULES["pkg"]`.

## 1. Ecosystems studied

- **npm** — `package.json` manifests, `node_modules` install layout, BFS-ish
  version resolution. Kept: `name@version` requests, dependency maps, a
  `create` spec.
- **crates.io / Cargo** — registry maps of name → versions, semver resolution.
  Kept: the registry map shape `name -> version -> spec`.
- **Go modules** — dependency graphs resolved as a graph with visited-set
  dedupe. Kept: the BFS resolver with a `name@version` visited set.
- **PyPI / pip** — index + resolver; the model `resolve` mirrors at the
  in-process level.

## 2. What was adopted

- Spec `{"tag": "package", "name", "version", "dependencies"}` and a registry
  of `name -> version -> spec` (matching the JS lane).
- `registry_add` with an optional `version` alias onto the whole version map
  (`registry[version] = registry[name]`).
- `registry_get` defaulting to the first registered version when none is
  requested (JS `versions[String(version || keys[0])] || null`).
- `resolve` as BFS with `seen = set("name@version")`, returning the ordered
  install list (parents before children, siblings in discovery order).
- `manifest`/`install` bridging to OMNISYS.fs (`read_file`/`json_decode`,
  `make_dir`/`join_path`/`write_file`/`json_encode`) with the `filesystem`
  capability.

## 3. Strengths / weaknesses of the studied ecosystems

- npm: mature registry + lockfiles; heavyweight, network-bound.
- Cargo/crates.io: strict resolution; Rust-toolchain-bound.
- Go modules: simple graphs; vendoring quirks.
- In-process registry: deterministic, offline, JSON-friendly; no remote
  ecosystem (documented escape).

## 4. Performance

- `resolve` is O(V+E) over the visited graph; `registry_add`/`get` are O(1)
  dict ops; `install` is O(specs) file writes; `list_dependencies` is O(deps).

## 5. Type-system interaction / portability

- Registry types: `fn(Text, Text, Map) -> Map`, `fn(Map, Text, Map) -> Map`,
  `fn(Text, Text, Map) -> List`, `fn(Text, Map) -> Map`, `fn(Map) -> List`.
  Python uses `Spec`/`Registry`/`Request` aliases over `dict[str, Any]`.

## 6. Lifecycle / error / concurrency model

- Pure registry/resolve helpers plus `filesystem`-capability functions that
  delegate to OMNISYS.fs (whose errors propagate). No panics in this module
  itself (unlike the JS browser-lane panics, which don't apply to Python —
  Python is always the native lane).

## 7. AI usability

- A registry and its resolved install list are plain JSON — an agent can
  create specs, register versions, resolve dependency graphs, read manifests,
  and install packages into a directory, all without a network or runtime.

## 8. Interop requirements

- Future escapes: remote registries (npm/PyPI), semver ranges, git deps,
  lockfiles — all consume the same registry/spec/resolve model.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/pkg.js`) | Python (this package) | Reason |
|---|----------------------|-----------------------|--------|
| 1 | `if (version !== undefined)` alias | `if version is not None` | Python has no `undefined`; `None` is the sentinel |
| 2 | `Object.keys(versions)[0]` | `list(versions)[0]` | Same insertion-ordered first key |
| 3 | `versions[String(version \|\| keys[0])] \|\| null` | `versions.get(key) or None` | Same fallback semantics |
| 4 | browser-lane `core.panic("pkg.manifest requires the fs module ...")` | n/a | Python always imports fs/serde; no browser lane |
| 5 | `Object.keys(spec.dependencies \|\| {})` | `(spec.get('dependencies') or {}).keys()` | Same |

## 10. Verification

- `python -m pytest packages/omnisys-pkg/tests -q -W error` — all tests pass,
  zero warnings.
- Coverage: `packages/omnisys-pkg/src` **100% branch**.
- `mypy --strict packages/omnisys-pkg/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-pkg` — clean.