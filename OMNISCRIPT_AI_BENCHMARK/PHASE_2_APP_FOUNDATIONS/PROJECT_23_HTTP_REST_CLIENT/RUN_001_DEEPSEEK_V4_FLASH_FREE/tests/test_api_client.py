"""Automated test suite for the OmniScript REST API client (Project 2.3).

Verifies (all inside the dedicated run directory):
  * compiler acceptance: `omni check` / `omni run` exit 0
  * capability model: declared network usage enforced (negative probes)
  * request construction, response parsing and error classification against
    the *compiled JS artifact* driven in Node with stubbed responses
  * the OMNISYS.http inproc:// transport (registered stub servers) end-to-end
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "api_client.omni"
TESTS_DIR = Path(__file__).resolve().parent
SNIPPETS = TESTS_DIR / "snippets"
DRIVER = TESTS_DIR / "node_driver.js"
BUILD = RUN_DIR / "build"
ARTIFACT = BUILD / "api_client.html"

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


def test_run_passes():
    proc = run([*COMPILER, "run", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() != ""  # program executes; scenario emits output


# ---- capability model ------------------------------------------------------

def test_network_capability_declared_on_network_functions():
    proc = run([*COMPILER, "inspect", "fetch_users", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert "network" in rec["declared_effects"]["uses"]


def test_pure_functions_carry_no_capability():
    proc = run([*COMPILER, "inspect", "classify_error", str(SOURCE)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["declared_effects"]["uses"] == []


def test_missing_network_declaration_rejected():
    bad = write_source(BUILD / "bad_missing_effect.omni", (
        "import OMNISYS.http\n"
        "\n"
        "fn fetch() -> Number:\n"
        "    resp = omnisys.http.get(\"inproc://test/x\")\n"
        "    return 0\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-EFFECT-003" in proc.stdout
    assert "network" in proc.stdout


def test_app_block_cannot_call_network_directly():
    bad = write_source(BUILD / "bad_app_direct.omni", (
        "import OMNISYS.http\n"
        "\n"
        "when app starts:\n"
        "    resp = omnisys.http.get(\"inproc://test/x\")\n"
        "    show resp\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-EFFECT-003" in proc.stdout
    assert "app starts" in proc.stdout


def test_unknown_http_function_rejected():
    # http.register exists in the JS runtime but is NOT in the registry's
    # function table, so it must not be callable from OmniScript source.
    bad = write_source(BUILD / "bad_register_call.omni", (
        "import OMNISYS.http\n"
        "\n"
        "fn setup() -> Number:\n"
        "    uses network\n"
        "    omnisys.http.register(\"api\", 1)\n"
        "    return 0\n"
        "end\n"
    ))
    proc = run([*COMPILER, "check", str(bad)])
    assert proc.returncode != 0
    assert "E-NAME" in proc.stdout or "E-IMPORT" in proc.stdout


# ---- request construction ---------------------------------------------------

def test_get_request_construction(artifact):
    out = run_snippet(artifact, "snippet_request_get.js")
    assert out["method"] == "GET"
    assert out["url"] == "https://api.example.com?page=1&size=10"
    assert out["headers"] == "Accept: application/json"
    assert out["body"] == ""


def test_post_request_with_json_body(artifact):
    out = run_snippet(artifact, "snippet_request_post.js")
    assert out["method"] == "POST"
    assert out["url"] == "https://api.example.com/users"
    assert out["headers"] == "Content-Type: application/json"
    assert out["bodyIsJson"] is True


def test_query_string_encoding(artifact):
    out = run_snippet(artifact, "snippet_encode_query.js")
    assert out["query"] == "page=1&size=10&active=true"


# ---- response parsing --------------------------------------------------------

def test_parse_single_user_payload(artifact):
    out = run_snippet(artifact, "snippet_parse_user.js")
    assert out["id"] == 7
    assert out["name"] == "Grace"
    assert out["email"] == "grace@x.com"


def test_parse_user_list_payload(artifact):
    out = run_snippet(artifact, "snippet_parse_users.js")
    assert out["count"] == 2
    assert out["firstId"] == 1
    assert out["firstName"] == "A"
    assert out["secondEmail"] == "b@x.com"


# ---- error & timeout classification ------------------------------------------

def test_error_classification_stubbed(artifact):
    out = run_snippet(artifact, "snippet_classify.js")
    assert out["ok"] == "ok"
    assert out["created"] == "ok"
    assert out["notFound"] == "not_found"
    assert out["serverErr"] == "server_error"
    assert out["httpErr"] == "http_error"
    assert out["connFail"] == "connection_failed"
    assert out["malformed"] == "malformed_payload"
    assert out["timedOut"] == "timeout"


# ---- end-to-end network paths (inproc:// stub servers) -----------------------

def test_network_get_stub(artifact):
    out = run_snippet(artifact, "snippet_network_ok.js")
    assert out["code"] == "ok"
    assert out["parsed"] == "Grace"


def test_network_404_stub(artifact):
    out = run_snippet(artifact, "snippet_network_404.js")
    assert out["code"] == "not_found"


def test_network_post_stub(artifact):
    out = run_snippet(artifact, "snippet_network_post.js")
    assert out["code"] == "ok"
    assert out["capturedMethod"] == "POST"
    assert out["capturedPath"] == "/users"
    assert out["bodyIsJson"] is True


def test_network_timeout_enforced(artifact):
    out = run_snippet(artifact, "snippet_network_timeout.js")
    assert out["slowCode"] == "timeout"
    assert out["fastCode"] == "ok"


def test_unregistered_transport_panics(artifact):
    # A network call to an unregistered host has no transport: the runtime
    # panics. This is the observable "connection failure" mode of the
    # OMNISYS.http portable transport (there is no status-0 error channel).
    snippet = write_source(TESTS_DIR / "_panic_snippet.js", (
        "globalThis.__RESULT__ = (async () => {\n"
        "  return await fetch_users(\"https://unknown.example\", 1000);\n"
        "})();\n"
    ))
    proc = subprocess.run(
        [NODE, str(DRIVER), str(artifact), str(snippet)],
        cwd=RUN_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert proc.returncode == 2
    assert "no transport" in proc.stderr
    snippet.unlink(missing_ok=True)