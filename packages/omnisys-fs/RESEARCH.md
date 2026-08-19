# OMNISYS.fs — Research & Design Notes (v6 Phase 1)

Research gate document (spec §17.8, `docs/architecture/19-quality-gates.md` §6)
for the Python reference implementation of the OMNISYS `fs` module. The API is
already locked by the compiler registry (`OMNISYS_MODULES["fs"]`, per
`docs/architecture/04-api-design-principles.md` §1/§7); this document records
the study that produced the Python lane design, the concrete decisions made,
and the deviations from the JS reference (`omnisys/fs.js`).

---

## 1. Scope

The module surface is fixed:

- 11 effectful I/O functions (`uses filesystem`): `read_file`, `write_file`,
  `append_file`, `delete_file`, `file_exists`, `file_size`, `list_dir`,
  `make_dir`, `remove_dir`, `rename_file`, `copy_file`.
- 3 pure path helpers: `join_path`, `basename`, `dirname`.
- Dependency: `omnisys_core` (registry `js_deps`; the Python lane needs no
  runtime import from it — the `panic` concept is mapped to a local helper).

"Filesystem access" here means the traditional synchronous POSIX-style file
operations plus simple path string manipulation. Everything else (watching,
temporary files, atomic writes, permissions, symlinks) is deliberately out of
scope for this phase and is discussed as future scope below.

---

## 2. The eleven questions (§17.3, doc 04 §1)

### 2.1 What problem is it solving?

Persistence and orchestration of local files: reading configs/sources,
writing outputs/logs, staging directories, moving and copying build artifacts,
and assembling paths. For an AI agent these are the highest-frequency "touch
the world" operations after network I/O.

### 2.2 Which concepts survived because they're genuinely useful?

- **Text round-trip** (`read`/`write`/`append`) — irreducible.
- **Existence and size probes** — cheap, decisive for branching.
- **Directory listing** — iteration over a namespace.
- **Create/remove directories** — staging and cleanup.
- **Rename and copy** — the only portable ways to move content and (with
  metadata-preserving copy) to snapshot state.
- **Path components** — join/base/dir are the three primitives every other
  language ships; every alternative (string concatenation) is worse.

### 2.3 Which exist due to historical constraints?

- Return-value error codes (`stat`, most C APIs) — superseded by richer error
  models, but their *shape* (sentinel on failure) is still the cheapest
  contract for scripting.
- `basename`/`dirname`/`join` as *string* operations — they exist because the
  path abstraction is weaker than the OS abstraction; they are kept because
  every host provides them and agents expect them.
- `recursive` flags on mkdir/rm — a reaction to decades of
  "must create parent first" ceremony.

### 2.4 Which APIs are awkward due to host language?

- Node's `readdirSync` returns names in arbitrary order (filesystem order);
  callers must sort to get determinism.
- Node's `rmSync` is a generic "remove anything"; it silently deletes files
  when called with `recursive`, blurring `remove_dir`.
- Rust's `std::fs` is byte-oriented; text I/O requires `read_to_string` plus a
  manual error mapping, and there is no `basename`/`dirname` in the standard
  library (paths live in `std::path` and are platform-typed).
- Go's `os` package mixes file ops and process ops; `os.Rename` has a
  platform quirk (fails on Windows when the target exists, silently overwrites
  on POSIX).
- Python's text-mode file objects apply **newline translation** on Windows by
  default (`\n` ↔ `\r\n`), silently corrupting byte-faithful round-trips.

### 2.5 Which abstractions are hard for AI agents?

- **Ambiguity of errors.** A bare `false` gives no diagnosis; a bare exception
  gives a stack trace the agent must parse. Both are usable, but the contract
  must be *stable* so the agent can branch on it without re-probing.
- **Asymmetric APIs.** Node's `fs` returns errors via exceptions *and*
  callbacks *and* promises (three shapes for one operation).
- **Non-determinism.** Unsorted listings make idempotent scripts fail
  spuriously.
- **Stringly paths.** Hosts that return joined strings force agents to guess
  separators; typed path objects reduce guessing.

### 2.6 Which concepts become first-class Omni concepts?

- **Capability declaration** — the `filesystem` effect is first-class (registry
  `uses filesystem`); the compiler can reject pure functions that reach a
  filesystem call.
- **Boolean outcomes** — `delete_file`, `rename_file`, `copy_file`, `make_dir`
  return `Boolean` *and* the registry types them that way; success/failure is
  part of the signature, not an afterthought.
- **Determinism** — a *sorted* `list_dir` is a semantic guarantee, not an
  implementation detail.

### 2.7 Which remain libraries?

- `tempfile` (mkstemp/mkdtemp/TemporaryDirectory) — naming policy, not I/O.
- Watch APIs (`fs.watch`, inotify, kqueue) — event-driven, concurrency-bound,
  belongs to the future `async`/event lane.
- Glob patterns — a separate search surface (`fnmatch`/`glob`).

### 2.8 Which map to the effect/capability system?

All 11 I/O functions map to `uses filesystem`. The 3 path helpers are `pure`
and therefore compiler-checked side-effect-free — the registry enforces this
(`04-api-design-principles.md` §4, "Capability Honesty"). This is the module's
cleanest effect mapping: no function reaches the disk without declaring it.

### 2.9 What belongs in the portable semantic layer?

The 14 functions above, with **documented cross-backend behavior**: same
semantics on Node and Python lanes. Concretely: byte-faithful UTF-8 text,
bool outcomes mirroring JS try/catch, deterministic listings, Python-native
exceptions where JS throws.

### 2.10 What must remain backend-specific?

- Error *mechanics* (JS throws `Error`; Python raises `OSError` subclasses).
- Path *separator* and absolute-path conventions (`/` vs `\`, drives/roots).
- Metadata fidelity of `copy2` (timestamps preserved where the OS allows).
- The exact exception *type* for a given failure (e.g. `FileNotFoundError` vs
  `PermissionError`) — the contract only guarantees `OSError` (or a subclass).

### 2.11 What is the escape hatch?

Raw `os`/`shutil`/`pathlib` from the host is always available to a Python
embedding; the module itself stays stdlib-only. In OmniScript terms, a script
that needs escapes uses the host lane directly rather than extending the
portable surface.

---

## 3. Ecosystem study

### 3.1 Node.js `fs` (sync + async)

- **Sync**: `readFileSync`, `writeFileSync`, `appendFileSync`, `unlinkSync`,
  `existsSync`, `statSync`, `readdirSync`, `mkdirSync({recursive})`,
  `rmSync({recursive, force})`, `renameSync`, `copyFileSync`. This is exactly
  the surface the JS lane (`omnisys/fs.js`) wraps.
- **Async**: callback and promise variants (`fs/promises`). Better for
  servers; strictly worse for a single-threaded script model where the 
  operation must complete before the next line.
- **Strengths**: one stdlib, exhaustive coverage, `String()` coercion makes it
  forgiving. `existsSync` follows symlinks; `statSync().size` is byte count.
- **Weaknesses**: `readdirSync` order is unspecified; error handling is
  exception-only (no boolean contract); newline translation is absent (good);
  `copyFileSync` does not preserve metadata unless `COPYFILE_FICLONE`/mode
  flags are passed.
- **Relevance**: the Python lane mirrors the *semantics* (bool on swallow,
  raise on propagate) while fixing determinism (sorted listing).

### 3.2 Rust `std::fs`

- `fs::read_to_string`, `fs::write`, `OpenOptions` (append), `remove_file`,
  `metadata()`, `read_dir`, `create_dir_all`, `remove_dir_all`, `rename`,
  `copy`.
- **Strengths**: explicit `Result<T, io::Error>` everywhere; `create_dir_all`
  and `remove_dir_all` are the sane recursive primitives; `ReadDir` is an
  iterator.
- **Weaknesses**: no `basename`/`dirname` in std (lives in `std::path`);
  `remove_dir_all` can fail midway; byte vs text distinction is explicit and
  verbose; `copy` preserves only permissions, not timestamps.
- **Relevance**: confirms that *return-bool on destructive ops* is a
  reasonable contract (Rust callers pattern-match on `Result`); supports the
  decision to make `remove_dir` tolerate missing trees.

### 3.3 Python `pathlib` / `os` / `shutil`

- **`pathlib.Path`**: object-oriented paths, `read_text`/`write_text`/
  `read_bytes`/`write_bytes`, `.unlink()`, `.exists()`, `.stat().st_size`,
  `.iterdir()`, `.mkdir(parents=True, exist_ok=True)`, `.rename()`, `.name`,
  `.parent`, `/` operator, `joinpath`.
- **`os`**: `rename`, `replace`, `unlink`, `stat`, `listdir`, `scandir`.
- **`shutil`**: `rmtree(ignore_errors=True)`, `copy2` (metadata-preserving),
  `move`.
- **Strengths**: `pathlib` is the modern idiomatic surface (ruff `PTH`);
  `mkdir(parents=True, exist_ok=True)` is exactly the recursive contract;
  `rmtree(ignore_errors=True)` is idempotent; `copy2` preserves metadata.
- **Weaknesses**: text-mode **newline translation** on Windows breaks
  byte-faithful round-trips (`Path.read_text`/`write_text` with default
  `newline=None`); `.exists()` is `False` for broken symlinks; on Windows
  `Path.rename`/`os.rename` refuse to overwrite an existing target (raises
  `FileExistsError`) unlike POSIX.
- **Relevance**: `pathlib` is mandated by the repo's ruff `PTH` rules; the
  newline-translation pitfall required an explicit `newline=''` decision
  (§7 below).

### 3.4 Go `os` package

- `os.ReadFile`, `os.WriteFile`, `os.OpenFile(APPEND)`, `os.Remove`,
  `os.Stat`, `os.ReadDir`, `os.MkdirAll`, `os.RemoveAll`, `os.Rename`,
  `io.Copy` (copying has no std helper until `os.CopyFS` in newer versions).
- **Strengths**: two-value returns (`value, err`), `MkdirAll`/`RemoveAll` are
  the recursive primitives, `os.ReadDir` sorts by filename since Go 1.16
  (validating the sorted-listing decision).
- **Weaknesses**: `os.Rename` silently overwrites on POSIX but fails on
  Windows (platform divergence); no metadata-preserving copy helper; file
  locking is famously absent from std.
- **Relevance**: Go's sorted `ReadDir` is independent evidence that
  deterministic listings are the right portable contract; its rename
  divergence is a documented platform trap.

### 3.5 POSIX semantics

- `open(2)`/`read(2)`/`write(2)`, `unlink(2)`, `stat(2)`, `readdir(3)`,
  `mkdir(2)`, `rmdir(2)`, `rename(2)`, `link(2)`/`copy` via userspace.
- **Key facts**: `unlink` returns `ENOENT` on missing files; `stat` returns
  `ENOENT` on missing paths; `rename` is atomic and *overwrites* the target on
  POSIX (no `EEXIST`); `rmdir` only removes empty directories (recursive
  removal is a library construction); `readdir` order is undefined.
- **Relevance**: the Python lane inherits POSIX semantics where the OS
  provides them (metadata via `stat`, rename overwrite on POSIX), while the
  return-bool/exception contract is ours.

---

## 4. Strengths / weaknesses summary

| Ecosystem | Strength | Weakness relevant here |
|---|---|---|
| Node `fs` | Complete, forgiving (`String()`), the JS lane is its mirror | Nondeterministic listings; exception-only errors |
| Rust `std::fs` | `Result`-typed errors, sane recursive ops | Verbose text I/O; no basename/dirname |
| Python `pathlib` | Idiomatic, `PTH`-friendly, `mkdir(exist_ok)` | Newline translation on Windows |
| Go `os` | Sorted `ReadDir`, two-value errors | Rename divergence; no copy helper |
| POSIX | `stat`, atomic rename, defined `ENOENT` | `readdir` order; `rmdir` non-recursive |

---

## 5. Performance

- All operations are single syscall-bound calls (`read`/`write`/`stat`/
  `unlink`/`mkdir`/`rename`); Python-level overhead is a fixed small constant.
  No buffering strategy is exposed or needed at this surface.
- `Path` object construction is cheap (a `PurePath` slice); calling `_as_path`
  per call adds a single `isinstance` pair.
- `list_dir` materializes the whole directory once and sorts — `O(n log n)`,
  matching every alternative (all hosts materialize listings anyway).
- No attempt is made to mirror Node's async or thread-pool paths: the Omni
  script model is synchronous, so the sync syscalls are the correct cost model.
- Reads/writes go through text mode with `newline=''`, so the only
  transformation is the UTF-8 codec itself (identical cost to JS `utf8`).

---

## 6. Ergonomics

- **One calling convention**: positional args, Python-native types, `str` or
  `Path` accepted interchangeably — no overloading, no kwargs.
- **Return values double as diagnostics**: `delete_file`/`rename_file`/
  `copy_file`/`make_dir` → `bool` (true = done); `file_size` → `int` (with
  `-1` sentinel); `file_exists` → `bool`; the rest → values or raise.
- **Deterministic listing** removes a whole class of "why did my script fail
  only sometimes" bugs for agents and humans alike.
- Path helpers are pure and total: no input (any string or Path) can raise;
  only non-path-like *types* panic.

---

## 7. Type-system interaction

- Full type hints, `mypy --strict` clean. `_PathLike = str | Path` is the
  shared path type; `Text` maps to `str`, `Number` maps to `int` (file sizes
  are non-negative or `-1`), `Boolean` to `bool`, `List` to `list[str]`.
- **Key typing trap found during implementation**: `Path.read_text(...)` on
  Windows translates `\r`/`\n`/`\r\n` in both directions unless `newline=''`
  is passed (`Path.write_text` accepts `newline` in 3.11, but
  `Path.read_text` does **not** — reads must open the handle manually).
  Without this, the property test `write/read` round-trip fails for texts
  containing `\r` or `\n`. The implementation therefore:
  - `read_file`: `with p.open('r', encoding='utf-8', newline='') as handle`.
  - `write_file`: `p.write_text(text, encoding='utf-8', newline='')`.
  - `append_file`: `with p.open('a', encoding='utf-8', newline='') as handle`.
  This makes the lane byte-faithful exactly like JS's `utf8` reads/writes.
- `mypy --strict` additionally forced a `NoReturn` annotation on `_panic` and
  a fully-typed `_as_path` coercion helper.

---

## 8. Portability

- **Separators**: `Path` resolves `/` and `\` on every host; all tests are
  written against `Path` semantics (e.g. `dirname('a/b/') == 'a'`,
  `dirname('single') == '.'`), so they run identically on POSIX and Windows.
- **Symlink policy**: the portable API does not special-case symlinks.
  `file_exists` follows links (false for broken links, matching JS
  `existsSync`); `file_size` stats the target (`Path.stat()` follows);
  `delete_file` uses `unlink` (removes the link itself, matching JS
  `unlinkSync`); `remove_dir` uses `shutil.rmtree`, which removes symlinks
  without recursing through them. Policy is "follow on probe, unlink on
  delete" — documented, deliberate, and identical to the JS lane.
- **Atomic writes**: NOT in scope. `write_file` truncates then writes
  (non-atomic, mirrors `writeFileSync`). An atomic-write helper
  (temp file + rename) is listed as future scope.
- **Watch / temp files**: watch APIs (event-driven) and `tempfile` (naming
  policy) are future scope; the registry has no `fs.watch`/`temp` functions.
- **Rename divergence**: `os.rename`/`Path.rename` overwrites on POSIX but
  raises `FileExistsError` on Windows (as does Node's `renameSync`). The
  contract is "returns `True` on success, `False` on error" — the
  cross-platform *shape* is portable even though the underlying behavior
  differs. Documented, not papered over.
- **`remove_dir` on a file**: on Windows `shutil.rmtree(file,
  ignore_errors=True)` returns without deleting; on POSIX it raises
  `NotADirectoryError`. The Python lane returns `False` (via the try/except)
  in the POSIX case and `True` (file untouched) on Windows — a platform
  divergence inherited from `shutil`, documented in §11.

---

## 9. Lifecycle / error model

The module uses a **dual error model**, mirroring the JS lane exactly:

- **Propagate (raise)**: operations whose failure the *caller* must handle to
  keep going — `read_file`, `write_file`, `append_file`, `list_dir`. These
  raise Python-native `OSError`/`FileNotFoundError` (the JS lane throws the
  corresponding `Error`). This keeps the "read the thing" pattern loud.
- **Swallow (return sentinel)**: destructive or probe-like operations where
  the JS lane wraps the call in `try/catch` — `delete_file` (`False`),
  `file_size` (`-1`), `make_dir` (`False`), `remove_dir` (`False`),
  `rename_file` (`False`), `copy_file` (`False`). The caller asks "did it
  happen?" and gets a `Boolean`; no exception can escape.
- **Panic (type error)**: a path argument that is neither `str` nor `Path` is
  a programming error. JS coerces everything with `String()`; Python cannot
  do that faithfully, so `_panic` raises `TypeError`. Panic is *never*
  swallowed by the try/except functions — type errors always propagate.
- `file_exists` never raises (it answers a question), and `file_size`
  returns `-1` rather than raising — both mirror JS.
- Rationale for return-bool on destructive ops: idempotent scripts
  ("delete if present", "make sure dir exists", "copy if source exists")
  are the dominant AI use case, and forcing exception handling on each would
  triple the verbosity for zero information.

---

## 10. AI usability

- **Discoverable**: `omni inspect` already reports every signature and its
  `uses filesystem` / `pure` effect from the registry (doc 04 §2).
- **Deterministic**: same inputs → same outputs (sorted listings, no
  ordering surprises); property tests lock this in.
- **One way to do each thing**: no sync/async/callback triple — one sync
  function per operation, like the JS lane.
- **Branchable outcomes**: `delete_file` → `Boolean`, `file_size` → `Number`,
  so an agent can pattern-match without try/catch in the common cases, and
  only `read/write/append/list` demand exception awareness.
- **Named errors**: failures are standard `OSError` subclasses with OS
  messages — no bespoke error vocabulary to learn, no undocumented
  conventions.
- **Self-diagnosing tests**: unit + hypothesis + conformance suites make the
  contract checkable by one command.

---

## 11. Concrete design decisions for THIS Python impl

1. `pathlib.Path` internally for every function (ruff `PTH`); `str`/`Path`
   accepted, `str` returned where the JS returns `String(path)`.
2. `newline=''` on all text I/O for byte-faithful UTF-8 round-trips.
3. `list_dir` returns **sorted** entry names (documented improvement over
   JS's arbitrary `readdirSync` order; matches Go's sorted `ReadDir`).
4. `delete_file` → `unlink()` + `try/except OSError: return False`.
5. `file_exists` → `Path.exists()` (follows links, like `existsSync`).
6. `file_size` → `Path.stat().st_size`, `-1` on any `OSError`.
7. `make_dir` → `mkdir(parents=True, exist_ok=True)`, `False` on error.
8. `remove_dir` → `shutil.rmtree(ignore_errors=True)`, `False` on error;
   idempotent for missing trees (matches JS `rmSync(force: true)`).
9. `rename_file` → `Path.rename`, `False` on error.
10. `copy_file` → `shutil.copy2` (metadata-preserving; JS `copyFileSync`
    does not copy metadata by default), `False` on error.
11. `join_path`/`basename`/`dirname` via `Path.joinpath`/`.name`/`.parent`,
    returning `str`.
12. `_panic` raises `TypeError` on non-path-like arguments; never swallowed.
13. `__all__` pins exactly the 14 registry functions (conformance-locked).
14. stdlib only; no runtime dependency on `omnisys_core` (conceptual dep only).

---

## 12. Deviations from JS and why

| # | JS lane | Python lane | Why |
|---|---|---|---|
| 1 | `readdirSync` arbitrary order | `list_dir` sorted | Determinism is a documented portable guarantee (AI/determinism rules); no caller depends on arbitrary order |
| 2 | `String(path)` coercion of any value | `TypeError` panic on non-`str`/`Path` | JS coercion is a loose-typing artifact; a typed lane must not silently coerce `123` into a filename |
| 3 | `core.panic` aborts when fs capability is missing | Python always has fs; panic reserved for type errors | The browser lane cannot exist in Python; panic's remaining job is argument validation |
| 4 | `copyFileSync` (no metadata) | `shutil.copy2` (preserves metadata) | `copy2` is the Python-idiomatic "copy a file"; richer fidelity with the same return shape |
| 5 | `writeFileSync` returns exact `String(path)` | `write_file` returns `str(Path(path))` (canonical form) | Normalized path is more useful and deterministic for chained calls |
| 6 | JS `utf8` decode replaces invalid bytes with U+FFFD | Python UTF-8 decode **raises** `UnicodeDecodeError` | Strict decoding surfaces corrupt data loudly; documented divergence (callers may re-open in binary) |
| 7 | `rmSync(recursive, force)` deletes a plain file too | `remove_dir` on a file returns `True` (Windows, file untouched) / `False` (POSIX, raises → caught) | `shutil.rmtree` is the sanctioned primitive; the file case is an OS divergence documented here |
| 8 | error model: JS throws / swallows | Python raises native `OSError` / returns bool sentinel | Same *shape*, Python-native mechanics (doc 04 §6) |

---

## 13. Open questions

1. **Atomic write**: should a future `write_file` (or a new `write_file_atomic`)
   write temp + rename? The JS lane does not; adding it would change failure
   atomicity and cost. Deferred.
2. **Overwrite policy on rename**: `os.rename` fails on Windows when the
   target exists. Should `rename_file` fall back to `os.replace` (unconditional
   overwrite) for cross-platform overwrite semantics, or stay a faithful
   mirror of `renameSync`? Currently faithful; the fallback is a one-line
   change if the ecosystem prefers overwrite.
3. **`list_dir` filtering**: should it return hidden files (`.env`)? Currently
   everything, matching JS. A filter flag would break the pure `List` shape.
4. **Watch / temp / permissions**: `fs.watch`, `tempfile`, and `chmod`-style
   permission functions are future registry candidates; none are in the v6
   registry contract.
5. **Symlink depth**: `file_size` follows links; an API for
   `lstat`-based sizes (the link itself) is absent. Add only if a consumer
   needs it.
6. **Invalid UTF-8 read policy**: strict-decode (current) vs replace-with-U+FFFD
   (JS). The tradeoff is loudness vs parity; revisit if interop with JS-created
   files becomes a real workload.
7. **Directory `copy`**: `copy_file` is file-only; a recursive
   `copy_dir`/`move_dir` is a natural v6.1 candidate.

---

## 14. Gates satisfied

- `python -m pytest packages/omnisys-fs/tests -q` — 38 tests pass.
- `--cov-branch --cov-fail-under=95` — 100% branch coverage on
  `packages/omnisys-fs/src`.
- `mypy --strict packages/omnisys-fs/src` — clean.
- `ruff check packages/omnisys-fs` / `ruff format --check packages/omnisys-fs`
  — clean (single-quote style via local `ruff.toml`, per sibling packages).