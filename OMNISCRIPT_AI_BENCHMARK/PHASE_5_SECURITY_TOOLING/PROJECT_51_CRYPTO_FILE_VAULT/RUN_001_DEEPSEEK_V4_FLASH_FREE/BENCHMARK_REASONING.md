# BENCHMARK REASONING LEDGER — Phase 5 Project 5.1: Secure File Vault

Model: deepseek-v4-flash-free (opencode). Run dir: `RUN_001_DEEPSEEK_V4_FLASH_FREE`.

## Initial Investigation (2026-08-19)

### Mission contract
Read `PROJECT_51_CRYPTO_FILE_VAULT/TASK.md`. STATUS is `BLOCKED` but the header
of the file says the block is stale: the brief asserts `OMNISYS.crypto` IS
registered and implemented. I verified this claim directly against
`omni_compiler/omnisys_registry.py` (lines 395-409): `crypto` module registered
with `sha256`, `sha1`, `hmac`, `to_hex`, `from_hex` (all pure),
`random_bytes`, `encrypt_aes`, `decrypt_aes`, `kdf` (all `uses secrets`),
`constant_time_eq` (pure). So the TASK.md "BLOCKED/Missing OMNISYS.crypto"
status is indeed outdated — the registry is the single source of truth the
compiler uses (`_check_omnisys_call_site`, `omnisys_effects`).

### Questions being investigated
1. Is `OMNISYS.crypto` fully usable through `omni check`? (arity + capability
   enforcement for `uses secrets`).
2. Can `OMNISYS.fs` file I/O be executed at runtime under the emitted JS lane?
   `run-omnisys.js` executes the inlined runtime via `vm.runInThisContext`,
   where Node's module-scoped `require` is NOT a global. `fs.js` and `crypto.js`
   detect `typeof require !== "undefined"` to enable the Node backend and fall
   back to browser-lane behavior otherwise (fs panics in browser lane). If the
   test harness binds `global.require = require`, the Node fs/crypto backends
   should activate. Needs a probe.
3. How does the effect checker propagate capability requirements through user
   function call sites? (`_walk_call` with `inherit=True` unions the callee's
   declared `uses` into the caller's actual set, so a caller MUST re-declare any
   capability its callees use.)
4. Can a function read fields out of the `encrypt_aes` result map (an OMNISYS
   call, resolved type 'unknown') via `m["key"]` indexing without E-TYPE-002?
   `_resolve_type_of(IndexExpr)` on a non-List/Map base returns 'unknown' (no
   error). IndexExpr WRITE is rejected by the parser (map index assignment is a
   syntax error) but reads should be fine.
5. Module-level vault state: reading/writing module-scope variables from inside
   functions triggers E-EFFECT-004 (`reads`/`writes` declarations required).
   Design the vault state so every function declares exactly the data it
   touches.
6. `result` is a reserved symbol inside functions (return slot) — cannot be a
   local. `counter`/`total` collide with module scope — avoid.

### Hypotheses & assumptions
- `omni check` exit 0 will be achievable with `uses secrets` + `uses filesystem`
  on the vault I/O functions and `pure` on hashing helpers.
- `omni verify` will report every function `no-contracts` (no require/ensure),
  so `verify` exits 0.
- Node CAN execute the emitted program if the harness exposes `require`; the
  emitted HTML inlines `omnisys/core.js`, `omnisys/error.js` (crypto deps),
  `omnisys/crypto.js`, `omnisys/fs.js`, `omnisys/collections.js` (fs dep),
  `omnisys/serde.js` in dependency order.
- `omni run` (stock scripts/run-omnisys.js) will NOT work for fs because
  `require` is absent in the vm context -> fs.panic. I will write my own Node
  harness in the pytest mirroring `tests/test_emitter.py::_run_emitted` but
  binding `global.require = require`.

### Files inspected
- `PROJECT_51_CRYPTO_FILE_VAULT/TASK.md` — mission brief.
- `PROJECT_55_NATIVE_INTEROP_ESCAPE_HATCH/RUN_001_CLAUDE_3_5/{TASK,RESULTS,BENCHMARK_REASONING}.md` — sibling structure to mirror (note: sibling has NO TASK.md, it was copied into the message body).
- `PROJECT_55.../RUN_001_CLAUDE_3_5/source/native_interop_demo.omni` — reference program (imports, fn, uses/pure, app block, show).
- `PROJECT_55.../RUN_001_CLAUDE_3_5/tests/test_native_interop.py` — reference pytest (subprocess `python -m omni_compiler.cli`, cwd=PROJECT_DIR).
- `omni_compiler/omnisys_registry.py` — full OMNISYS registry (crypto, fs, serde, core, collections signatures + effects).
- `omnisys/crypto.js` — runtime: `encrypt_aes(key, text)` -> `{tag:"cipher", iv: hex, data: hex}`; `decrypt_aes(cipher, key)`; `kdf(password, salt, iterations)` -> sha256 chain hex; `hmac(key, data)` -> hex; `constant_time_eq(a,b)`; `random_bytes(n)` -> hex.
- `omnisys/fs.js` — runtime: `write_file/read_file/delete_file/file_exists/join_path/list_dir/make_dir` etc. Node backend when `require` present, else panic.
- `omni_compiler/cli.py` — `check/run/build/verify/inspect` semantics; exit codes; `build --target js` default.
- `omni_compiler/checker.py` — effect enforcement: `_walk_call` propagates callee `uses` to caller (inherit=True); `_enforce` raises E-EFFECT-001 (pure+effect), E-EFFECT-003 (undeclared cap), E-EFFECT-004 (undeclared reads/writes of module data). App block is enforced with NO declared caps -> any direct capability call in `when app starts` fails E-EFFECT-003. BUILTIN_CAPABILITIES maps `read_secret` -> secrets etc.
- `omni_compiler/emitter.py` — `_omnisys_runtime` inlines JS sources dependency-ordered; `show` -> `console.log`; map literal `{k: v}` -> JS object; `index` -> `obj[idx]`; struct construct -> object; `join`/`range` special-cased; division via `OmniFP.divide`; `%` via `OmniFP.modulo`.
- `omni_compiler/parser.py` — map literal `{key: value}`, while/for/if blocks, function defs with effects, `parse_field_access`, IndexExpr, function literals.
- `omnisys/core.js` — `split(s, sep)` = String(s).split(sep); `is_empty`; `length` (string/array/object).
- `omnisys/collections.js` — `list_join(list, sep)` = list.map(String).join(sep); `list_get` PANICS on out-of-range.
- `scripts/run-omnisys.js` — harness for `omni run`; `vm.runInThisContext`; binds document stubs; does NOT expose `require`.
- `tests/test_emitter.py::_run_emitted` — the DOM-stub harness pattern I will mirror, with the addition of `global.require = require` for the Node fs/crypto backends.

### Discovered language rules (so far)
- Capability calls from `when app starts` require declaring the capability in the
  app block -> avoid; wrap all I/O in named functions that declare `uses ...`.
- A function calling another function that declares `uses X` must itself declare
  `uses X` (capability propagation via `_walk_call` inherit=True).
- `pure` functions must not call any effectful OMNISYS function or an effectful
  user function (E-EFFECT-001).
- Map index WRITE is a syntax error; map index READ is fine and emits `m[k]`.
- `encrypt_aes` returns a Map; field extraction via `enc["iv"]`/`enc["data"]`
  should typecheck (resolved type 'unknown').
- `list_get` panics on out-of-range; prefer raw index reads `parts[1]` for safe
  splits.
- `result` reserved inside functions; avoid `counter`/`total` as module names.

## Probe 1 — crypto round-trip (`probes/probe_crypto.omni`)
Verified: `kdf` (64-hex output), `encrypt_aes` -> map with `iv`/`data` hex fields,
`decrypt_aes(map, key)` reproduces plaintext, `hmac`, `constant_time_eq`.

Command + raw output (workdir E:\simualtion):
```
python -m omni_compiler.cli check ...\probes\probe_crypto.omni
-> E-EFFECT-003: "Capability secrets used without declaration. app starts performs
   secrets I/O but declares no capability for it."
```
Interpretation: `when app starts` calls `omnisys.crypto.random_bytes(16)` DIRECTLY.
The app block is effect-enforced with ZERO declared capabilities, and `_walk_call`
adds `omnisys_effects()` for direct omnisys calls regardless of app_scope. FIX:
wrap `random_bytes` in `generate_salt() -> Text: uses secrets`. After fix:
```
python -m omni_compiler.cli check ...\probe_crypto.omni -> omni check: OK (exit 0)
python -m omni_compiler.cli build ... --output probe_crypto.html -> wrote ... (exit 0)
python -m omni_compiler.cli run ...\probe_crypto.omni ->
  KEY_LEN: 64
  BLOB: 3dbbd480dc20a41b6d2c5cfb87917f68|5ee4c17b5761b3853086152fd51317048b
  PLAIN: hello vault world
  MAC: 23e9d7b5e9cb955e95aacd6c91f3a83e4be4a6feae34f5c4f2cb5229bb4f3b92
  TAMPER_CHECK_FALSE: false
  (exit 0)
```
KEY DISCOVERY: app block CAN call user functions that declare `uses X`
(inherit=False at the app block), but CANNOT call an `omnisys.*` capability
function directly. Confirms the mission brief's warning. Map-field read
`enc["iv"]`/`enc["data"]` works (resolved type 'unknown', no E-TYPE-002).

## Probe 2 — filesystem (`probes/probe_fs.omni`)
First `check` failed E-IMPORT-003: `omnisys.collections.list_join` used without
`import OMNISYS.collections` (modules must be imported even when another import
pulls in their JS via js_deps). After adding the import: check+build exit 0.

`python -m omni_compiler.cli run probe_fs.omni` printed ONLY `OK` and exited 0 —
suspicious. Root cause (verified with `probes/debug_fs.js`, an async-aware
harness): the emitted app block runs inside `batchUpdate(async function(){...})`.
Inside the emitted `<script>`, `typeof require` is UNDEFINED (vm.runInThisContext
does not inherit Node's module-scoped `require`; my earlier `node -e` one-liner
misled me — that context does see `require`). So fs.js takes the browser lane and
`write_file` calls `core.panic(...)`, rejecting the async batchUpdate promise.
`run-omnisys.js` flushes `logs` and calls `process.exit(0)` SYNCHRONOUSLY before
the rejection is handled, so `omni run` exits 0 with only the first log line.
ECOSYSTEM FINDING: `omni run` silently swallows async app-block failures
(unhandled rejection + immediate exit 0) — partial output, misleading status.

FIX for runtime testing: bind `global.require = require;` in the harness before
`vm.runInThisContext`. The inlined `fs.js`/`crypto.js` then activate the Node
backends. Verified: dir + files created, all 6 lines logged, exit 0.

## Full vault runtime verification (manual, before pytest)
`build source/file_vault.omni --output out/file_vault.html` first FAILED:
`FileNotFoundError ... \out\file_vault.html` — the CLI does NOT create parent
directories for --output. Created `out/` and rebuilt (exit 0).

Phase 1 (fresh dir `probes/rt1`): harness `probes/run_vault.js`
(global.require + unhandledRejection trap + 500 ms flush, cwd=rt1):
```
["=== Secure File Vault Demo ===","STATUS: OK: LOCKED","OK: VAULT_CREATED_AND_UNLOCKED",
 "STATUS: OK: UNLOCKED","PHASE: store","OK: STORED secrets.txt","OK: STORED notes.txt",
 "RETRIEVE secrets.txt = OK: The combination is 4 8 15 16 23 42",
 "RETRIEVE missing.txt = ERROR: NOT_FOUND","LIST = OK: notes.txt, secrets.txt",
 "OK: DELETED notes.txt","LIST = OK: secrets.txt","OK: VAULT_LOCKED",
 "STATUS: OK: LOCKED","RETRIEVE secrets.txt = ERROR: VAULT_LOCKED","=== Demo Complete ==="]
```
Round-trip decrypt(encrypt(x)) == x PROVEN at runtime. Entry file format on disk
(encrypted at rest): `IV:<hex>\nHASH:<hex>\nMAC:<hex>\nCIPHER:<hex>` — plaintext
never written to disk (verify: Get-Content showed only hex).

Phase 2 (tamper): prepended `aa` to the CIPHER line via PowerShell, re-ran
harness in the SAME dir:
```
["=== Secure File Vault Demo ===","STATUS: OK: LOCKED","OK: VAULT_UNLOCKED",
 "STATUS: OK: UNLOCKED","PHASE: verify","RETRIEVE secrets.txt = ERROR: TAMPER_DETECTED",
 "OK: VAULT_LOCKED","STATUS: OK: LOCKED","RETRIEVE secrets.txt = ERROR: VAULT_LOCKED",
 "=== Demo Complete ==="]
```
Tamper detection PROVEN (HMAC + SHA-256 integrity check fail before decrypt).

Wrong-passphrase probe (`probes/probe_wrong_pass.omni`, reuses rt1/vault_data):
```
["ERROR: WRONG_PASSPHRASE","STATUS: OK: LOCKED"]
```
Passphrase verification on unlock PROVEN; vault stays locked.

`python -m omni_compiler.cli verify source/file_vault.omni` -> exit 0, all 15
functions `no-contracts` (no require/ensure used).

## Compiler friction encountered (source/file_vault.omni)
- `check` failed E-EFFECT-004: "Module data 'vault_salt' accessed via reads
  without declaration." Root cause: `vault_unlock` PASSES `vault_salt` as an
  argument to `derive_storage_key` — argument position counts as a READ even
  when the function also writes the var. FIX: declare `reads vault_salt` in
  addition to `writes vault_salt`. Lesson: every function must declare BOTH
  reads and writes of each module var it touches in any position.

## Final verification (all run in the run dir)
```
python -m pytest tests/ -q
-> 18 passed in 7.71s        (exit 0)

python -m omni_compiler.cli check source\file_vault.omni
-> omni check: OK — file_vault.omni        (exit 0)

python -m omni_compiler.cli build source\file_vault.omni --output out\file_vault.html
-> omni build: wrote out\file_vault.html (target=js)        (exit 0)

python -m omni_compiler.cli verify source\file_vault.omni
-> omni.verify.batch, 15 functions, every status "no-contracts"        (exit 0)
```

Runtime test coverage (all under Node, real fs+crypto backends via the custom
harness): decrypt(encrypt(x))==x round-trip; plaintext never present in the
at-rest entry file; tampered CIPHER line -> TAMPER_DETECTED on a second run;
wrong passphrase -> WRONG_PASSPHRASE and vault stays locked; retrieve after
lock -> VAULT_LOCKED.

## Unresolved questions / follow-ups
- `omni verify` covers functions only; the app entry point is not in `results`.
- `run-omnisys.js` silently exits 0 on unhandled async app-block failures
  (proposed HIGH fix in RESULTS.md).
- A `borrows`-based design was considered and rejected as unnecessary — plain
  `uses`/`reads`/`writes` covered every boundary.