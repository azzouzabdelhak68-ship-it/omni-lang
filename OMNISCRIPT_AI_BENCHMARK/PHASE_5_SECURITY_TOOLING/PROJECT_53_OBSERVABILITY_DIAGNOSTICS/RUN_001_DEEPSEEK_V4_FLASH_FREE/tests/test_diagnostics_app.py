# Application Diagnostics & Observability Tests — Project 5.3
# Verifies: omni check/build/verify, OMNISYS.observability API shape (from the
# compiler registry), source-level invocation arity/types, and a Node runtime
# test that executes the emitted program under a DOM stub and asserts on the
# in-process telemetry snapshot (metric record->query round trip, trace pairing,
# log levels, remediation result).

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
SOURCE_FILE = PROJECT_DIR / "source" / "diagnostics_app.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

OBSERVABILITY = {
    "log": ("Text, Text, Map", "None"),
    "info": ("Text, Map", "None"),
    "warn": ("Text, Map", "None"),
    "error": ("Text, Map", "None"),
    "metric": ("Text, Number", "None"),
    "metric_value": ("Text", "Number"),
    "trace_begin": ("Text", "Number"),
    "trace_end": ("Number, Map", "None"),
    "snapshot": ("", "Map"),
    "clear": ("", "None"),
    "profile": ("fn, Number", "Number"),
}


def run_omni(command: list[str]) -> subprocess.CompletedProcess:
    """Run an omni CLI command and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


def _emit_html() -> str:
    """Compile the source with the compiler pipeline and return emitted JS."""
    from omni_compiler.checker import analyze
    from omni_compiler.emitter import emit_js
    from omni_compiler.lexer import tokenize
    from omni_compiler.mir import to_mir
    from omni_compiler.parser import parse

    code = SOURCE_FILE.read_text(encoding="utf-8")
    ast = parse(tokenize(code))
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def _run_emitted(html: str) -> dict:
    """Run the emitted HTML under Node with a DOM stub and a snapshot epilogue.

    Returns {'logs': [...], 'snap': {'logs': ..., 'metrics': ..., 'traces': ...}}.
    The entry point executes synchronously (no awaits in the workload), so the
    observability snapshot is fully populated when runInThisContext returns.
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
global.__app = { innerHTML: "", addEventListener: () => {} };
global.document = {
  getElementById: () => global.__app,
  querySelectorAll: () => [],
  createElement: () => ({}),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
global.window = global;
vm.runInThisContext(code, { filename: htmlPath });
global.__snap = omnisys.observability.snapshot();
process.stdout.write(JSON.stringify({ logs: global.__logs, snap: global.__snap }) + "\n");
"""
    html_path = None
    runner_path = None
    try:
        with __import__("tempfile").NamedTemporaryFile(
            mode="w", suffix=".html", encoding="utf-8", delete=False
        ) as f:
            f.write(html)
            html_path = Path(f.name)
        with __import__("tempfile").NamedTemporaryFile(
            mode="w", suffix=".js", encoding="utf-8", delete=False
        ) as g:
            g.write(harness)
            runner_path = Path(g.name)
        proc = subprocess.run(
            ["node", str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 0, f"node runtime failed: {proc.stderr}"
        return json.loads(proc.stdout.strip())
    finally:
        if html_path is not None:
            html_path.unlink(missing_ok=True)
        if runner_path is not None:
            runner_path.unlink(missing_ok=True)


def _node_available() -> bool:
    return shutil.which("node") is not None


needs_node = pytest.mark.skipif(not _node_available(), reason="node not installed")


# --- Compiler checks ---------------------------------------------------------


class TestCompilerChecks:
    """The source file passes all static compiler checks."""

    def test_check_passes(self):
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"

    def test_build_succeeds(self):
        result = run_omni(["build", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert "target=js" in result.stdout

    def test_verify_all_contracts_proven(self):
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Verify failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"
        assert len(data["results"]) >= 10
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )


# --- OMNISYS.observability API shape (registry) -------------------------------


class TestObservabilityApiShape:
    """The registered observability module exposes the expected signatures."""

    @pytest.fixture(scope="class")
    def module(self):
        from omni_compiler.omnisys_registry import OMNISYS_MODULES

        return OMNISYS_MODULES["observability"]

    def test_module_registered(self, module):
        assert module is not None
        assert module.js_file == "omnisys/observability.js"

    def test_all_observability_functions_pure(self, module):
        # Every observability function must be pure (no capability effects).
        for name, fn in module.functions.items():
            assert fn.effects == frozenset(), f"{name} should be pure, got {fn.effects}"

    def test_function_signatures_match_contract(self, module):
        for name, (params, ret) in OBSERVABILITY.items():
            assert name in module.functions, f"missing {name}"
            expected = f"fn({params}) -> {ret}"
            assert module.functions[name].type == expected, (
                f"{name}: expected {expected}, got {module.functions[name].type}"
            )


# --- Source-level instrumentation (arity / types in the .omni source) ---------


class TestSourceInstrumentation:
    """The diagnostics program invokes the observability API with the right shape."""

    def test_source_calls_structured_log_levels(self):
        src = SOURCE_FILE.read_text(encoding="utf-8")
        # The app emits structured info + error records; warn/log are part of
        # the API (validated in TestObservabilityApiShape) but unused here.
        assert 'omnisys.observability.info("' in src
        assert 'omnisys.observability.error("' in src

    def test_source_calls_metric_counters_and_gauges(self):
        src = SOURCE_FILE.read_text(encoding="utf-8")
        assert "omnisys.observability.metric(" in src
        assert "omnisys.observability.metric_value(" in src
        assert "rejected_total" in src
        assert "accepted_total" in src
        assert "queue_depth" in src

    def test_source_calls_trace_and_snapshot(self):
        src = SOURCE_FILE.read_text(encoding="utf-8")
        assert "omnisys.observability.trace_begin(" in src
        assert "omnisys.observability.trace_end(" in src
        assert "omnisys.observability.snapshot()" in src
        assert "omnisys.observability.profile(" in src

    def test_source_has_struct_report_and_workload(self):
        src = SOURCE_FILE.read_text(encoding="utf-8")
        assert "type DiagnosticReport" in src
        assert "type DispatchTask" in src
        assert "when app starts" in src


# --- Language-rule negative probes (discovered during investigation) ---------


class TestDiscoveredLanguageRules:
    """Lock in the language rules discovered while building the app."""

    def test_module_scope_collision_rejected(self, tmp_path):
        """A name assigned in `when app starts` becomes module data; reusing it
        as a function-local (non-loop) variable triggers E-EFFECT-004."""
        src = """
import OMNISYS.observability
fn shared() -> Number:
    pure
    value = 1
    return value
end
when app starts:
    value = omnisys.observability.metric_value("x")
    show value
end
"""
        f = tmp_path / "collision.omni"
        f.write_text(src, encoding="utf-8")
        result = run_omni(["check", str(f)])
        assert result.returncode == 1
        assert "E-EFFECT-004" in result.stdout

    def test_loop_variable_shadow_is_exempt(self, tmp_path):
        """Loop variables shadow module scope and do NOT require writes."""
        src = """
import OMNISYS.core
when app starts:
    items = [1, 2, 3]
    total = 0
    for item in items:
        total = total + item
    end
    show total
end
"""
        f = tmp_path / "loop_ok.omni"
        f.write_text(src, encoding="utf-8")
        result = run_omni(["check", str(f)])
        assert result.returncode == 0, f"unexpected: {result.stdout}"

    def test_to_text_not_in_registry(self):
        """OMNISYS.core.to_text does not exist (brief was stale); text coercion
        is implicit via `+` concatenation."""
        src = """
import OMNISYS.core
fn txt(v: Number) -> Text:
    pure
    return omnisys.core.to_text(v)
end
when app starts:
    show txt(1)
end
"""
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".omni", encoding="utf-8", delete=False
        ) as f:
            f.write(src)
            path = Path(f.name)
        try:
            result = run_omni(["check", str(path)])
            assert result.returncode == 1
            assert "E-NAME-001" in result.stdout
        finally:
            path.unlink(missing_ok=True)


# --- Runtime behavior under Node (DOM stub harness) ---------------------------


@needs_node
class TestRuntimeTelemetry:
    """Execute the emitted program and assert on the in-process snapshot."""

    @pytest.fixture(scope="class")
    def runtime(self):
        return _run_emitted(_emit_html())

    def test_program_runs_to_completion(self, runtime):
        assert any("Diagnostics App Complete" in line for line in runtime["logs"])

    def test_metric_record_to_query_round_trip(self, runtime):
        metrics = runtime["snap"]["metrics"]
        # Final state is the remediated batch: priorities 1..5, max_allowed 3,
        # strict `>` gate -> 3 accepted, 2 rejected.
        assert metrics["accepted_total"] == 3
        assert metrics["rejected_total"] == 2
        assert metrics["queue_depth"] == 5

    def test_trace_begin_end_pairing(self, runtime):
        traces = runtime["snap"]["traces"]
        assert len(traces) == 5
        for tr in traces:
            assert tr["end"] is not None, f"unpaired trace: {tr['id']}"
            assert tr["duration"] >= 0
        failed = [tr for tr in traces if tr["fields"]["ok"] is False]
        assert len(failed) == 2

    def test_structured_log_levels_captured(self, runtime):
        levels = [entry["level"] for entry in runtime["snap"]["logs"]]
        assert "info" in levels
        assert "error" in levels
        assert levels.count("error") == 2  # only the remediated batch remains

    def test_error_log_carries_fields(self, runtime):
        errors = [e for e in runtime["snap"]["logs"] if e["level"] == "error"]
        for e in errors:
            assert "REJECTED priority" in e["message"]
            assert e["fields"]["task"].startswith("t-")

    def test_remediation_verified_at_runtime(self, runtime):
        logs = runtime["logs"]
        assert any("phase1 buggy rejected: 3" in line for line in logs)
        assert any("phase3 fixed rejected: 2" in line for line in logs)
        assert any("rejections dropped from 3 to 2" in line for line in logs)
        assert any("boundary case confirmed" in line for line in logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])