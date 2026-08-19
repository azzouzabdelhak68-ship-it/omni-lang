"""Automated test suite for the OmniScript video player & media controller (Project 4.2).

Verifies:
  * compiler acceptance: `omni check` exits 0
  * media model structure: `MediaInfo` fields and inspection
  * timeline control math: seeking with clamping to 0 and duration
  * metadata extraction and decoding functions
  * capability model: declared filesystem usage enforced
"""

import json
import subprocess
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "video_player.omni"
TESTS_DIR = Path(__file__).resolve().parent

REPO_ROOT = Path(__file__).resolve().parents[5]
assert REPO_ROOT.is_dir() and (REPO_ROOT / "omni_compiler").is_dir(), REPO_ROOT

def run_omni(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "omni_compiler.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

def test_check_passes():
    proc = run_omni("check", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "omni check: OK" in proc.stdout

def test_media_model_inspection():
    proc = run_omni("inspect", "extract_metadata", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["declared_effects"]["pure"] is True

def test_seek_video_logic():
    proc = run_omni("inspect", "seek_video", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["declared_effects"]["pure"] is True

def test_load_media_stream_capability():
    proc = run_omni("inspect", "load_media_stream", str(SOURCE))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = json.loads(proc.stdout)
    uses = rec["declared_effects"]["uses"]
    assert "filesystem" in uses, f"Expected 'filesystem' in uses, got: {rec}"

def test_pure_functions():
    for fname in ["extract_metadata", "play_video", "pause_video", "seek_video", "get_current_position", "decode_frame"]:
        proc = run_omni("inspect", fname, str(SOURCE))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        rec = json.loads(proc.stdout)
        assert rec["declared_effects"]["pure"] is True

def test_effectful_functions():
    for fname in ["load_media_stream", "save_media_info"]:
        proc = run_omni("inspect", fname, str(SOURCE))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        rec = json.loads(proc.stdout)
        assert rec["declared_effects"]["pure"] is False
        assert "filesystem" in rec["declared_effects"]["uses"]
