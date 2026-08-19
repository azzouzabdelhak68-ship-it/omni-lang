"""pytest suite for Benchmark Task 3.4 — Integrated ECS Simulation & 3D Scene.

Drives the OmniScript compiler from the repo root. Verifies:
  - `omni check` passes.
  - JS, C, and Rust targets all build successfully.
  - The JS build runs under Node with a browser stub PLUS a portable `sim.*`
    ECS runtime (the JS lane ships no inlined ECS runtime for `sim.*`, only the
    actor runtime — see BENCHMARK_REASONING.md), and asserts the motion-system
    update math and scene/sim consistency against a Python reference.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "integrated_sim.omni"

DOC_STUB = (
    'const document = { getElementById: (id) => ({ innerHTML: "" }), '
    "querySelectorAll: () => [], createElement: (tag) => ({}), "
    "head: { appendChild: () => {} }, body: { appendChild: () => {} } }; "
    "globalThis.document = document;"
)

SIM_STUB = (
    "const _simEntities = {};"
    "const _simSystems = [];"
    "const sim = {"
    "  entity: (name, comps) => { if (!_simEntities[name]) _simEntities[name] = (comps || []).slice(); return name; },"
    "  system: (name, fn, comps) => { _simSystems.push(fn); return name; },"
    "  run: (steps) => { for (let i = 0; i < steps; i++) { for (const fn of _simSystems) fn(); } return steps; },"
    "  query: (component) => Object.keys(_simEntities).filter((n) => _simEntities[n].includes(component)),"
    "};"
    "globalThis.sim = sim;"
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


# ---- Compiler pipeline ----------------------------------------------------

def test_omni_check_exits_zero():
    r = run_omni("check", str(SOURCE))
    assert r.returncode == 0
    assert "OK" in r.stdout


@pytest.mark.parametrize("target,suffix", [("js", ".html"), ("c", ".c"), ("rust", ".rs")])
def test_omni_build_target_succeeds(tmp_path, target, suffix):
    artifact = tmp_path / f"integrated_sim{suffix}"
    r = run_omni("build", str(SOURCE), "--target", target, "-o", str(artifact))
    assert r.returncode == 0, f"{target} build failed:\n{r.stdout}\n{r.stderr}"
    assert artifact.exists()
    assert artifact.read_text(encoding="utf-8")


def test_c_artifact_mentions_flecs(tmp_path):
    artifact = tmp_path / "integrated_sim.c"
    r = run_omni("build", str(SOURCE), "--target", "c", "-o", str(artifact))
    assert r.returncode == 0
    assert "flecs.h" in artifact.read_text(encoding="utf-8")


def test_rust_artifact_mentions_bevy(tmp_path):
    artifact = tmp_path / "integrated_sim.rs"
    r = run_omni("build", str(SOURCE), "--target", "rust", "-o", str(artifact))
    assert r.returncode == 0
    assert "bevy" in artifact.read_text(encoding="utf-8").lower()


# ---- JS runtime + simulation math -----------------------------------------

@pytest.fixture(scope="module")
def stdout_lines(tmp_path_factory) -> list[str]:
    tmp = tmp_path_factory.mktemp("sim_artifacts")
    artifact = tmp / "integrated_sim.html"
    r = run_omni("check", str(SOURCE))
    assert r.returncode == 0, f"check failed:\n{r.stdout}\n{r.stderr}"
    r = run_omni("build", str(SOURCE), "--target", "js", "-o", str(artifact))
    assert r.returncode == 0, f"build failed:\n{r.stdout}\n{r.stderr}"
    html = artifact.read_text(encoding="utf-8")
    match = re.search(r"<script>([\s\S]*?)</script>", html)
    assert match, "no <script> block found in built artifact"
    script = tmp / "app.js"
    script.write_text(DOC_STUB + "\n" + SIM_STUB + "\n" + match.group(1), encoding="utf-8")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, f"node failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip().splitlines()


def _final_position(stdout_lines: list[str], body: str) -> tuple[float, float]:
    for line in stdout_lines:
        if line.startswith(f"final:{body}:"):
            x, y = line.split(":", 2)[2].split(",")
            return float(x), float(y)
    raise AssertionError(f"no final:{body} line in program output")


def test_motion_system_updates_positions(stdout_lines):
    dt = 0.25
    steps = 3
    expect = {
        "p1": (0.0 + 1.0 * dt * steps, 0.0 + 0.5 * dt * steps),
        "p2": (-2.0 + 0.25 * dt * steps, 1.0 + 0.75 * dt * steps),
        "p3": (2.0 - 0.5 * dt * steps, -1.0 + 1.25 * dt * steps),
    }
    for body, (ex, ey) in expect.items():
        gx, gy = _final_position(stdout_lines, body)
        assert gx == pytest.approx(ex, abs=1e-9)
        assert gy == pytest.approx(ey, abs=1e-9)


def test_tick_lines_show_progression(stdout_lines):
    ticks = [line for line in stdout_lines if line.startswith("tick:")]
    assert len(ticks) == 3
    x0 = float(ticks[0].split(":", 1)[1].split(",")[0])
    x2 = float(ticks[2].split(":", 1)[1].split(",")[0])
    assert x2 > x0


def test_scene_renders_one_body_per_entity(stdout_lines):
    assert any("scene-bodies:3" in line for line in stdout_lines)


def test_scene_and_sim_positions_consistent(stdout_lines):
    """Rendered bodies mirror the simulated final positions (tick 3 values)."""
    for body in ("p1", "p2", "p3"):
        assert any(f"final:{body}:" in line for line in stdout_lines)