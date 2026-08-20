# AI Assistant Tests — Project 6.1
# Automated test suite verifying the OmniScript local-AI-inference assistant.
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
SOURCE_FILE = PROJECT_DIR / "source" / "ai_assistant.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

EXPECTED_FUNCTIONS = [
    "create_model_layers",
    "extract_features",
    "run_inference",
    "softmax_probs",
    "argmax",
    "max_value",
    "intent_to_action",
    "format_intent_result",
    "classify_intent",
    "tool_greeting",
    "tool_weather",
    "tool_time",
    "tool_calculate",
    "tool_unknown",
    "dispatch_tool",
    "demo_tensor_ops",
    "demo_tensor_serialization",
    "process_input",
]


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

    ``omni run`` runs the program in a sandbox that never exposes ``require``;
    this harness binds ``global.require = require`` and stubs the DOM so the
    emitted ``<script>`` (which inlines the full OMNISYS runtime) can run
    standalone under Node.
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
        """omni check source/ai_assistant.omni exits with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"

    def test_build_succeeds(self):
        """omni build source/ai_assistant.omni succeeds (exit 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "assistant.html"
            result = run_omni(["build", str(SOURCE_FILE), "-o", str(out)])
            assert result.returncode == 0, f"Build failed: {result.stderr}"
            assert out.exists(), "build did not write the output artifact"
            assert out.stat().st_size > 0, "build artifact is empty"

    def test_verify_all_contracts_proven(self):
        """omni verify proves all contracts (status verified or no-contracts)."""
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Verify failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"

        assert data["results"], "verify returned no function results"
        assert len(data["results"]) == len(EXPECTED_FUNCTIONS)
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )


# --- Language / Type Declarations ---


class TestLanguageDeclarations:
    """Test the language-level structure: types, purity, symbol table."""

    def test_intent_result_type_declared(self):
        """The program declares the IntentResult structured-output type."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "type IntentResult = {" in source_text
        assert "action: Text" in source_text
        assert "confidence: Number" in source_text

    def test_tool_result_type_declared(self):
        """The program declares the ToolResult structured-output type."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "type ToolResult = {" in source_text
        assert "success: Boolean" in source_text
        assert "output: Text" in source_text

    def test_all_functions_declared_pure(self):
        """Every pipeline function is declared `pure` (no capabilities needed)."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        # 18 pure declarations: one per expected function.
        assert source_text.count("pure") >= len(EXPECTED_FUNCTIONS)

    def test_core_functions_in_symbol_table(self):
        """create_model_layers / classify_intent / process_input are function symbols."""
        _, symbol_table, _ = _compile_source()
        for name in ("create_model_layers", "classify_intent", "process_input"):
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            assert rec["kind"] == "function", f"{name} is not a function symbol"

    def test_core_functions_pure_in_mir(self):
        """The inference helpers lower to pure MIR functions (no uses/reads/writes)."""
        _, _, mir = _compile_source()
        for name in ("create_model_layers", "extract_features", "run_inference"):
            fn = mir.functions[name]
            assert fn.effects.pure, f"{name} is not marked pure in MIR"
            assert fn.effects.uses == []
            assert fn.effects.reads == []
            assert fn.effects.writes == []


# --- OMNISYS.ai Integration ---


class TestAiIntegration:
    """Test integration with OMNISYS.ai through the compiler pipeline."""

    def test_ai_module_imported(self):
        """The source imports OMNISYS.ai."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "import OMNISYS.ai" in source_text

    def test_predict_called_with_correct_arity(self):
        """omnisys.ai.predict is called with exactly two arguments (layers, features)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.ai.predict")
        assert calls, "no omnisys.ai.predict call found in MIR"
        for call in calls:
            assert len(call["args"]) == 2, f"predict arity wrong: {call['args']}"

    def test_softmax_called_with_correct_arity(self):
        """omnisys.ai.softmax is called with exactly one argument (the logits)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.ai.softmax")
        assert calls, "no omnisys.ai.softmax call found in MIR"
        for call in calls:
            assert len(call["args"]) == 1, f"softmax arity wrong: {call['args']}"

    def test_tensor_called_with_correct_arity(self):
        """omnisys.ai.tensor is called with exactly two arguments (shape, data)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.ai.tensor")
        assert calls, "no omnisys.ai.tensor call found in MIR"
        for call in calls:
            assert len(call["args"]) == 2, f"tensor arity wrong: {call['args']}"

    def test_tensor_matmul_called_with_correct_arity(self):
        """omnisys.ai.tensor_matmul is called with exactly two arguments (a, b)."""
        _, _, mir = _compile_source()
        calls = _collect_mir_calls(mir, "omnisys.ai.tensor_matmul")
        assert calls, "no omnisys.ai.tensor_matmul call found in MIR"
        for call in calls:
            assert len(call["args"]) == 2, f"tensor_matmul arity wrong: {call['args']}"


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
    def test_demo_markers_logged(self):
        """The app block prints the demo markers to console.log."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        assert any("=== AI Assistant Demo ===" in line for line in logs), (
            f"demo header missing from logs: {logs}"
        )
        assert any("Serialization round-trip: PASS" in line for line in logs), (
            f"serialization PASS marker missing from logs: {logs}"
        )
        assert any("=== Demo Complete ===" in line for line in logs), (
            f"demo completion marker missing from logs: {logs}"
        )

    @needs_node
    def test_all_inputs_classified_structured(self):
        """Every demo input produces a structured intent + tool output line."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_require(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        inputs = [
            "Hello there!",
            "What's the weather like?",
            "What time is it?",
            "Calculate 2 + 2",
            "Random nonsense input",
        ]
        for sample in inputs:
            assert any(line == "Input: " + sample for line in logs), (
                f"input {sample!r} not processed: {logs}"
            )

        intent_lines = [line for line in logs if line.startswith("  Intent: ")]
        assert len(intent_lines) == len(inputs), f"expected {len(inputs)} intent lines"
        for line in intent_lines:
            assert "confidence:" in line, f"intent line missing confidence: {line}"
            assert "QUERY_WEATHER" in line, f"unexpected classification: {line}"


# --- Degradation / Graceful Behavior ---


class TestDegradation:
    """Test graceful degradation and capability discipline."""

    def test_omni_run_exit_zero_with_markers(self):
        """omni run exits 0 and prints the full demo (pure program, no fs/secrets)."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"omni run failed: {result.stderr}"
        assert "=== AI Assistant Demo ===" in result.stdout
        assert "Serialization round-trip: PASS" in result.stdout
        assert "=== Demo Complete ===" in result.stdout

    def test_no_capability_declarations_needed(self):
        """The pure inference pipeline needs no `uses filesystem`/`uses secrets`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "uses filesystem" not in source_text
        assert "uses secrets" not in source_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])