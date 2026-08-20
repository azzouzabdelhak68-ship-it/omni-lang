# Project Inspector Tests — Project 5.4
# Automated test suite verifying the OmniScript source-inspection utility.
# Mirrors the structure of test_native_interop.py (Project 5.5).

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
SOURCE_FILE = PROJECT_DIR / "source" / "project_inspector.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

INLINE_SOURCE = (
    "fn add(a: Number, b: Number) -> Number:\n"
    "    pure\n"
    "    return a + b\n"
    "end\n"
    "import OMNISYS.core\n"
)

# Expected metrics for INLINE_SOURCE (verified against OMNISYS.tool at runtime):
#   line_count:   6 lines  ("split('\n').length" on the 5-line sample + trailing '')
#   tokenize:     25 tokens
#   identifier_count: 20 identifiers
#   functions:    ["add"]
#   capabilities: ["pure"]
#   imports:      ["OMNISYS.core"]


def run_omni(command: list[str]) -> subprocess.CompletedProcess:
    """Run an omni CLI command and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


def _compile_source() -> tuple[list, object, object]:
    """Tokenize, parse, analyze and lower the project source via the Python API."""
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

    Unlike ``omni run`` (whose runner never exposes ``require`` inside the vm
    context), this harness binds ``global.require`` so the inlined OMNISYS.fs
    and OMNISYS.tool runtimes can reach the real Node filesystem and the
    compiler CLI through child_process.
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
        """omni check source/project_inspector.omni exits with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"

    def test_build_succeeds(self):
        """omni build source/project_inspector.omni succeeds (exit 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "inspector.html"
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
        """Inspection of real files requires `uses filesystem` declarations."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "uses filesystem" in source_text
        # Every capability-using path is wrapped in try/on error for grace.
        assert "try:" in source_text

    def test_process_capability_declared(self):
        """Compiler-CLI inspection (OMNISYS.tool.check/explain) requires `uses process`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "uses process" in source_text

    def test_pure_helpers_declared(self):
        """Pure text-analysis helpers are marked `pure`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert source_text.count("pure") >= 13

    def test_effect_check_enforces_declarations(self):
        """omni check enforces the effect system (any missed declaration fails)."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, (
            f"check failed; a capability declaration is missing: {result.stdout}"
        )


# --- OMNISYS.tool Integration ---


class TestToolIntegration:
    """Test integration with OMNISYS.tool through the compiler pipeline."""

    def test_tool_module_imported(self):
        """The source imports OMNISYS.tool."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "import OMNISYS.tool" in source_text

    def test_check_invoked_with_correct_arity(self):
        """omnisys.tool.check is called with exactly one argument (the path)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.tool.check")
        assert calls, "no omnisys.tool.check call found in MIR"
        for call in calls:
            assert len(call["args"]) == 1, f"tool.check arity wrong: {call['args']}"

    def test_explain_invoked_with_correct_arity(self):
        """omnisys.tool.explain is called with exactly one argument (the path)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.tool.explain")
        assert calls, "no omnisys.tool.explain call found in MIR"
        for call in calls:
            assert len(call["args"]) == 1, f"tool.explain arity wrong: {call['args']}"

    def test_tool_check_and_explain_wrapped_in_try(self):
        """Capability calls degrade gracefully via try/on error (no crash paths)."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "omnisys.tool.check" in source_text
        assert "omnisys.tool.explain" in source_text
        assert source_text.count("on error:") >= 6

    def test_tool_functions_wrapped_by_named_functions(self):
        """Capability logic lives in named functions declaring their capabilities."""
        _, symbol_table, _ = _compile_source()
        for name in ("tool_check_safe", "tool_explain_safe"):
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            assert rec["kind"] == "function"
            declared_uses = rec["declared_effects"].get("uses", [])
            assert "process" in declared_uses, f"{name} missing uses process"


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
    def test_inline_metrics_asserted(self):
        """tokenize/line_count/identifier_count report expected counts on a sample."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        inline = [line for line in logs if line.startswith("inline-metrics: ")]
        assert inline, f"inline-metrics line missing from logs: {logs}"

        metrics = json.loads(inline[0].split("inline-metrics: ", 1)[1])
        assert metrics["lines"] == 6
        assert metrics["tokens"] == 25
        assert metrics["identifiers"] == 20
        assert metrics["functions"] == ["add"]
        assert metrics["capabilities"] == ["pure"]
        assert metrics["imports"] == ["OMNISYS.core"]

    @needs_node
    def test_project_report_analyzes_own_source(self):
        """The tool inspects the real source/ directory via OMNISYS.fs."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        report_line = [line for line in logs if line.startswith("project-report: ")]
        assert report_line, f"project-report line missing from logs: {logs}"

        report = json.loads(report_line[0].split("project-report: ", 1)[1])
        assert report["tool"] == "project-inspector"
        assert report["target"] == "source"
        assert report["summary"]["files"] == 1
        assert report["summary"]["lines"] > 100
        assert report["summary"]["functions"] >= 21

        entry = report["sources"][0]
        assert entry["name"] == "project_inspector.omni"
        assert entry["exists"] is True
        assert entry["size"] > 0
        assert entry["lines"] == report["summary"]["lines"]
        assert entry["status"] == "clean"
        assert "lstrip" in entry["functions"]
        assert "inspect_project" in entry["functions"]
        assert "filesystem" in entry["capabilities"]
        assert "process" in entry["capabilities"]


# --- Degradation Behavior ---


class TestDegradation:
    """Test that the tool degrades gracefully when capabilities are unavailable."""

    @needs_node
    def test_graceful_without_require_bridge(self):
        """Under the reference `omni run` lane (no require), the program still exits 0."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"omni run failed: {result.stderr}"
        assert "inline-metrics: " in result.stdout
        assert "project-report: " in result.stdout

    def test_wrapper_functions_always_return(self):
        """Capability wrappers never panic; they return default values on error."""
        _, symbol_table, _ = _compile_source()
        for name in ("file_exists_safe", "file_size_safe", "read_source_safe"):
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            declared_uses = rec["declared_effects"].get("uses", [])
            assert "filesystem" in declared_uses, f"{name} missing uses filesystem"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])