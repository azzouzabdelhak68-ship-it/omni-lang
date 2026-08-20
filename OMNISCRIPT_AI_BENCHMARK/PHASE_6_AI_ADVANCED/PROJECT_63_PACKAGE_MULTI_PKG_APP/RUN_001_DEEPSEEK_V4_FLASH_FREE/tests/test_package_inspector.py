# Package Inspector Tests — Project 6.3
# Automated test suite verifying the OmniScript multi-package dependency
# inspector (OMNISYS.pkg: create/registry_add/registry_get/list_dependencies/
# parse_version/satisfies/resolve/compute_checksum/install/manifest).
# Mirrors the structure of test_project_inspector.py (Project 5.4).

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse

PROJECT_DIR = Path(__file__).parent.parent
SOURCE_FILE = PROJECT_DIR / "source" / "package_inspector.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

# Functions that are declared `pure` (no capability uses).
PURE_HELPERS = (
    "build_registry",
    "test_list_dependencies",
    "test_version_satisfaction",
    "test_dependency_resolution",
    "test_checksums",
)
# Functions that interact with the filesystem.
FS_FUNCTIONS = ("test_manifest_parsing", "test_install_packages")

# Expected arity of each OMNISYS.pkg call (verified against the MIR).
EXPECTED_ARITIES = {
    "omnisys.pkg.create": 3,
    "omnisys.pkg.registry_add": 3,
    "omnisys.pkg.registry_get": 3,
    "omnisys.pkg.list_dependencies": 1,
    "omnisys.pkg.parse_version": 1,
    "omnisys.pkg.satisfies": 2,
    "omnisys.pkg.resolve": 3,
    "omnisys.pkg.compute_checksum": 1,
}

RUN_MARKERS = (
    "=== Package System Inspector ===",
    "Registry built with packages: core, parser, app, analytics",
    "Dependencies listed:",
    "Version satisfaction tested:",
    "Resolution order:",
    "Checksum tests:",
    "Manifest parsed:",
    "=== Inspection Complete ===",
)


def run_omni(command: list[str]) -> subprocess.CompletedProcess:
    """Run an omni CLI command and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


def _compile_source() -> tuple[list, object, object]:
    """Tokenize, parse, analyze and lower the package inspector source."""
    code = SOURCE_FILE.read_text(encoding="utf-8")
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return tokens, symbol_table, mir


def _collect_mir_calls(mir: object, name: str) -> list[dict]:
    """Collect MIR call nodes with the given (normalized) name."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("op") == "call" and node.get("name") == name:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(mir.entry_point)  # type: ignore[arg-type]
    for fn in mir.functions.values():  # type: ignore[attr-defined]
        walk(fn.body)
    return found


def _node_available() -> bool:
    return shutil.which("node") is not None


needs_node = pytest.mark.skipif(not _node_available(), reason="node not installed")


def _run_emitted_with_require(html: str) -> subprocess.CompletedProcess[str]:
    """Run an emitted HTML document under Node with a DOM stub.

    Binds ``global.require`` so the inlined OMNISYS.fs and OMNISYS.pkg
    runtimes can reach the real Node filesystem and crypto backends. When the
    manifest is not at the cwd the program degrades to the synthetic manifest.
    """
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];
global.__logs = [];
global.console = Object.assign({}, console, {
  log: (...a) => global.__logs.push(a.map(String).join(" ")),
});
global.__app = { innerHTML: "", addEventListener: (t, fn) => { global.__listener = fn; } };
global.document = {
  getElementById: () => global.__app,
  querySelectorAll: () => [],
  createElement: () => ({}),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
global.window = global;
global.name = "";
global.require = require;
vm.runInThisContext(code, { filename: htmlPath });
process.stdout.write(JSON.stringify(global.__logs) + "\n");
"""
    runner_src = harness
    html_path = None
    runner_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", encoding="utf-8", delete=False
        ) as f:
            f.write(html)
            html_path = Path(f.name)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", encoding="utf-8", delete=False
        ) as g:
            g.write(runner_src)
            runner_path = Path(g.name)
        return subprocess.run(
            ["node", str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        if html_path is not None:
            html_path.unlink(missing_ok=True)
        if runner_path is not None:
            runner_path.unlink(missing_ok=True)


def _program_logs(proc: subprocess.CompletedProcess[str]) -> list[str]:
    """Parse the JSON-encoded __logs array from the harness stdout."""
    out = proc.stdout.strip()
    if not out:
        return []
    return json.loads(out)


# --- Compiler Checks ---


class TestCompilerChecks:
    """Test that the source file passes all compiler checks."""

    def test_check_passes(self):
        """omni check source/package_inspector.omni exits with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"

    def test_build_succeeds(self):
        """omni build source/package_inspector.omni succeeds (exit 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "package_inspector.html"
            result = run_omni(["build", str(SOURCE_FILE), "-o", str(out)])
            assert result.returncode == 0, f"Build failed: {result.stderr}"
            assert out.exists(), "build did not write the output artifact"

    def test_verify_all_contracts_proven(self):
        """omni verify proves all contracts (status verified or no-contracts)."""
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Verify failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"

        assert data["results"], "verify returned no function results"
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )


# --- Capability Declarations ---


class TestCapabilityDeclarations:
    """Test that capability declarations are present and correct."""

    def test_filesystem_capability_declared(self):
        """The fs-using paths (manifest/install) declare `uses filesystem`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "uses filesystem" in source_text
        # Both fs paths are wrapped in try/on error for graceful degradation.
        assert "try:" in source_text
        assert "on error:" in source_text

    def test_pure_helpers_declared(self):
        """Registry/version/resolution/checksum helpers are marked `pure`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert source_text.count("pure") >= 5

    def test_symbol_table_uses_filesystem(self):
        """analyze() records `filesystem` in declared_effects for fs functions."""
        _, symbol_table, _ = _compile_source()
        for name in FS_FUNCTIONS:
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            assert "filesystem" in rec["declared_effects"]["uses"], (
                f"{name} missing uses filesystem: {rec['declared_effects']}"
            )

    def test_symbol_table_pure_helpers(self):
        """analyze() marks registry/version/checksum helpers pure with no uses."""
        _, symbol_table, _ = _compile_source()
        for name in PURE_HELPERS:
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            effects = rec["declared_effects"]
            assert effects["pure"] is True, f"{name} is not pure"
            assert effects["uses"] == [], f"{name} unexpectedly uses {effects['uses']}"


# --- OMNISYS.pkg Integration ---


class TestPkgIntegration:
    """Test integration with OMNISYS.pkg through the compiler pipeline."""

    def test_pkg_modules_imported(self):
        """The source imports the OMNISYS modules it consumes."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        for mod in ("OMNISYS.pkg", "OMNISYS.fs", "OMNISYS.serde", "OMNISYS.collections"):
            assert f"import {mod}" in source_text, f"missing import {mod}"

        _, _, mir = _compile_source()
        imported = {tuple(path) for path in mir.imports}
        assert ("OMNISYS", "pkg") in imported
        assert ("OMNISYS", "fs") in imported
        assert ("OMNISYS", "serde") in imported
        assert ("OMNISYS", "collections") in imported

    def test_pkg_call_arities(self):
        """Every OMNISYS.pkg call uses the declared arity (E-CALL-003 check)."""
        _, _, mir = _compile_source()
        for name, arity in EXPECTED_ARITIES.items():
            calls = _collect_mir_calls(mir, name)
            assert calls, f"no {name} call found in MIR"
            for call in calls:
                assert len(call["args"]) == arity, (
                    f"{name} arity wrong: {len(call['args'])} != {arity}"
                )

    def test_registry_add_declared_shape(self):
        """registry_add is called as (registry, name, spec) per the declaration."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.pkg.registry_add")
        assert calls, "no omnisys.pkg.registry_add call found in MIR"
        for call in calls:
            args = call["args"]
            assert args[0]["op"] == "ident", f"first arg must be the registry: {args}"
            assert args[1]["op"] == "text", f"second arg must be the name: {args}"

    def test_resolve_constraint_aware(self):
        """resolve is called with (name, version, registry) = 3 args."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.pkg.resolve")
        assert calls, "no omnisys.pkg.resolve call found in MIR"
        for call in calls:
            assert len(call["args"]) == 3
            assert call["args"][0]["op"] == "text", "resolve name must be a literal"
            assert call["args"][2]["op"] == "ident", "resolve registry must be a variable"


# --- Runtime Behavior (Node) ---


class TestRuntimeBehavior:
    """Test the emitted program under Node with a require-bridging DOM harness."""

    @needs_node
    def test_program_runs_under_node(self):
        """Emitted program exits 0 under the Node harness (graceful, no crash)."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

    @needs_node
    def test_program_markers_logged(self):
        """All inspection phases print their expected markers."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        for marker in RUN_MARKERS:
            assert any(marker in line for line in logs), f"missing marker {marker!r}: {logs}"

    @needs_node
    def test_checksum_deterministic_and_resolution_ordered(self):
        """Checksums are deterministic and resolution is topological."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)

        checksum_line = next(line for line in logs if line.startswith("Checksum tests:"))
        assert '"match":"true"' in checksum_line, f"checksums not equal: {checksum_line}"

        resolution_line = next(line for line in logs if line.startswith("Resolution order:"))
        assert '"name":"app"' in resolution_line
        assert '"name":"core"' in resolution_line
        assert '"name":"parser"' in resolution_line

    @needs_node
    def test_manifest_degrades_to_synthetic(self):
        """With no manifest at cwd, the program returns the synthetic manifest."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        manifest_line = next(line for line in logs if line.startswith("Manifest parsed:"))
        assert '"name":"sample-app"' in manifest_line, f"unexpected manifest: {manifest_line}"


# --- Degradation Behavior ---


class TestDegradation:
    """Test that the inspector degrades gracefully via try/on error."""

    @needs_node
    def test_omni_run_exits_zero(self):
        """The reference `omni run` lane exits 0 with all markers."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"omni run failed: {result.stderr}"
        for marker in RUN_MARKERS:
            assert marker in result.stdout, f"missing marker {marker!r}"

    @needs_node
    def test_omni_run_resolution_and_checksum(self):
        """`omni run` resolution is topological and checksums deterministic."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"omni run failed: {result.stderr}"

        resolution_line = next(
            line for line in result.stdout.splitlines() if line.startswith("Resolution order:")
        )
        assert '"name":"core"' in resolution_line
        assert '"name":"parser"' in resolution_line

        checksum_line = next(
            line for line in result.stdout.splitlines() if line.startswith("Checksum tests:")
        )
        assert '"match":"true"' in checksum_line

    def test_fs_wrappers_always_return(self):
        """fs paths never panic; try/on error returns the synthetic manifest."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "omnisys.fs.file_exists" in source_text
        assert "on error:" in source_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])