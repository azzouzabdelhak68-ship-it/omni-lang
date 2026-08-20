# Secure File Vault Tests — Project 5.1
# Compiler-level (check/build/verify/inspect), language-rule, and Node runtime
# tests (round-trip, tamper detection, encrypted-at-rest, policy enforcement).

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
SOURCE_FILE = PROJECT_DIR / "source" / "file_vault.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

PLAINTEXT = "The combination is 4 8 15 16 23 42"
PASSPHRASE = "correct horse battery staple"


def run_omni(command: list[str]) -> subprocess.CompletedProcess:
    """Run an omni CLI command from the run dir and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


def _node_available() -> bool:
    return shutil.which("node") is not None


needs_node = pytest.mark.skipif(not _node_available(), reason="node not installed")


# --- Node DOM-stub harness (mirrors tests/test_emitter.py::_run_emitted) ---
# Adds `global.require = require` so the inlined omnisys/fs.js and crypto.js
# activate their Node backends (the stock run-omnisys.js omits this, so fs
# panics in the browser lane), plus an unhandled-rejection trap and a 500 ms
# flush so the async `batchUpdate` app block always drains before we read logs.

_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];
const logs = [];
global.console = Object.assign({}, console, { log: (...a) => logs.push(a.map(String).join(" ")) });
global.document = {
  getElementById: () => ({ innerHTML: "", addEventListener: () => {} }),
  querySelectorAll: () => [],
};
global.name = "";
global.window = new Proxy({}, { get: () => () => {} });
global.require = require;
try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("SYNC FAIL: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}
process.on("unhandledRejection", (reason, p) => {
  console.error("UNHANDLED REJECTION: " + (reason && reason.stack ? reason.stack : reason));
  process.exit(2);
});
setTimeout(() => {
  process.stdout.write(JSON.stringify(logs) + "\n");
  process.exit(0);
}, 500);
"""


def _build_html(tmpdir: Path) -> Path:
    """Build the vault source to an HTML artifact inside tmpdir."""
    html_path = tmpdir / "file_vault.html"
    result = run_omni(["build", str(SOURCE_FILE), "--output", str(html_path)])
    assert result.returncode == 0, f"build failed: {result.stdout}\n{result.stderr}"
    return html_path


def _run_node(html_path: Path, cwd: Path) -> subprocess.CompletedProcess:
    """Run the emitted program under Node with the DOM-stub harness."""
    runner = cwd / "_runner.js"
    runner.write_text(_HARNESS, encoding="utf-8")
    return subprocess.run(
        ["node", str(runner), str(html_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _logs(proc: subprocess.CompletedProcess) -> list[str]:
    assert proc.returncode == 0, f"node failed rc={proc.returncode}: {proc.stderr}\n{proc.stdout}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _tamper_cipher(entry_file: Path) -> None:
    """Flip the stored ciphertext so the HMAC/SHA-256 integrity check must fail."""
    content = entry_file.read_text(encoding="utf-8")
    assert "CIPHER:" in content, f"entry file has no CIPHER line: {content!r}"
    entry_file.write_text(content.replace("CIPHER:", "CIPHER:aa", 1), encoding="utf-8")


# --- Compiler-level tests ---------------------------------------------------


class TestCompilerChecks:
    """omni check / build / verify acceptance."""

    def test_check_passes(self):
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"check failed: {result.stdout}\n{result.stderr}"

    def test_build_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            html = _build_html(Path(td))
            assert html.exists() and html.stat().st_size > 0
            text = html.read_text(encoding="utf-8")
            assert "<script>" in text
            assert "OMNISYS runtime (inlined" in text

    def test_verify_all_contracts_proven(self):
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"verify failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"
        assert len(data["results"]) >= 15
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )

    def test_native_target_rejected_for_omnisys(self):
        """§8.3 gate: an omnisys-calling program cannot build to a native lane."""
        result = run_omni(["build", str(SOURCE_FILE), "--target", "c"])
        assert result.returncode == 1
        diagnostic = json.loads(result.stdout)
        assert diagnostic["code"] == "E-BACKEND-001"


class TestCapabilityDeclarations:
    """Function-boundary capability declarations required by the brief."""

    def test_source_declares_secrets_and_filesystem(self):
        src = SOURCE_FILE.read_text(encoding="utf-8")
        assert "uses secrets" in src
        assert "uses filesystem" in src
        assert "pure" in src

    def test_vault_store_declares_both_capabilities(self):
        result = run_omni(["inspect", "vault_store", str(SOURCE_FILE)])
        assert result.returncode == 0, result.stderr
        sym = json.loads(result.stdout)
        uses = sym["declared_effects"]["uses"]
        assert "secrets" in uses
        assert "filesystem" in uses

    def test_vault_retrieve_declares_both_capabilities(self):
        result = run_omni(["inspect", "vault_retrieve", str(SOURCE_FILE)])
        assert result.returncode == 0, result.stderr
        sym = json.loads(result.stdout)
        uses = sym["declared_effects"]["uses"]
        assert "secrets" in uses
        assert "filesystem" in uses

    def test_integrity_helpers_are_pure(self):
        for name in ("entry_mac", "mac_is_valid", "entry_hash", "encode_entry", "parse_field"):
            result = run_omni(["inspect", name, str(SOURCE_FILE)])
            assert result.returncode == 0, f"inspect {name} failed: {result.stderr}"
            sym = json.loads(result.stdout)
            assert sym["declared_effects"]["pure"] is True, f"{name} is not pure"

    def test_key_derivation_uses_secrets(self):
        result = run_omni(["inspect", "derive_storage_key", str(SOURCE_FILE)])
        assert result.returncode == 0, result.stderr
        sym = json.loads(result.stdout)
        assert "secrets" in sym["declared_effects"]["uses"]

    def test_vault_list_uses_filesystem(self):
        result = run_omni(["inspect", "vault_list", str(SOURCE_FILE)])
        assert result.returncode == 0, result.stderr
        sym = json.loads(result.stdout)
        assert "filesystem" in sym["declared_effects"]["uses"]
        assert "secrets" not in sym["declared_effects"]["uses"]


class TestLanguageRules:
    """Discovered language rules, verified at compile time."""

    def test_map_index_write_is_syntax_error(self, tmp_path):
        bad = tmp_path / "bad.omni"
        bad.write_text(
            "import OMNISYS.crypto\n"
            "fn f() -> Text:\n"
            "    uses secrets\n"
            "    m = omnisys.crypto.encrypt_aes(\"k\", \"p\")\n"
            '    m["x"] = "y"\n'
            "    return \"z\"\n"
            "end\n"
            "when app starts:\n"
            "    show f()\n"
            "end\n",
            encoding="utf-8",
        )
        result = run_omni(["check", str(bad)])
        assert result.returncode == 1

    def test_missing_capability_is_rejected(self, tmp_path):
        bad = tmp_path / "bad.omni"
        bad.write_text(
            "import OMNISYS.crypto\n"
            "fn f() -> Text:\n"
            "    return omnisys.crypto.kdf(\"a\", \"b\", 10)\n"
            "end\n"
            "when app starts:\n"
            "    show f()\n"
            "end\n",
            encoding="utf-8",
        )
        result = run_omni(["check", str(bad)])
        assert result.returncode == 1
        diagnostic = json.loads(result.stdout)
        assert diagnostic["code"] == "E-EFFECT-003"
        assert diagnostic["context"]["capability"] == "secrets"


# --- Runtime tests (Node, real fs + crypto backends) -----------------------


@needs_node
class TestRuntimeRoundTrip:
    """decrypt(encrypt(x)) == x with integrity intact."""

    def test_store_and_retrieve_round_trip(self, tmp_path):
        html = _build_html(tmp_path)
        proc = _run_node(html, tmp_path)
        logs = _logs(proc)

        assert "OK: VAULT_CREATED_AND_UNLOCKED" in logs
        assert "PHASE: store" in logs
        assert "OK: STORED secrets.txt" in logs
        assert f"RETRIEVE secrets.txt = OK: {PLAINTEXT}" in logs
        assert "RETRIEVE missing.txt = ERROR: NOT_FOUND" in logs
        assert "OK: DELETED notes.txt" in logs
        assert "RETRIEVE secrets.txt = ERROR: VAULT_LOCKED" in logs  # after lock denied

    def test_plaintext_never_at_rest(self, tmp_path):
        html = _build_html(tmp_path)
        _logs(_run_node(html, tmp_path))
        entry = tmp_path / "vault_data" / "secrets.txt"
        assert entry.exists()
        stored = entry.read_text(encoding="utf-8")
        assert PLAINTEXT not in stored
        assert "IV:" in stored and "HASH:" in stored and "MAC:" in stored and "CIPHER:" in stored

    def test_wrong_passphrase_keeps_vault_locked(self, tmp_path):
        # First run creates the vault under the correct passphrase.
        html = _build_html(tmp_path)
        _logs(_run_node(html, tmp_path))
        # Second run uses a different passphrase program; vault must stay locked.
        src = SOURCE_FILE.read_text(encoding="utf-8")
        wrong_src = src.replace(f'vault_unlock("{PASSPHRASE}")', 'vault_unlock("nope nope nope")')
        wrong_omni = tmp_path / "wrong_pass.omni"
        wrong_omni.write_text(wrong_src, encoding="utf-8")
        result = run_omni(["build", str(wrong_omni), "--output", str(tmp_path / "wrong.html")])
        assert result.returncode == 0
        logs = _logs(_run_node(tmp_path / "wrong.html", tmp_path))
        assert any("WRONG_PASSPHRASE" in line for line in logs)


@needs_node
class TestRuntimeTamperDetection:
    """Modifying a stored entry must be detected before decryption."""

    def test_tampered_entry_is_detected(self, tmp_path):
        html = _build_html(tmp_path)
        first = _logs(_run_node(html, tmp_path))
        assert "PHASE: store" in first

        entry = tmp_path / "vault_data" / "secrets.txt"
        _tamper_cipher(entry)

        second = _logs(_run_node(html, tmp_path))
        assert "PHASE: verify" in second
        assert "RETRIEVE secrets.txt = ERROR: TAMPER_DETECTED" in second
        assert PLAINTEXT not in " ".join(second)


# --- Structural tests -------------------------------------------------------


class TestStructure:
    """Deliverable structure and acceptance criteria."""

    def test_deliverable_files_exist(self):
        assert (PROJECT_DIR / "source" / "file_vault.omni").exists()
        assert (PROJECT_DIR / "tests" / "test_file_vault.py").exists()
        assert (PROJECT_DIR / "BENCHMARK_REASONING.md").exists()
        assert (PROJECT_DIR / "RESULTS.md").exists()

    def test_full_check_acceptance(self):
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Full check failed: {result.stderr}"
        assert "omni check: OK" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])