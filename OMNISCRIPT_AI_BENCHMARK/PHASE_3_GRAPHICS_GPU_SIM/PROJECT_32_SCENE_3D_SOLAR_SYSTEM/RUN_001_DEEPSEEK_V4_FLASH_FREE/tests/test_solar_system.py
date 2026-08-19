"""pytest suite for Benchmark Task 3.2 — Interactive 3D Solar System.

Drives the OmniScript compiler (`python -m omni_compiler.cli`) from the repo
root, builds the JS artifact, runs the extracted <script> body under Node with
a browser-stub (including the scene block's document.createElement calls), and
asserts orbital / hierarchical-motion math against a Python reference that
mirrors the program's Taylor-series cos/sin approximations exactly.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "solar_system.omni"

DOC_STUB = (
    'const document = { getElementById: (id) => ({ innerHTML: "" }), '
    "querySelectorAll: () => [], createElement: (tag) => ({}), "
    "head: { appendChild: () => {} }, body: { appendChild: () => {} } }; "
    "globalThis.document = document;"
)

TWO_PI = 6.283185307179586


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


# ---- Python reference mirrors of the program's pure motion math ------------

def sin_t(x: float) -> float:
    x2 = x * x
    x3 = x2 * x
    x5 = x3 * x2
    x7 = x5 * x2
    x9 = x7 * x2
    x11 = x9 * x2
    return x - x3 / 6.0 + x5 / 120.0 - x7 / 5040.0 + x9 / 362880.0 - x11 / 39916800.0


def cos_t(x: float) -> float:
    x2 = x * x
    x4 = x2 * x2
    x6 = x4 * x2
    x8 = x4 * x4
    x10 = x6 * x4
    x12 = x6 * x6
    return 1.0 - x2 / 2.0 + x4 / 24.0 - x6 / 720.0 + x8 / 40320.0 - x10 / 3628800.0 + x12 / 479001600.0


def advance_angle(angle: float, speed: float, dt: float) -> float:
    nxt = angle + speed * dt
    if nxt >= TWO_PI:
        nxt -= TWO_PI
    if nxt < 0:
        nxt += TWO_PI
    return nxt


def run_series(initial: float, speed: float, dt: float, ticks: int) -> float:
    a = initial
    for _ in range(ticks):
        a = advance_angle(a, speed, dt)
    return a


def orbital_position(radius: float, angle: float) -> tuple[float, float]:
    return radius * cos_t(angle), radius * sin_t(angle)


# ---- Harness ---------------------------------------------------------------

def _run_program(tmp_path_factory) -> list[str]:
    tmp = tmp_path_factory.mktemp("solar_artifacts")
    artifact = tmp / "solar_system.html"
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
    return r.stdout.strip().splitlines()


@pytest.fixture(scope="module")
def stdout_lines(tmp_path_factory) -> list[str]:
    return _run_program(tmp_path_factory)


def _body_position(stdout: list[str], tick: int, body: str) -> tuple[float, float]:
    prefix = f"tick={tick} {body}="
    for line in stdout:
        if line.startswith(prefix):
            x, z = line[len(prefix):].split(",")
            return float(x), float(z)
    raise AssertionError(f"no {prefix}... line in program output")


# ---- Compiler pipeline ----------------------------------------------------

def test_omni_check_exits_zero():
    r = run_omni("check", str(SOURCE))
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_omni_build_js_produces_artifact(tmp_path):
    artifact = tmp_path / "solar_system.html"
    r = run_omni("build", str(SOURCE), "--target", "js", "-o", str(artifact))
    assert r.returncode == 0
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_node_harness_runs_to_completion(stdout_lines):
    assert any("highlight pluto idx=-1" in line for line in stdout_lines)


# ---- Scene composition ----------------------------------------------------

def test_scene_bodies_listed(stdout_lines):
    assert any(
        "scene bodies=sun,mercury,venus,earth,moon,mars" in line for line in stdout_lines
    )


def test_scene_body_counts(stdout_lines):
    assert any("count bodies=6 planets=4 moon=1" in line for line in stdout_lines)


def test_body_colors_assigned(stdout_lines):
    assert any(
        "colors sun=#fbbf24 mercury=#9ca3af venus=#eab308 earth=#3b82f6 "
        "moon=#e2e8f0 mars=#ef4444" in line
        for line in stdout_lines
    )


# ---- Orbital motion math (Python reference) -------------------------------

@pytest.mark.parametrize(
    "body,radius,speed,initial",
    [
        ("mercury", 1.5, 1.2, 0.0),
        ("venus", 2.2, 0.9, 0.3),
        ("earth", 3.0, 0.6, 0.6),
        ("mars", 3.9, 0.4, 0.9),
    ],
)
def test_orbital_positions_match_reference(stdout_lines, body, radius, speed, initial):
    for tick in range(5):
        angle = run_series(initial, speed, 0.25, tick + 1)
        ex, ez = orbital_position(radius, angle)
        gx, gz = _body_position(stdout_lines, tick, body)
        assert gx == pytest.approx(ex, abs=1e-9)
        assert gz == pytest.approx(ez, abs=1e-9)


def test_moon_hierarchical_transform(stdout_lines):
    for tick in range(5):
        earth_angle = run_series(0.6, 0.6, 0.25, tick + 1)
        moon_angle = run_series(0.1, 2.0, 0.25, tick + 1)
        ex, ez = orbital_position(3.0, earth_angle)
        mx_off, mz_off = orbital_position(0.6, moon_angle)
        gx, gz = _body_position(stdout_lines, tick, "moon")
        assert gx == pytest.approx(ex + mx_off, abs=1e-9)
        assert gz == pytest.approx(ez + mz_off, abs=1e-9)


def test_camera_orbit_distance(stdout_lines):
    for tick in range(5):
        x, z = _body_position(stdout_lines, tick, "camera")
        assert x * x + z * z == pytest.approx(100.0, rel=1e-9)


# ---- Interaction & animation ----------------------------------------------

def test_highlight_selects_existing_body(stdout_lines):
    assert any("highlight earth idx=3" in line for line in stdout_lines)


def test_highlight_rejects_missing_body(stdout_lines):
    assert any("highlight pluto idx=-1" in line for line in stdout_lines)


def test_animation_advances_over_ticks(stdout_lines):
    m0x, _ = _body_position(stdout_lines, 0, "mercury")
    m4x, _ = _body_position(stdout_lines, 4, "mercury")
    assert m0x != m4x
    e0x, _ = _body_position(stdout_lines, 0, "earth")
    e4x, _ = _body_position(stdout_lines, 4, "earth")
    assert e0x != e4x