# RESULTS — Phase 5 Project 5.1: Secure File Vault

Run: `RUN_001_DEEPSEEK_V4_FLASH_FREE` (model: deepseek-v4-flash-free via opencode).

## MODEL_RESULT

### Task Completion Status: ✅ COMPLETE

**Summary**: Built a working secure file vault in OmniScript that:
1. Derives a storage key from a passphrase via `omnisys.crypto.kdf` (PBKDF-style
   SHA-256 chain, per-vault random salt, 1000 iterations).
2. Encrypts file contents with `omnisys.crypto.encrypt_aes` before storing and
   decrypts on read with `decrypt_aes`; plaintext is only ever materialized in
   memory after unlock (verified at rest: entry files hold hex `IV/HASH/MAC/CIPHER`
   fields only).
3. Computes and verifies integrity via keyed HMAC-SHA256 signature AND a SHA-256
   content hash; any on-disk modification is detected before decryption
   (`ERROR: TAMPER_DETECTED` proven at runtime by tampering the stored cipher).
4. Implements lock / unlock / store / retrieve / list / delete. Unlock verifies
   the passphrase against a stored `PASS` (HMAC check) — a wrong passphrase keeps
   the vault locked. All read/write operations are gated on the unlocked state.
5. Declares `uses secrets` and `uses filesystem` at every function boundary and
   `pure` on hashing/HMAC/encoding helpers; module-level vault state is read and
   written only through explicit `reads`/`writes` clauses.

**The TASK.md "BLOCKED / OMNISYS.crypto missing" status is stale** — the registry
(`omni_compiler/omnisys_registry.py`) registers and the JS runtime
(`omnisys/crypto.js`) implements the full crypto surface. The task was runnable.

### Execution Efficiency
- `omni check source/file_vault.omni` — exit 0.
- `omni build source/file_vault.omni --output out/file_vault.html` — exit 0 (JS lane).
- `omni verify source/file_vault.omni` — exit 0; all 15 functions `no-contracts`.
- `omni inspect` — capability declarations verified per function.
- `python -m pytest tests/ -q` — 18 passed (~11 s).
- Runtime round-trip `decrypt(encrypt(x)) == x` proven under Node against real
  `fs`/`crypto` backends (fresh vault dir + tamper + wrong-passphrase phases).

### Invalid Assumptions Encountered
1. **`omni run` executes the app**: The emitted app block runs inside
   `batchUpdate(async function(){...})`. When `omnisys.fs` panics (browser lane,
   because `run-omnisys.js` never exposes Node's `require`), the rejection is
   unhandled and `run-omnisys.js` exits 0 after flushing only the synchronous
   logs. Misleading success with truncated output. Workaround: custom DOM-stub
   harness binding `global.require = require` (activates the Node fs/crypto
   backends) plus an `unhandledRejection` trap and a post-flush read.
2. **`require` availability inside the emitted `<script>`**: an earlier
   `node -e` probe showed `typeof require === "function"` inside
   `vm.runInThisContext`, but inside the emitted program it is undefined (the
   OMNISYS runtime IIFEs take the browser lane). Empirically resolved by the
   harness fix above.
3. **A single `writes` declaration covers a module var**: passing a module var
   as an argument counts as a READ (`E-EFFECT-004`). `vault_unlock` needed
   `reads vault_salt` in addition to `writes vault_salt`.
4. **The app block can call capability functions through wrappers, but not
   `omnisys.*` capability functions directly**: direct `omnisys.crypto.*`
   /`omnisys.fs.*` calls in `when app starts` fail `E-EFFECT-003` (the app block
   declares no capabilities); user wrappers are fine (inherit=False at the app
   block).

---

## ECOSYSTEM_RESULT

### API Findings
| Aspect | Finding |
|--------|---------|
| **`OMNISYS.crypto`** | Registered AND implemented (TASK.md status is stale). `kdf(password,salt,iters)->hex`, `encrypt_aes(key,text)->{tag,iv,data}` (data = hex ciphertext), `decrypt_aes(map,key)->Text`, `random_bytes(n)->hex`, `hmac(key,data)->hex`, `sha256`, `constant_time_eq` — all as advertised. |
| **Capability split** | `sha256/sha1/hmac/to_hex/from_hex/constant_time_eq` are PURE; `random_bytes/encrypt_aes/decrypt_aes/kdf` are `uses secrets`. |
| **`OMNISYS.fs`** | Full file surface (`read_file`…`copy_file`) `uses filesystem`; `join_path/basename/dirname` pure. `write_file`/`read_file` return the path / content text. |
| **`OMNISYS.core`** | `split`, `length(any)`, `is_empty(any)` pure; no built-in `split` shortcut — must call `omnisys.core.split` explicitly. |
| **`OMNISYS.collections`** | `list_push`, `list_join` (maps elements to String) useful for vault list building. `list_get` PANICS on out-of-range — raw `parts[1]` index reads are the safe choice for parsing. |

### Language Findings
| Aspect | Finding |
|--------|---------|
| **Effect propagation** | A caller inherits every `uses X` of its callees (`_walk_call` inherit=True): `vault_unlock` must declare `uses secrets` because it calls `derive_storage_key`/`make_salt`. |
| **App-block carve-out** | The app block is enforced with zero declared capabilities and does NOT inherit callee effects (inherit=False) — but direct `omnisys.*` capability calls still fail `E-EFFECT-003`. |
| **Data-access declarations** | Reading OR writing a module-scope variable from a function requires `reads`/`writes` — including passing it as an argument. This is a real, working model of module resource ownership. |
| **Map reads vs writes** | `m["k"]` reads are legal (emit `m["k"]`); `m["k"] = v` writes are a syntax error — use `omnisys.collections.map_set`. |
| **Pure helpers** | Hashing/HMAC/constant-time/encoding helpers are expressible as `pure` and compose freely inside effectful functions. |
| **`result` reserved** | Cannot be a local inside functions (return slot); avoided `counter`/`total` per module-scope collision warning. |

### Compiler Findings
| Aspect | Finding |
|--------|---------|
| **E-EFFECT-004 granularity** | Per-module-var reads/writes, not per-module; message names the exact resource and offers an `add_declaration` auto-fix. |
| **E-EFFECT-003 auto-fix** | Correctly suggests `uses secrets` with an `add_declaration` edit. |
| **E-IMPORT-003** | Every module used must be imported even if its JS is pulled in transitively (fs → collections via js_deps). |
| **`build --output`** | Does NOT create parent directories — `FileNotFoundError` if the out dir is missing. |
| **`verify`** | Emits `omni.verify.batch`; functions without `require`/`ensure` are `no-contracts` (exit 0). |
| **`inspect`** | Returns `omni.symbol` with `declared_effects` — great for testing capability declarations. |

### Diagnostic Findings
| Code | Scenario |
|------|----------|
| `E-EFFECT-003` | Direct `omnisys.crypto.random_bytes` in `when app starts`; also missing `uses secrets` on a kdf caller. |
| `E-EFFECT-004` | `vault_salt` passed as an argument without a `reads` declaration. |
| `E-IMPORT-003` | `omnisys.collections.list_join` used without `import OMNISYS.collections`. |
| `E-BACKEND-001` | `build --target c` on an omnisys-calling program (correct §8.3 per-capability gate). |

### Capability/Effect Findings
- `secrets` and `filesystem` are cleanly enforceable at function boundaries and
  propagate transitively through the call graph to the app block edge.
- `panic`-flagged functions (`json_decode`) would require `uses panic` — avoided
  `json_decode` entirely by using a stable delimited entry format + `core.split`.
- No `borrows` needed; plain `uses`/`pure`/`reads`/`writes` covered all cases.

### Backend Findings
| Backend | Status |
|---------|--------|
| **JS lane (emitted HTML)** | Fully functional for crypto + fs when `require` is exposed. Both Node backends (`crypto`, `fs`) activate; pure-JS crypto fallback also works. |
| **`omni run`** | Silent async-failure bug: app-block rejections are unhandled and the runner exits 0 with only the synchronous log lines. Should await the batchUpdate promise / handle rejections. |

### Documentation Findings
- `docs/architecture/17-escape-hatch.md` and `OMNI_SPEC.md` §17.3/§17.4 are
  consistent with the observed effect model.
- TASK.md §5.1 `STATUS: BLOCKED` is outdated: `OMNISYS.crypto` has shipped.
  `scripts/run-omnisys.js` has no note that fs needs `require` exposed to use
  the Node lane.

### Positive Discoveries
1. `OMNISYS.crypto` + `OMNISYS.fs` compose into a genuinely working encrypted
   vault under the emitted JS lane — real end-to-end crypto/file behavior, not
   just static checks.
2. The reads/writes effect model makes module-state ownership explicit and
   compiler-checked; combined with `uses` it produced a complete policy
   declaration surface for the vault with zero runtime enforcement code.
3. Pure integrity helpers (HMAC + SHA-256 + constant-time compare) let the whole
   tamper-detection path live in `pure` functions that are trivially testable.
4. The two-phase "store then verify" demo pattern (a marker file chosen by a
   `uses filesystem` function) enables deterministic runtime tamper testing of a
   single build artifact.

### Proposed Changes
| Priority | Change | Rationale |
|----------|--------|-----------|
| **HIGH** | `run-omnisys.js`: expose `require` (or bind Node fs/crypto) and await the batchUpdate promise / trap rejections | `omni run` currently exits 0 with truncated output on any runtime failure — silently misleading. |
| **HIGH** | `build --output` should create missing parent directories | Raw `FileNotFoundError` today. |
| **MEDIUM** | Add `list_size` to `OMNISYS.collections` | Only `core.length` covers lists; `list_get` panics on OOB, so parsing code must jump through `core.length` anyway. |
| **MEDIUM** | `omni verify` should include the app entry point in `results` | Contract verification currently covers functions only. |
| **LOW** | Document the browser-lane fs panic + Node `require` requirement | Saves future runs from the same discovery cost. |

---

## Verification Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| `omni check` passes | ✅ | Exit 0 |
| `omni build` succeeds | ✅ | JS target → `out/file_vault.html` |
| `omni verify` passes | ✅ | 15 functions, all `no-contracts` |
| Round-trip `decrypt(encrypt(x)) == x` | ✅ | Runtime-proven under Node |
| Tamper detection | ✅ | Runtime-proven (cipher modified on disk) |
| Wrong passphrase rejected | ✅ | Runtime-proven |
| Policy enforcement (locked → denied) | ✅ | Runtime-proven |
| Plaintext only in memory after unlock | ✅ | At-rest file verified to contain hex fields only |
| `secrets`/`filesystem` declared at boundaries | ✅ | Via `omni inspect` |
| Tests pass | ✅ | 18/18 passing |

---

## Files Produced

```
RUN_001_DEEPSEEK_V4_FLASH_FREE/
├── BENCHMARK_REASONING.md   # Continuous investigation ledger
├── RESULTS.md               # This summary
├── source/
│   └── file_vault.omni      # Vault program (~220 lines)
├── tests/
│   └── test_file_vault.py   # 18 tests (compiler + language-rule + runtime)
├── out/
│   └── file_vault.html      # Built JS artifact
└── probes/                  # Investigation artifacts (probe_*.omni, run_vault.js, ...)
```