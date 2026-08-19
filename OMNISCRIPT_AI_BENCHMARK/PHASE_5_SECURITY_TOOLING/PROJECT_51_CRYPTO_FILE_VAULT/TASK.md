# Benchmark Task 5.1: Secure File Vault

## Status Metadata
- **STATUS**: `BLOCKED`
- **Implemented**: Core language, `secrets`/`filesystem` capability vocabulary, effects enforcement.
- **Missing**: `OMNISYS.crypto` — hash, encrypt, decrypt, sign, verify, key derivation, TLS.
- **Benchmark purpose**: Discovery/limitation testing only — runnable once `OMNISYS.crypto` ships in v6.
- **Verified by**: `omni check`, `omni run`.

---

## Investigation Requirement & Reasoning Instructions

Before implementing the project, investigate the OmniScript compiler and establish the language rules necessary for this task.

Do not assume that OmniScript follows conventions from another programming language.

When uncertain, investigate the repository, construct a minimal probe, inspect compiler behavior, or write a focused test.

Create `RUN_xxx_<MODEL_NAME>/BENCHMARK_REASONING.md` inside a dedicated run directory (e.g., `RUN_001_CLAUDE_3_5/BENCHMARK_REASONING.md`) at the beginning of the task.

Continuously record your explicit, observable investigation throughout implementation:
- Questions currently being investigated
- Initial hypotheses and assumptions
- Files, documentation, and compiler source inspected
- Probes and experimental source files created
- Compiler commands executed and raw outputs
- Errors encountered and your interpretation
- Architectural and code decisions made
- Alternative approaches considered and rejected
- Failed approaches and corrections
- Discovered language rules and compiler behaviors
- Unresolved questions and verification results

**Do not retrospectively rewrite or polish the reasoning history after completion.** The purpose of this file is to preserve the actual observable decision trajectory of the implementation process.

---

## Behavioral Mission Brief

Implement a secure file vault utility that encrypts stored files, derives keys from passphrases, verifies integrity, and enforces access policies.

### Functional Requirements
1. **Key Derivation**:
   - Derive a storage key from a user passphrase.
2. **Encryption & Decryption**:
   - Encrypt file contents before storage and decrypt on read.
3. **Integrity & Signing**:
   - Compute and verify content hashes / signatures to detect tampering.
4. **Vault Operations**:
   - Lock, unlock, store, retrieve, list, and delete vault entries.
   - Preserve encrypted form at rest; plaintext only in memory after unlock.
5. **Policy & Effects**:
   - Enforce access rules (unlocked-vault required for read/write).
   - Declare `secrets` and `filesystem` capabilities at function boundaries.

---

## Deliverables & Acceptance Criteria

All outputs must be written inside your dedicated run directory (`RUN_xxx_<MODEL_NAME>/`):

1. **`BENCHMARK_REASONING.md`**: Continuously maintained observable research ledger.
2. **`source/file_vault.omni`**: Primary program implementing the vault.
3. **`tests/test_file_vault.py`**: Automated test suite verifying round-trip encryption, tamper detection, and policy enforcement.
4. **`RESULTS.md`**: Dual-dimension benchmark summary:
   - `## MODEL_RESULT`: Task completion status, execution efficiency, invalid assumptions encountered.
   - `## ECOSYSTEM_RESULT`: Structured telemetry covering API, Language, Compiler, Diagnostic, Documentation, Capability/Effect, and Backend findings, plus Positive Discoveries and Proposed Changes.

### Verification Criteria
- `omni check source/file_vault.omni` exits with code 0.
- Round-trip decrypt(encrypt(x)) reproduces x; tampering is detected.
- All tests in `tests/` pass.