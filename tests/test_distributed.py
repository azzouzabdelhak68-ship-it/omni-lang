"""v5.3 — Distributed Systems: actor model, clustering, fault tolerance, chaos.

The `sim.actor` runtime (simulation_engine/runtime.js) is a self-contained,
dependency-free Node.js module. These tests exercise it three ways:

1. Runtime unit + chaos tests: small JS programs run under Node via a
   subprocess (skipped gracefully when `node` is absent, mirroring the
   `test_c_emitter.py` gcc/cargo skip pattern). Chaos is injected through
   explicit runtime hooks (partition/heal/fail/restart) at deterministic
   points — never through sleeps or randomness.
2. Clustering: two nodes exchange messages; membership converges via
   heartbeats; a failed node is detected and removed.
3. Integration: examples/actors.omni and examples/chaos.omni compile through
   the full Python pipeline (lexer -> parser -> checker -> MIR -> JS emitter)
   and, when node is present, run end-to-end through the Node harness.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_JS = ROOT / "simulation_engine" / "runtime.js"
EXAMPLES = ROOT / "examples"
SCRIPTS = ROOT / "scripts"


def _node_available() -> bool:
    return shutil.which("node") is not None


NEEDS_NODE = pytest.mark.skipif(not _node_available(), reason="node not installed")


def _emit_html(code: str) -> str:
    """Run the OmniScript pipeline and return the emitted JS HTML document."""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def _run_node(js: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", encoding="utf-8", delete=False) as f:
        f.write(js)
        path = Path(f.name)
    try:
        return subprocess.run(
            ["node", str(path)], capture_output=True, text=True, timeout=timeout, check=False
        )
    finally:
        path.unlink(missing_ok=True)


def _js_program(body: str) -> str:
    return (
        '"use strict";\n'
        f"const {{ createRuntime }} = require({str(RUNTIME_JS)!r});\n"
        "const sim = createRuntime().sim;\n"
        + body
    )


def _js_result(body: str) -> Any:
    """Run a JS program; return the JSON value printed on its last stdout line."""
    proc = _run_node(_js_program(body))
    assert proc.returncode == 0, proc.stderr
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, "no JSON result was printed"
    return json.loads(lines[-1])


# --------------------------------------------------------------------------
# Runtime unit tests
# --------------------------------------------------------------------------


@NEEDS_NODE
def test_spawn_send_receive_happy_path() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("happy");
        sim.actor.cluster.addNode(c, "n1");
        const counter = sim.actor.spawn(c, "n1", "counter",
          (s, m) => (m === "inc" ? s + 1 : s), 0);
        sim.actor.send(c, counter, "inc");
        sim.actor.send(c, counter, "inc");
        sim.actor.run(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "counter");
        console.log(JSON.stringify({ state: a.state, processed: a.processed }));
        """
    )
    assert result == {"state": 2, "processed": 2}


@NEEDS_NODE
def test_message_ordering_per_mailbox() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("order");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.spawn(c, "n1", "bucket", (s, m) => (s || []).concat(m), []);
        sim.actor.send(c, "n1/bucket", "a");
        sim.actor.send(c, "n1/bucket", "b");
        sim.actor.send(c, "n1/bucket", "c");
        sim.actor.run(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "bucket");
        console.log(JSON.stringify(a.state));
        """
    )
    assert result == ["a", "b", "c"]


@NEEDS_NODE
def test_dead_letter_unknown_target() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("dead");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.spawn(c, "n1", "counter", (s) => s, 0);
        sim.actor.send(c, "n1/ghost", "hi");
        sim.actor.run(c);
        const dl = sim.actor.deadletters(c);
        const st = sim.actor.statistics(c);
        console.log(JSON.stringify({
          dead: st.dead, delivered: st.delivered, sent: st.sent,
          reason: dl[0] && dl[0].reason }));
        """
    )
    assert result == {"dead": 1, "delivered": 0, "sent": 0, "reason": "unknown-actor"}


@NEEDS_NODE
def test_receive_primitive_filters_messages() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("filter");
        sim.actor.cluster.addNode(c, "n1");
        const h = sim.actor.receive(
          (s, m) => (s || []).concat(m), (msg) => msg === "keep");
        sim.actor.spawn(c, "n1", "f", h, []);
        sim.actor.send(c, "n1/f", "drop");
        sim.actor.send(c, "n1/f", "keep");
        sim.actor.run(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "f");
        console.log(JSON.stringify({ state: a.state, dropped: h.dropped }));
        """
    )
    assert result == {"state": ["keep"], "dropped": 1}


@NEEDS_NODE
def test_actor_crash_supervision_restarts_and_resets_state() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("crash");
        sim.actor.cluster.addNode(c, "n1");
        const beh = (s, m) => {
          if (m === "boom") throw new Error("boom");
          return (s || 0) + 1;
        };
        sim.actor.spawn(c, "n1", "a", beh, 0);
        sim.actor.send(c, "n1/a", "boom");
        sim.actor.send(c, "n1/a", "ok");
        sim.actor.run(c);
        const st = sim.actor.statistics(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "a");
        const out = {
          state: a.state, restarts: a.restarts, crashes: a.crashes,
          alive: a.alive, dead: st.dead, delivered: st.delivered };
        console.log(JSON.stringify(out));
        """
    )
    assert result == {
        "state": 1,
        "restarts": 1,
        "crashes": 1,
        "alive": True,
        "dead": 1,
        "delivered": 1,
    }


@NEEDS_NODE
def test_actor_crash_restart_limit_dead_letters_mailbox() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("stop", { maxActorRestarts: 1 });
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.spawn(c, "n1", "a", (s, m) => {
          if (m === "boom") throw new Error("x");
          return s;
        }, 0);
        sim.actor.send(c, "n1/a", "boom");
        sim.actor.send(c, "n1/a", "boom");
        sim.actor.send(c, "n1/a", "leftover");
        sim.actor.run(c);
        const st = sim.actor.statistics(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "a");
        const out = {
          alive: a.alive, stopped: a.stopped, restarts: a.restarts,
          crashes: a.crashes, dead: st.dead, mailbox: a.mailbox.length };
        console.log(JSON.stringify(out));
        """
    )
    assert result == {
        "alive": False,
        "stopped": True,
        "restarts": 1,
        "crashes": 2,
        "dead": 3,
        "mailbox": 0,
    }


@NEEDS_NODE
def test_runtime_api_surface_nested_and_flat_bridge() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("surf");
        const flat = sim.spawn("surf.coordinator", "x", (s) => s, 0);
        const nested = sim.actor.spawn(c, "surf.coordinator", "y", (s) => s, 0);
        console.log(JSON.stringify({
          spawn: typeof sim.actor.spawn,
          send: typeof sim.actor.send,
          receive: typeof sim.actor.receive,
          clusterCreate: typeof sim.actor.cluster.create,
          flatSpawn: flat.__omniActor,
          nestedSpawn: nested.__omniActor,
          version: sim.version,
        }));
        """
    )
    assert result == {
        "spawn": "function",
        "send": "function",
        "receive": "function",
        "clusterCreate": "function",
        "flatSpawn": True,
        "nestedSpawn": True,
        "version": "5.3.0",
    }


# --------------------------------------------------------------------------
# Clustering tests
# --------------------------------------------------------------------------


@NEEDS_NODE
def test_cluster_two_nodes_exchange_messages() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("ring");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.cluster.addNode(c, "n2");
        const a = sim.actor.spawn(c, "n1", "a", (s, m) => {
          if (m === "go") sim.actor.send(c, "n2/b", "hello");
          return s;
        }, 0);
        sim.actor.spawn(c, "n2", "b", (s, m) => (s || []).concat(m), []);
        sim.actor.send(c, a, "go");
        sim.actor.run(c);
        const snap = sim.actor.cluster.snapshot(c);
        const b = snap.nodes.find(n => n.id === "n2").actors.find(x => x.name === "b");
        console.log(JSON.stringify(b.state));
        """
    )
    assert result == ["hello"]


@NEEDS_NODE
def test_membership_converges_via_heartbeats_and_detects_failure() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("memb");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.cluster.addNode(c, "n2");
        sim.actor.steps(c, c.config.heartbeatInterval);
        const before = sim.actor.cluster.members(c, "n1");
        sim.actor.cluster.fail(c, "n2", { restart: false });
        sim.actor.steps(c, c.config.heartbeatTimeout + 2);
        const after = sim.actor.cluster.members(c, "n1");
        const snap = sim.actor.cluster.snapshot(c);
        const n2 = snap.nodes.find(n => n.id === "n2");
        console.log(JSON.stringify({
          before, after, n2Removed: n2.removed, failures: snap.stats.failures }));
        """
    )
    assert result == {
        "before": ["memb.coordinator", "n1", "n2"],
        "after": ["memb.coordinator", "n1"],
        "n2Removed": True,
        # 1 from the explicit fail() + 1 from heartbeat detection of the death
        "failures": 2,
    }


@NEEDS_NODE
def test_partition_holds_messages_until_heal_then_redelivers() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("part");
        sim.actor.cluster.addNode(c, "n1");
        const counter = sim.actor.spawn(c, "n1", "counter",
          (s, m) => (m === "inc" ? s + 1 : s), 0);
        sim.actor.cluster.partition(c, "part.coordinator", "n1");
        sim.actor.send(c, counter, "inc");
        sim.actor.run(c);
        const during = sim.actor.statistics(c);
        sim.actor.cluster.heal(c, "part.coordinator", "n1");
        sim.actor.run(c);
        const after = sim.actor.statistics(c);
        const snap = sim.actor.cluster.snapshot(c);
        const a = snap.nodes.find(n => n.id === "n1").actors.find(x => x.name === "counter");
        console.log(JSON.stringify({
          during, after, state: a.state, redelivered: after.redelivered }));
        """
    )
    during = result["during"]
    after = result["after"]
    assert isinstance(during, dict) and isinstance(after, dict)
    assert during["sent"] == 1
    assert during["delivered"] == 0
    assert during["dead"] == 0
    assert after["delivered"] == 1
    assert after["dead"] == 0
    assert result["state"] == 1
    assert result["redelivered"] >= 1


@NEEDS_NODE
def test_heal_redelivery_dead_letters_when_target_is_gone() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("dlpart");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.spawn(c, "n1", "counter", (s) => s, 0);
        sim.actor.cluster.partition(c, "dlpart.coordinator", "n1");
        sim.actor.send(c, "n1/counter", "inc");
        sim.actor.cluster.heal(c, "dlpart.coordinator", "n1");
        sim.actor.cluster.stopActor(c, "n1", "counter");
        sim.actor.run(c);
        const st = sim.actor.statistics(c);
        const dl = sim.actor.deadletters(c);
        console.log(JSON.stringify({
          dead: st.dead, delivered: st.delivered, reason: dl[0] && dl[0].reason }));
        """
    )
    assert result == {"dead": 1, "delivered": 0, "reason": "actor-gone"}


# --------------------------------------------------------------------------
# Chaos tests
# --------------------------------------------------------------------------


@NEEDS_NODE
def test_node_failure_supervisor_restart_has_no_message_loss() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("fail");
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.cluster.addNode(c, "n2");
        sim.actor.spawn(c, "n1", "acc", (s, m) => (m === "inc" ? s + 1 : s), 0);
        sim.actor.spawn(c, "n2", "log", (s, m) => (s || []).concat(m), []);
        sim.actor.send(c, "n2/log", "ping");
        sim.actor.cluster.fail(c, "n2");
        sim.actor.send(c, "n2/log", "after-crash");
        sim.actor.run(c);
        const st = sim.actor.statistics(c);
        const snap = sim.actor.cluster.snapshot(c);
        const log = snap.nodes.find(n => n.id === "n2").actors.find(x => x.name === "log");
        const out = {
          sent: st.sent, delivered: st.delivered, dead: st.dead,
          restarts: st.restarts, log: log.state, alive: log.alive };
        console.log(JSON.stringify(out));
        """
    )
    assert result == {
        "sent": 2,
        "delivered": 2,
        "dead": 0,
        "restarts": 1,
        "log": ["ping", "after-crash"],
        "alive": True,
    }


@NEEDS_NODE
def test_node_failure_restart_limit_removes_and_dead_letters() -> None:
    result = _js_result(
        """
        const c = sim.actor.cluster.create("flimit", { maxNodeRestarts: 1 });
        sim.actor.cluster.addNode(c, "n1");
        sim.actor.cluster.addNode(c, "n2");
        sim.actor.spawn(c, "n2", "log", (s, m) => s, 0);
        sim.actor.send(c, "n2/log", "m1");
        sim.actor.cluster.fail(c, "n2");
        sim.actor.run(c);
        sim.actor.cluster.fail(c, "n2");
        sim.actor.send(c, "n2/log", "m2");
        sim.actor.run(c);
        const st = sim.actor.statistics(c);
        const snap = sim.actor.cluster.snapshot(c);
        const n2 = snap.nodes.find(n => n.id === "n2");
        const out = {
          restarts: st.restarts, dead: st.dead, delivered: st.delivered,
          removed: n2.removed, alive: n2.alive };
        console.log(JSON.stringify(out));
        """
    )
    assert result == {"restarts": 1, "dead": 1, "delivered": 1, "removed": True, "alive": False}


@NEEDS_NODE
def test_chaos_scenario_is_deterministic_across_replays() -> None:
    proc = _run_node(
        _js_program(
            """
            function scenario() {
              const rt2 = createRuntime();
              const sim2 = rt2.sim;
              const c = sim2.actor.cluster.create("det");
              sim2.actor.cluster.addNode(c, "n1");
              sim2.actor.cluster.addNode(c, "n2");
              sim2.actor.spawn(c, "n1", "acc", (s, m) => (m === "inc" ? s + 1 : s), 0);
              sim2.actor.spawn(c, "n2", "log", (s, m) => (s || []).concat(m), []);
              sim2.actor.send(c, "n2/log", "a");
              sim2.actor.cluster.partition(c, "det.coordinator", "n2");
              sim2.actor.send(c, "n2/log", "b");
              sim2.actor.cluster.fail(c, "n2");
              sim2.actor.cluster.heal(c, "det.coordinator", "n2");
              sim2.actor.send(c, "n1/acc", "inc");
              sim2.actor.run(c);
              return JSON.stringify(sim2.actor.cluster.snapshot(c));
            }
            const s1 = scenario();
            const s2 = scenario();
            console.log(JSON.stringify({ identical: s1 === s2, s1 }));
            """
        )
    )
    assert proc.returncode == 0, proc.stderr
    parsed = json.loads(proc.stdout.splitlines()[-1])
    assert parsed["identical"] is True


# --------------------------------------------------------------------------
# Integration: OmniScript example -> pipeline -> Node harness
# --------------------------------------------------------------------------


def test_example_actors_compiles_through_pipeline() -> None:
    code = (EXAMPLES / "actors.omni").read_text(encoding="utf-8")
    html = _emit_html(code)
    markers = (
        "sim.cluster(",
        "sim.node(",
        "sim.spawn(",
        "sim.send(",
        "sim.partition(",
        "sim.heal(",
        "sim.run(",
        "sim.members(",
    )
    for marker in markers:
        assert marker in html


def test_example_chaos_compiles_through_pipeline() -> None:
    code = (EXAMPLES / "chaos.omni").read_text(encoding="utf-8")
    html = _emit_html(code)
    for marker in ("sim.cluster(", "sim.node(", "sim.spawn(", "sim.fail(", "sim.run("):
        assert marker in html


def test_checker_allows_sim_prefix_calls_and_behavior_arguments() -> None:
    code = """
fn counter_behavior(state: Number, msg: Text) -> Number:
    if msg is "inc":
        return state + 1
    end
    return state
end

when app starts:
    sim.cluster("c")
    sim.node("n1")
    counter = sim.spawn("n1", "counter", counter_behavior, 0)
    sim.send(counter, "inc")
    sim.run()
    show "ok"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)  # must not raise


@NEEDS_NODE
def test_example_actors_runs_through_harness(tmp_path: Path) -> None:
    html = _emit_html((EXAMPLES / "actors.omni").read_text(encoding="utf-8"))
    out = tmp_path / "actors.html"
    out.write_text(html, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(SCRIPTS / "run-actors.js"), str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["during partition", "demo.coordinator, n1, n2", "done"]


@NEEDS_NODE
def test_example_chaos_runs_through_harness(tmp_path: Path) -> None:
    html = _emit_html((EXAMPLES / "chaos.omni").read_text(encoding="utf-8"))
    out = tmp_path / "chaos.html"
    out.write_text(html, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(SCRIPTS / "run-actors.js"), str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["ping", "after-crash", "chaos done"]


@NEEDS_NODE
def test_run_actors_script_cli_end_to_end() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "run-actors.py"), str(EXAMPLES / "actors.omni")],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "during partition" in proc.stdout
    assert "done" in proc.stdout


def test_run_actors_script_missing_arguments() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "run-actors.py")],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 2  # noqa: PLR2004


@NEEDS_NODE
def test_run_actors_script_missing_file() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "run-actors.py"), "tests/no_such_file.omni"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 1  # noqa: PLR2004