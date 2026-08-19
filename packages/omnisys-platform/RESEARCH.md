# OMNISYS.platform — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and
`docs/architecture/09-media-platform.md`. Grounded in the JS reference
`omnisys/platform.js` and the compiler registry `OMNISYS_MODULES["platform"]`.

## 1. Ecosystems studied

- **Node `os` module / `process`** — `os.platform()`, `os.arch()`,
  `process.env`, `process.version`, `Date.now()`. The exact vocabulary the
  JS lane mirrors.
- **Python stdlib `platform`/`sys`/`os`/`time`** — `platform.system()`,
  `platform.machine()`, `sys.platform`, `sys.version`, `os.environ`,
  `time.time()`. Always present in CPython 3.11+; the Python lane's native
  source.
- **Windows Win32 APIs** — `GetVersionEx`, `GetEnvironmentVariableW`,
  `QueryPerformanceCounter`, `GetTickCount64`. Host-faithful but C-level and
  Windows-only; a backend escape.
- **POSIX `uname(2)` / `environ(7)`** — `sysname`/`machine` fields and the
  process environment array. Authoritative on Linux/macOS; again an escape.
- **Browser `navigator`** — `navigator.platform`, `navigator.userAgent`,
  `navigator.mediaDevices` (camera/microphone). The JS lane's browser branch
  and the source of the device-capability vocabulary.

## 2. What was adopted

- The Python lane always has a process runtime: `_HAS_PROCESS = True`,
  `_RUNTIME = 'python'`. No import-time detection is needed because
  `os`/`platform`/`time` are stdlib (JS probes `process.versions.node`, then
  `require('os')`).
- `now()` = `time.time() * 1000` — float milliseconds, mirroring
  `Date.now()`.
- `os()` returns `sys.platform` — deliberately OS-faithful to Node's
  `os.platform()` names ('win32', 'linux', 'darwin') rather than
  `platform.system().lower()` ('windows', 'linux', 'darwin').
- `arch()` returns `platform.machine()` — the host-native name ('AMD64',
  'x86_64') instead of Node's normalized 'x64'/'arm64'.
- `env(key)` reads `os.environ.get(key)`; a missing key panics with the
  exact JS message `"platform: env 'KEY' unavailable in this lane"`.
- `sleep_ms(ms)` busy-waits deterministically (`end = now() + max(0,
  int(ms)); while now() < end: pass`) and returns the original `ms` —
  mirroring the JS loop exactly.
- `info()` reports `{'os', 'arch', 'python', 'runtime'}` (JS has `node`
  where Python has `python`, and `runtime` is `'python'` not
  `'node'`/`'browser'`).
- `capabilities()` reports the Python lane set: `['none', 'process',
  'filesystem', 'camera', 'microphone', 'graphics']`.

## 3. Strengths / weaknesses of the studied ecosystems

- Node os: process-native, exact platform names; Node runtime only, no
  browser fallback.
- Python platform/sys/os: stdlib, portable, always present; names differ
  from Node (`platform.system()` vs `sys.platform`), so `sys.platform` is
  chosen for OS-faithfulness.
- Win32/POSIX APIs: authoritative but host-bound and C-level; escapes, not
  the portable core.
- Browser navigator: portable web surface; no process access, and device
  capabilities require user permission.

OMNISYS keeps the portable semantic core only: os/arch/env/now/sleep_ms over
the process lane plus a capability list. Win32/POSIX/browser backends are
escapes that consume the same API.

## 4. Performance

- `now()` is one `time.time()` call. `sleep_ms` is an intentional busy-wait
  — O(ms) wall-clock with no OS sleep, so tiny sleeps are deterministic and
  never interrupted early. A host `time.sleep` is the documented escape for
  large sleeps.

## 5. Type-system interaction / portability

- Registry types: `fn() -> Map`, `fn(Text) -> Text`, `fn() -> Number`,
  `fn(Number) -> Number`, `fn() -> List`. Python typing uses `str`, `float`,
  `list[str]`, `dict[str, str]`.
- `now()` returns a float (JS Number); `sleep_ms(Number) -> Number` returns
  the argument unchanged (int stays int, float stays float).

## 6. Lifecycle / error / concurrency model

- Module state is fixed at import time (`_HAS_PROCESS`, `_RUNTIME`); there
  is no mutable state.
- Errors: `env` on a missing key raises `omnisys_core.PanicError` with the
  exact JS message. No other paths raise.

## 7. AI usability

- Everything is strings, numbers, and lists of strings: an agent can query
  os/arch/env, timestamp with `now()`, and gate on `capabilities()` without
  any runtime; every value is directly inspectable and verifiable.

## 8. Interop requirements

- Future escapes: host `time.sleep` for large sleeps, direct `os.environ`
  access, and browser/device camera/microphone backends consume the same
  API. Camera/microphone *device access* is a **platform escape** (per the
  repo decision): `capabilities()` still reports them as lane capabilities
  while no camera/microphone module exists in the registry.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/platform.js`) | Python (this package) | Reason |
|---|----------------------------|-----------------------|--------|
| 1 | `os.platform()` ('win32', 'linux', 'darwin') | `sys.platform` (same names) | `sys.platform` matches Node's `os.platform()` names OS-faithfully |
| 2 | `os.arch()` ('x64', 'arm64', ...) | `platform.machine()` ('AMD64', 'x86_64', ...) | Python has no `os.arch`; `platform.machine()` is the native name |
| 3 | `info().node` = `process.version` | `info().python` = `sys.version.split()[0]` | Lane-appropriate runtime version key |
| 4 | `info().runtime` = 'node'/'browser' | `info().runtime` = 'python' | Lane name |
| 5 | node/browser capability gating at import | `_HAS_PROCESS` constant `True` | Python stdlib always provides the process lane |
| 6 | browser caps `['none','graphics','camera','microphone']` | `['none','process','filesystem','camera','microphone','graphics']` | Python lane's declared capability set; device access is an escape |
| 7 | `process.env[String(key)]` lookup | `os.environ.get(key)` | Same semantics; `String()` coercion is a no-op for `str` |

## 10. Verification

- `python -m pytest packages/omnisys-platform/tests -q -W error` — all
  tests pass, zero warnings.
- Coverage: `packages/omnisys-platform/src` **100% branch**.
- `mypy --strict packages/omnisys-platform/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-platform` —
  clean.