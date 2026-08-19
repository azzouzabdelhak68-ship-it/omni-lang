"""pytest suite for Benchmark Task 3.1 — Interactive 2D Vector Drawing Canvas.

Drives the OmniScript compiler (`python -m omni_compiler.cli`) from the repo
root, builds the JS artifact, runs the extracted <script> body under Node with
a document stub, and asserts on the program's stdout. Expected transform and
animation values are recomputed in Python with the same IEEE-754 arithmetic.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "canvas_app.omni"

DOC_STUB = (
    'const document = { getElementById: (id) => ({ innerHTML: "" }), '
    "querySelectorAll: () => [] }; globalThis.document = document;"
)


def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for _ in range(10):
        if (p / "omni_compiler").is_dir():
            return p
        p = p.parent
    raise RuntimeError("repo root not found")


REPO_ROOT = _find_repo_root()


def run_omni(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "omni_compiler.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _parse_output(stdout: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in stdout.strip().splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


@pytest.fixture(scope="module")
def program_stdout(tmp_path_factory) -> str:
    tmp = tmp_path_factory.mktemp("canvas_artifacts")
    artifact = tmp / "canvas_app.html"
    r = run_omni("check", str(SOURCE))
    assert r.returncode == 0, f"check failed:\n{r.stdout}\n{r.stderr}"
    r = run_omni("build", str(SOURCE), "--target", "js", "-o", str(artifact))
    assert r.returncode == 0, f"build failed:\n{r.stdout}\n{r.stderr}"
    assert artifact.exists(), "build artifact was not written"
    html = artifact.read_text(encoding="utf-8")
    match = re.search(r"<script>([\s\S]*?)</script>", html)
    assert match, "no <script> block found in built artifact"
    script = tmp / "app.js"
    script.write_text(DOC_STUB + "\n" + match.group(1), encoding="utf-8")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, f"node failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout


@pytest.fixture(scope="module")
def program_output(program_stdout) -> dict[str, str]:
    return _parse_output(program_stdout)


def _tick_values(out: dict[str, str], key: str) -> tuple[float, float, float]:
    x, y, rot = out[key].split(",")
    return float(x), float(y), float(rot)


# ---- Compiler pipeline ----------------------------------------------------

def test_omni_check_exits_zero():
    r = run_omni("check", str(SOURCE))
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_omni_build_js_produces_artifact(tmp_path):
    artifact = tmp_path / "canvas_app.html"
    r = run_omni("build", str(SOURCE), "--target", "js", "-o", str(artifact))
    assert r.returncode == 0
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_node_harness_produces_done_marker(program_stdout):
    assert "done" in program_stdout, program_stdout


# ---- Shape model creation -------------------------------------------------

def test_shape_count(program_output):
    assert program_output["shape_count"] == "5"


def test_move_shape_updates_position(program_output):
    assert program_output["moved_rect"] == "20,25"


def test_set_shape_color_updates_fill(program_output):
    assert program_output["colored_circle"] == "#0000ff"


# ---- Transform math -------------------------------------------------------

def test_apply_transform(program_output):
    assert program_output["transformed_rect"] == "25,22,0.5,1.5"


# ---- Input handling -------------------------------------------------------

def test_select_shape_valid_index(program_output):
    assert program_output["selected_index"] == "2"


def test_select_shape_invalid_index(program_output):
    assert program_output["invalid_selection"] == "-1"


def test_delete_shape_removes_one(program_output):
    assert program_output["count_after_delete"] == "4"


# ---- Animation stepping ---------------------------------------------------

def test_tick_animation_stepping(program_output):
    x, y, rot = 25.0, 22.0, 0.5
    for key in ("tick1_rect", "tick2_rect", "tick3_rect"):
        x = x + 2 * 0.1
        y = y + 1 * 0.1
        rot = rot + 0.5 * 0.1
        got = _tick_values(program_output, key)
        assert got == pytest.approx((x, y, rot), abs=1e-12)


def test_animated_rect_moves_forward(program_output):
    x1, _, _ = _tick_values(program_output, "tick1_rect")
    x3, y3, r3 = _tick_values(program_output, "tick3_rect")
    assert x3 > x1
    assert y3 > 22.0
    assert r3 > 0.5


# ---- Canvas rendering -----------------------------------------------------

def test_rendered_op_count(program_output):
    assert program_output["rendered_ops"] == "5"


def test_canvas_dimensions_from_json(program_output):
    assert program_output["canvas_width"] == "800"
    assert program_output["canvas_height"] == "600"