# OMNISYS.platform

Python reference implementation of the OMNISYS `platform` module: native
platform abstractions — OS, architecture, environment, monotonic time, and
the current lane's capability list. Python always provides the stdlib
`os`/`platform`/`time` modules, so the process lane is always available.

- **Registry**: `OMNISYS_MODULES["platform"]` — 7 functions, `js_deps =
  ("core",)`. `info`/`os`/`arch`/`env`/`sleep_ms` declare the `process`
  effect; `now` and `capabilities` are pure.
- **Import**: `from omnisys_platform import info, os, arch, env, now,
  sleep_ms, capabilities` — add `packages/omnisys-platform/src` to
  `PYTHONPATH`, or rely on the monorepo `packages/conftest.py` bootstrap.
- **Value shapes**: `info` returns `{"os": str, "arch": str, "python": str,
  "runtime": "python"}`; `env(Text) -> Text`; `now() -> Number` (float
  milliseconds); `sleep_ms(Number) -> Number`; `capabilities() -> List`.
- **Semantics**: mirrors `omnisys/platform.js` — `now()` is
  `time.time() * 1000` (float milliseconds, like `Date.now()`); `os()`
  returns `sys.platform` ('win32', 'linux', 'darwin' — the same names Node's
  `os.platform()` returns); `arch()` returns `platform.machine()` ('AMD64',
  'x86_64'); `env(key)` returns `os.environ[key]` or panics with the exact
  JS message; `sleep_ms(ms)` busy-waits deterministically and returns `ms`;
  `info()` reports `os`/`arch`/`python`/`runtime` (JS reports
  `os`/`arch`/`node`/`runtime`).
- **Python lane capability set**: `['none', 'process', 'filesystem',
  'camera', 'microphone', 'graphics']`. `filesystem`/`camera`/`microphone`/
  `graphics` are *reported* as lane capabilities (the JS browser lane does
  the same for `graphics`/`camera`/`microphone`), but their device access is
  a **platform escape** and is not ported: no camera/microphone module
  exists in the registry, and device I/O stays host-side.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.