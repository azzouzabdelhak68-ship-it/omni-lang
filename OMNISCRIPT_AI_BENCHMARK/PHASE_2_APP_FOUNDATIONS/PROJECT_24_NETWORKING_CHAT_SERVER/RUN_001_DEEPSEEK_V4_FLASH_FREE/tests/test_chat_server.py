"""Automated test suite for the OmniScript multi-client chat server (Project 2.4).

Verifies (all inside the dedicated run directory):
  * compiler acceptance: `omni check` / `omni run` exit 0
  * capability model: declared network usage enforced (negative probes),
    module-data reads enforced (E-EFFECT-004)
  * connect/disconnect lifecycle, protocol parsing and channel-scoped
    broadcasting against the *compiled JS artifact* driven in Node with
    simulated clients over the OMNISYS.net in-process request/response
    transport
  * concurrency: a burst of interleaved joins/broadcasts keeps the client
    registry and message log consistent (the synchronous transport serializes
    arrivals by construction)
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "chat_server.omni"
TESTS_DIR = Path(__file__).resolve().parent
SNIPPETS = TESTS_DIR / "snippets"
DRIVER = TESTS_DIR / "node_driver.js"
BUILD = RUN_DIR / "build"
ARTIFACT = BUILD / "chat_server.html"

# repo root that provides the omni_compiler package
REPO_ROOT = Path(__file__).resolve().parents[5]
assert REPO_ROOT.is_dir() and (REPO_ROOT / "omni_compiler").is_dir(), REPO_ROOT

COMPILER = [sys.executable, "-m", "omni_compiler.cli"]
NODE = shutil.which("node")
assert NODE, "node is required to drive the compiled JS artifact"


def run(cmd, cwd=REPO_ROOT, timeout=120):
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    return proc


def write_source(path: Path, text: str) -> Path:
    """Write UTF-8 without BOM (the OmniScript lexer rejects a BOM)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


@pytest.fixture(scope="session")
def artifact():
    proc = run([*COMPILER, "build", str(SOURCE), "--target", "js", "--output", str(ARTIFACT)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ARTIFACT.exists()
    return ARTIFACT


def run_snippet(artifact, name):
    snippet = SNIPPETS / name
    proc = subprocess.run(
        [NODE, str(DRIVER), str(artifact), str(snippet)],
        cwd=RUN_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert proc.returncode == 0, f"{name}: rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}"
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise AssertionError(f"{name}: non-JSON stdout: {proc.stdout!r}") from exc


# ---- compiler acceptance --------------------------------------------------

def test_check_passes():
    proc = run([*COMPILER, "check", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "omni check: OK" in proc.stdout


def test_run_passes_and_executes_entry_block():
    # `omni run` compiles AND executes the emitted program under Node, so the
    # entry block's `show` message must appear on stdout.
    proc = run([*COMPILER, "run", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "chat_server.omni loaded" in proc.stdout


# ---- capability model ------------------------------------------------------

def test_transport_lifecycle_declares_network():
    proc = run([*COMPILER, "inspect", "start_server", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert "network" in rec["declared_effects"]["uses"]


def test_protocol_client_function_declares_network():
    proc = run([*COMPILER, "inspect", "connect_client", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert "network" in rec["declared_effects"]["uses"]


def test_pure_parser_carries_no_capability():
    proc = run([*COMPILER, "inspect", "parse_message", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["declared_effects"]["uses"] == []
    assert rec["declared_effects"]["pure"] is True


def test_module_data_read_declared():
    proc = run([*COMPILER, "inspect", "client_names", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["declared_effects"]["reads"] == ["client_registry"]


def test_missing_network_declaration_rejected():
    bad = write_source(BUILD / "bad_missing_effect.omni", (
        "import OMNISYS.net\n"
        "\n"
        "fn fetch() -> Number:\n"
        "    response_value = omnisys.net.get(\"inproc://test/x\")\n"
        "    return 0\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-EFFECT-003" in proc.stdout
    assert "network" in proc.stdout


def test_app_block_cannot_call_network_directly():
    bad = write_source(BUILD / "bad_app_direct.omni", (
        "import OMNISYS.net\n"
        "\n"
        "when app starts:\n"
        "    response_value = omnisys.net.get(\"inproc://test/x\")\n"
        "    show response_value\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-EFFECT-003" in proc.stdout
    assert "app starts" in proc.stdout


def test_module_data_read_without_declaration_rejected():
    # The checker enforces `reads <module-resource>` at function boundaries
    # (E-EFFECT-004); a pure function reading the registry without declaring
    # it must be rejected.
    bad = write_source(BUILD / "bad_undeclared_read.omni", (
        "import OMNISYS.collections\n"
        "\n"
        "fn peek() -> Text:\n"
        "    pure\n"
        "    return omnisys.collections.list_join(omnisys.collections.map_keys(client_registry), \",\")\n"
        "end\n"
        "\n"
        "when app starts:\n"
        "    client_registry = []\n"
        "    show peek()\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-EFFECT-004" in proc.stdout
    assert "client_registry" in proc.stdout


def test_doc_phantom_net_listen_rejected():
    # docs/omnisys/net/README.md documents `net.listen(port)`; the registry has
    # no such function, so it must be rejected (docs lag the registry).
    bad = write_source(BUILD / "bad_net_listen.omni", (
        "import OMNISYS.net\n"
        "\n"
        "fn listen_probe(port: Number) -> Number:\n"
        "    uses network\n"
        "    response_value = omnisys.net.listen(port)\n"
        "    return 0\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-NAME" in proc.stdout or "E-IMPORT" in proc.stdout


# ---- connect / disconnect lifecycle ----------------------------------------

def test_connect_disconnect_lifecycle(artifact):
    out = run_snippet(artifact, "snippet_chat_flow.js")
    st = out["statuses"]
    assert st["connectAlive"] == 200
    assert st["connectBob"] == 200
    assert st["connectCarol"] == 200
    assert st["connectDave"] == 200
    assert st["duplicateAlice"] == 409
    assert out["clientsBefore"] == "alice,bob,carol,dave"
    assert st["disconnectBob"] == 200
    assert st["disconnectGhost"] == 404
    assert out["clientsAfter"] == "alice,carol,dave"


def test_shutdown_is_clean_and_denies_further_requests(artifact):
    out = run_snippet(artifact, "snippet_chat_flow.js")
    assert out["statuses"]["shutdown"] == 200
    assert out["statuses"]["afterShutdown"] == 503


# ---- protocol parsing -------------------------------------------------------

def test_parse_message_into_structured_record(artifact):
    out = run_snippet(artifact, "snippet_parse.js")
    assert out["parsedSender"] == "nina"
    assert out["parsedChannel"] == "general"
    assert out["parsedPayload"] == "hi"
    assert out["parsedTimestamp"] == 1723900000000


def test_server_stamps_timestamp_at_broadcast(artifact):
    out = run_snippet(artifact, "snippet_parse.js")
    assert out["sendStatus"] == 200
    assert out["logCount"] == 1
    assert out["storedSender"] == "nina"
    assert out["storedPayload"] == "hello from nina"
    assert out["storedChannel"] == "general"
    assert out["storedTimestampType"] == "number"
    assert out["storedTimestampPositive"] is True


# ---- broadcasting -----------------------------------------------------------

def test_broadcast_is_channel_scoped(artifact):
    out = run_snippet(artifact, "snippet_chat_flow.js")
    assert out["broadcastOk"] is True
    assert out["broadcastSender"] == "alice"
    assert out["broadcastChannel"] == "general"
    assert out["broadcastPayload"] == "hello team"
    # alice (sender) and dave (off-topic channel) excluded; bob+carol receive.
    assert out["broadcastRecipients"] == "bob,carol"
    assert out["generalLogCount"] == 2
    assert out["generalLogSender"] == "alice"
    assert out["generalLogPayload"] == "hello team"
    assert out["offtopicLogCount"] == 0


# ---- validation -------------------------------------------------------------

def test_protocol_validation_status_codes(artifact):
    out = run_snippet(artifact, "snippet_validation.js")
    assert out["connectEmpty"] == 400
    assert out["connectNoChannel"] == 400
    assert out["connectOk"] == 200
    assert out["duplicate"] == 409
    assert out["sendNoSender"] == 400
    assert out["sendUnknownSender"] == 404
    assert out["readNoChannel"] == 400
    assert out["unknownPath"] == 404
    assert out["badMethod"] == 405
    assert out["disconnectOk"] == 200
    assert out["disconnectGhost"] == 404


# ---- concurrency (simulated concurrent arrivals) ----------------------------

def test_concurrent_burst_keeps_registry_consistent(artifact):
    out = run_snippet(artifact, "snippet_concurrency.js")
    assert out["joinCount"] == 10
    assert all(s == 200 for s in out["statuses"][:10])
    assert out["duplicateInBurst"] == 409
    assert out["logCount"] == 9
    assert out["lastSender"] == "u10"
    assert out["registryStable"] is True
    assert out["registryTail"] == "u09,u10"


def test_malformed_json_panics_uncatchably(artifact):
    # OmniScript has no try/catch, so a non-empty malformed JSON body
    # propagates as an un-catchable runtime panic (documented limitation).
    snippet = write_source(TESTS_DIR / "_panic_snippet.js", (
        "globalThis.__RESULT__ = (async () => {\n"
        "  const srv = await start_server();\n"
        "  return await send_request(srv, \"POST\", \"/connect\", \"{not-json\");\n"
        "})();\n"
    ))
    proc = subprocess.run(
        [NODE, str(DRIVER), str(artifact), str(snippet)],
        cwd=RUN_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert proc.returncode == 2
    assert "HARNESS_ERROR" in proc.stderr
    snippet.unlink(missing_ok=True)