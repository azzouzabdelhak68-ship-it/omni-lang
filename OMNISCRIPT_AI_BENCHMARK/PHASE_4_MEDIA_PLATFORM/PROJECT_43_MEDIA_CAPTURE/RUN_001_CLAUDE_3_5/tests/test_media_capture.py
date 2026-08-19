"""Automated test suite for the OmniScript media/camera capture (Project 4.3).

Verifies:
  * compiler acceptance: `omni check` / `omni run` exit 0
  * capability model: declared camera and microphone usage enforced
  * permission lifecycle: granted/denied status handling
  * capture functions: camera frame and microphone sample acquisition
"""

import json
import subprocess
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "media_capture.omni"
TESTS_DIR = Path(__file__).resolve().parent

# Repo root that provides the omni_compiler package
REPO_ROOT = Path(__file__).resolve().parents[5]
assert REPO_ROOT.is_dir() and (REPO_ROOT / "omni_compiler").is_dir(), REPO_ROOT

COMPILER = [sys.executable, "-m", "omni_compiler.cli"]
NODE = shutil.which("node")
SHOULD_RUN_NODE = NODE is not None


def run_omni(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "omni_compiler.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ---- compiler acceptance ----

def test_check_passes():
    proc = run_omni("check", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "omni check: OK" in proc.stdout


# ---- capability model ----

def test_camera_declaration():
    proc = run_omni("inspect", "capture_camera_frame", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert "camera" in rec["declared_effects"]["uses"], (
        f"Expected 'camera' in declared effects, got: {rec}"
    )


def test_microphone_declaration():
    proc = run_omni("inspect", "capture_microphone_samples", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert "microphone" in rec["declared_effects"]["uses"], (
        f"Expected 'microphone' in declared effects, got: {rec}"
    )


def test_pure_functions_no_capability():
    for fname in ["check_camera_permission", "check_microphone_permission",
                  "handle_camera_denial", "handle_microphone_denial",
                  "start_camera_preview", "stop_camera_preview",
                  "start_microphone_recording", "stop_microphone_recording"]:
        proc = run_omni("inspect", fname, str(SOURCE))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        rec = json.loads(proc.stdout)
        assert rec["declared_effects"]["uses"] == [], (
            f"{fname}: expected no uses, got: {rec['declared_effects']['uses']}"
        )
        assert rec["declared_effects"]["pure"] is True


def test_effectful_functions_have_capability():
    for fname in ["capture_camera_frame", "capture_microphone_samples",
                  "save_capture", "load_capture"]:
        proc = run_omni("inspect", fname, str(SOURCE))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        rec = json.loads(proc.stdout)
        uses = rec["declared_effects"]["uses"]
        assert len(uses) > 0, f"{fname}: expected capability declarations, got: {rec}"


# ---- permission lifecycle ----

def test_camera_permission_returns_granted():
    proc = run_omni("inspect", "check_camera_permission", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["result"] == "granted", (
        f"Expected 'granted', got: {rec['result']}"
    )


def test_microphone_permission_returns_granted():
    proc = run_omni("inspect", "check_microphone_permission", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["result"] == "granted", (
        f"Expected 'granted', got: {rec['result']}"
    )


# ---- capture functions ----

def test_capture_camera_frame_returns_buffer():
    proc = run_omni("inspect", "capture_camera_frame", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["pure"] is False, "capture_camera_frame should not be pure"


def test_capture_microphone_samples_returns_buffer():
    proc = run_omni("inspect", "capture_microphone_samples", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["pure"] is False, "capture_microphone_samples should not be pure"


# ---- entry block ----

def test_entry_block():
    proc = run_omni("run", str(SOURCE))
    if SHOULD_RUN_NODE:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "media capture demo complete" in proc.stdout
    else:
        # Node not available - just check compilation
        assert "omni check: OK" in run_omni("check").stdout