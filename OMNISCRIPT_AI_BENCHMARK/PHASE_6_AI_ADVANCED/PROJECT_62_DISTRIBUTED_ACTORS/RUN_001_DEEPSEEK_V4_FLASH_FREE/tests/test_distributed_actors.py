# Distributed Actor Cluster Tests — Project 6.2
# Automated test suite verifying the flat sim.* actor-cluster program.
# Mirrors the structure of test_project_inspector.py (Project 5.4):
# run_omni helper, tokenize/parse/analyze/to_mir compile, MIR call walker,
# needs_node skipif, class-based groups, and a graceful-degradation class.

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
SOURCE_FILE = PROJECT_DIR / "source" / "distributed_actors.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]

# Repo root E:\simualtion — parents[0] is PROJECT_62_..., [3] is the repo root.
REPO_ROOT = PROJECT_DIR.parents[3]
SIM_RUNTIME = REPO_ROOT / "simulation_engine" / "runtime.js"

DEMO_HEADER = "=== DISTRIBUTED ACTOR CLUSTER DEMO (Project 6.2) ==="
COMPLETE_MARKER = "=== ALL SCENARIOS COMPLETE ==="
SCENARIO_HEADERS = [
    "=== SCENARIO 1: Basic Cluster ===",
    "=== SCENARIO 2: Partition & Heal ===",
    "=== SCENARIO 3: Node Failure & Restart ===",
    "=== SCENARIO 4: Deterministic Ordering ===",
    "=== SCENARIO 5: Dead Letters ===",
    "=== SCENARIO 6: Stats & Membership ===",
]

# Functions that call the flat sim.* surface and must declare `uses network`.
NETWORK_FUNCTIONS = [
    "create_cluster",
    "add_nodes",
    "spawn_actors",
    "send_messages",
    "run_cluster",
    "run_cluster_steps",
    "partition_nodes",
    "heal_nodes",
    "fail_node",
    "restart_node",
    "get_members",
    "get_snapshot",
    "show_snapshot",
    "show_deadletters",
    "show_status",
    "get_deadletters",
    "get_stats",
    "get_status",
    "scenario_basic",
    "scenario_partition_heal",
    "scenario_fail_restart",
    "scenario_ordering",
    "scenario_dead_letters",
    "scenario_stats_membership",
]

# Pure actor behaviors / helpers — no network effects.
PURE_FUNCTIONS = [
    "counter_behavior",
    "logger_behavior",
    "pong_behavior",
    "forwarder_behavior",
    "echo_behavior",
    "make_initial_logger_state",
    "make_initial_forwarder_state",
    "format_members",
    "format_stats",
]

# Flat sim.* names exercised by the program (single-dot call names only).
FLAT_SIM_CALLS = [
    "sim.spawn",
    "sim.send",
    "sim.cluster",
    "sim.node",
    "sim.run",
    "sim.steps",
    "sim.partition",
    "sim.heal",
    "sim.fail",
    "sim.restart",
    "sim.members",
    "sim.deadletters",
    "sim.stats",
    "sim.status",
    "sim.snapshot",
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


def _run_emitted_with_sim(html: str) -> subprocess.CompletedProcess[str]:
    """Run an emitted HTML document under Node with a DOM stub + sim bridge.

    Mirrors scripts/run-omnisys.js: binds ``global.sim`` from
    simulation_engine/runtime.js so the flat ``sim.*`` calls resolve, exposes
    ``require`` for the inlined OMNISYS runtimes, and exits 0 after flushing
    the captured logs exactly like the reference runner lane.
    """
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const simRuntimePath = process.argv[3];
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
try {
  global.sim = require(simRuntimePath).createRuntime().sim;
} catch (e) {
  console.error("sim bind failed: " + (e && e.stack ? e.stack : e));
  process.exit(3);
}
try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("program failed: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}
process.stdout.write(JSON.stringify(global.__logs) + "\n");
process.exit(0);
"""
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
            g.write(harness)
            runner_path = Path(g.name)
        return subprocess.run(
            ["node", str(runner_path), str(html_path), str(SIM_RUNTIME)],
            capture_output=True,
            text=True,
            timeout=120,
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
        """omni check source/distributed_actors.omni exits with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Compiler check failed: {result.stderr}"
        assert "omni check: OK" in result.stdout

    def test_build_succeeds(self):
        """omni build source/distributed_actors.omni succeeds (exit 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "distributed_actors.html"
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
        assert len(data["results"]) >= 20, "expected the 20+ functions to be verified"
        for fn_result in data["results"]:
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )


# --- Capability Declarations ---


class TestCapabilityDeclarations:
    """Test that capability declarations are present and correct."""

    def test_network_capability_declared_in_source(self):
        """Every sim.*-calling function declares `uses network`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert source_text.count("uses network") >= 24  # 18 ops + 6 scenarios

    def test_pure_behaviors_declared(self):
        """Actor behaviors and pure helpers are marked `pure`."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert source_text.count("pure") >= 9

    def test_network_functions_use_network(self):
        """Network/scenario functions declare uses network in the symbol table."""
        _, symbol_table, _ = _compile_source()
        for name in NETWORK_FUNCTIONS:
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            assert rec["kind"] == "function"
            declared_uses = rec["declared_effects"].get("uses", [])
            assert "network" in declared_uses, f"{name} missing uses network"

    def test_pure_functions_have_no_network(self):
        """Behaviors/helpers have no uses network (they are pure)."""
        _, symbol_table, _ = _compile_source()
        for name in PURE_FUNCTIONS:
            rec = symbol_table.inspect_symbol(name)
            assert rec is not None, f"symbol {name} missing"
            declared_effects = rec["declared_effects"]
            assert "network" not in declared_effects.get("uses", []), (
                f"{name} must not declare uses network"
            )
            assert declared_effects.get("pure") is True, f"{name} must be pure"

    def test_scenario_functions_use_network(self):
        """All six scenario entry points declare `uses network`."""
        _, symbol_table, _ = _compile_source()
        for name in NETWORK_FUNCTIONS[-6:]:  # the six scenario_* functions
            rec = symbol_table.inspect_symbol(name)
            assert "network" in rec["declared_effects"].get("uses", [])


# --- Flat sim.* Integration ---


class TestFlatSimIntegration:
    """Test integration with the flat sim.* actor API and OMNISYS modules."""

    def test_omnisys_modules_imported(self):
        """The source imports OMNISYS.collections and OMNISYS.core."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "import OMNISYS.collections" in source_text
        assert "import OMNISYS.core" in source_text

    def test_collections_calls_in_mir(self):
        """list_push/map_get/map_set/list_join appear as MIR calls."""
        _, _, mir = _compile_source()
        for name in (
            "omnisys.collections.list_push",
            "omnisys.collections.map_get",
            "omnisys.collections.map_set",
            "omnisys.collections.list_join",
        ):
            calls = _collect_mir_calls(mir, name)
            assert calls, f"no {name} call found in MIR"

    def test_flat_sim_calls_in_source(self):
        """The source exercises every flat sim.* operation."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        for name in FLAT_SIM_CALLS:
            assert source_text.count(name) >= 1, f"{name} missing from source"

    def test_flat_sim_calls_in_mir(self):
        """Key sim.* operations lower to MIR call nodes."""
        _, _, mir = _compile_source()
        for name in (
            "sim.cluster",
            "sim.spawn",
            "sim.send",
            "sim.partition",
            "sim.heal",
            "sim.fail",
            "sim.restart",
            "sim.members",
            "sim.snapshot",
            "sim.stats",
            "sim.status",
            "sim.deadletters",
        ):
            calls = _collect_mir_calls(mir, name)
            assert calls, f"no {name} call found in MIR"

    def test_no_multi_dot_sim_names(self):
        """The parser only accepts single-dot call names; no sim.actor.* in source."""
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        assert "sim.actor." not in source_text


# --- Runtime Behavior (Node) ---


class TestRuntimeBehavior:
    """Test the emitted program under Node with a sim-bridging DOM harness."""

    @needs_node
    def test_sim_runtime_resolvable(self):
        """The simulation runtime used by the harness exists at the expected path."""
        assert SIM_RUNTIME.exists(), f"sim runtime missing: {SIM_RUNTIME}"

    @needs_node
    def test_program_runs_under_node(self):
        """Emitted program exits 0 under the Node harness (all scenarios run)."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_sim(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

    @needs_node
    def test_all_scenarios_complete(self):
        """The emitted program logs every scenario header and the completion marker."""
        _, _, mir = _compile_source()
        html = emit_js(mir)
        proc = _run_emitted_with_sim(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"

        logs = _program_logs(proc)
        joined = "\n".join(logs)
        assert DEMO_HEADER in joined
        assert COMPLETE_MARKER in joined
        for header in SCENARIO_HEADERS:
            assert header in joined, f"missing log marker: {header}"

    @needs_node
    def test_scenario_done_returns_are_compiled(self):
        """Each scenario returns its 'SCENARIO N DONE' string (app discards them).

        The app block calls the scenarios without printing their return values,
        so the DONE strings never reach stdout; the runtime markers above prove
        each scenario ran. This test proves the DONE returns are compiled in.
        """
        _, _, mir = _compile_source()
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        for n in range(1, 7):
            assert f'return "SCENARIO {n} DONE"' in source_text
        html = emit_js(mir)
        proc = _run_emitted_with_sim(html)
        assert proc.returncode == 0, f"runtime failed: {proc.stderr}"
        logs = _program_logs(proc)
        # The 6 scenarios ran and the program completed cleanly.
        assert sum("=== SCENARIO" in line for line in logs) == 6


# --- Degradation Behavior ---


class TestDegradation:
    """Test that the program degrades gracefully under the reference runner."""

    def test_graceful_under_omni_run(self):
        """`omni run` exits 0 and prints all scenario markers."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"omni run failed: {result.stderr}"
        assert DEMO_HEADER in result.stdout
        assert COMPLETE_MARKER in result.stdout
        for header in SCENARIO_HEADERS:
            assert header in result.stdout, f"missing run marker: {header}"

    def test_app_block_invokes_all_scenarios(self):
        """The when-app-starts block calls all six scenario functions."""
        _, _, mir = _compile_source()
        for name in NETWORK_FUNCTIONS[-6:]:
            calls = _collect_mir_calls(mir, name)
            assert calls, f"app block never calls {name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
