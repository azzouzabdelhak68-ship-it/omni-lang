"""Benchmark 3.3 — GPU Image Processing Pipeline test suite.

Drives the OmniScript compiler (check/build) and the Node JS lane, then
compares the emitted stdout against a CPU reference of the same convolution
math implemented in Python.

Reproduces the OmniScript program's flattened image layout:
    input = [width=4, p0..p15]   (row-major 4x4, pixel values 10..160)

Run from the repo root:  python -m pytest <this file>  (or pytest -q)
Node v24 is required on PATH.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "gpu_filter.omni"

# --- repo root resolution (where the omni_compiler package lives) ---------
def _find_repo_root(start: Path) -> Path:
    cur = start
    while True:
        if (cur / "omni_compiler").is_dir():
            return cur
        if cur.parent == cur:
            raise RuntimeError("could not locate repo root (omni_compiler package)")
        cur = cur.parent


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --- CPU reference implementation (same math as the kernels) --------------
W = 4
N = 16
PIXELS = [10 * (i + 1) for i in range(N)]


def _neighbors(i, pixels=PIXELS):
    w, n = W, N
    center = pixels[i]
    up = pixels[i - w] if i >= w else center
    down = pixels[i + w] if i + w <= n - 1 else center
    col = i - (i // w) * w
    left = pixels[i - 1] if col > 0 else center
    right = pixels[i + 1] if col < w - 1 else center
    return center, left, right, up, down


def blur_ref(pixels=PIXELS):
    return [(c + l + r + u + d) / 5 for (c, l, r, u, d) in (_neighbors(i, pixels) for i in range(N))]


def sharpen_ref(pixels=PIXELS):
    return [c * 5 - (l + r + u + d) for (c, l, r, u, d) in (_neighbors(i, pixels) for i in range(N))]


def edge_ref(pixels=PIXELS):
    return [abs(u - d) + abs(l - r) for (c, l, r, u, d) in (_neighbors(i, pixels) for i in range(N))]


# --- compiler / node harness helpers --------------------------------------
def run_omni(args):
    return subprocess.run(
        [sys.executable, "-m", "omni_compiler.cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def build_js(tmp_path):
    out = tmp_path / "gpu_filter.html"
    r = run_omni(["build", str(SOURCE), "--target", "js", "-o", str(out)])
    assert r.returncode == 0, f"build failed:\n{r.stdout}\n{r.stderr}"
    assert out.exists(), "build artifact not created"
    return out


_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)

_DOC_STUB = (
    'const document = { getElementById: (id) => ({ innerHTML: "" }), '
    "querySelectorAll: () => [] };\n"
    "globalThis.document = document;\n"
)


def run_node(tmp_path):
    """Build the JS artifact, extract the script body, stub the DOM, run node."""
    html = build_js(tmp_path)
    m = _SCRIPT_RE.search(html.read_text(encoding="utf-8"))
    assert m, "no <script> body found in build artifact"
    app_js = tmp_path / "app.js"
    app_js.write_text(_DOC_STUB + "\n" + m.group(1), encoding="utf-8")
    r = subprocess.run(["node", str(app_js)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.splitlines()


# --- tests -----------------------------------------------------------------
def test_check_exits_zero():
    """omni check accepts the program even though GPU effects are declared."""
    r = run_omni(["check", str(SOURCE)])
    assert r.returncode == 0, f"check failed:\n{r.stdout}\n{r.stderr}"
    assert "OK" in r.stdout


def test_build_creates_html_artifact(tmp_path):
    """omni build --target js writes a real HTML artifact."""
    out = build_js(tmp_path)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")
    assert "<script>" in text


def test_blur_matches_cpu_reference(tmp_path):
    lines = run_node(tmp_path)
    got = [float(v) for v in lines[1].split(",")]
    assert got == pytest.approx(blur_ref(), rel=1e-9)


def test_sharpen_matches_cpu_reference(tmp_path):
    lines = run_node(tmp_path)
    got = [float(v) for v in lines[2].split(",")]
    assert got == pytest.approx(sharpen_ref(), rel=1e-9)


def test_edge_matches_cpu_reference(tmp_path):
    lines = run_node(tmp_path)
    got = [float(v) for v in lines[3].split(",")]
    assert got == pytest.approx(edge_ref(), rel=1e-9)


def test_filter_outputs_are_integer_exact(tmp_path):
    """The chosen dataset yields exact integers, so equality is strict."""
    lines = run_node(tmp_path)
    for idx in (1, 2, 3):
        for tok in lines[idx].split(","):
            assert float(tok) == float(int(float(tok))), f"non-integer result: {tok}"


def test_buffer_lifecycle_roundtrip(tmp_path):
    """buffer allocate + read-back returns the original host pixel list."""
    lines = run_node(tmp_path)
    assert lines[0] == "image 4x4 loaded"
    got = [int(v) for v in lines[4].split(",")]
    assert got == PIXELS


def test_backend_abstraction(tmp_path):
    """device_info reports the portable backend; select_backend maps/swaps."""
    lines = run_node(tmp_path)
    assert lines[5] == "backend=portable-cpu cores=1"
    assert lines[6] == "cuda"
    assert lines[7] == "portable-cpu"  # unknown backend -> portable fallback


def test_run_pipeline_equals_apply_filter(tmp_path):
    """Backend-selected pipeline (mode 1, vulkan) matches apply_filter blur."""
    lines = run_node(tmp_path)
    assert lines[8] == lines[1]


def test_capability_declarations_emitted(tmp_path):
    """Every GPU-touching function carries a capability marker in the JS."""
    html = build_js(tmp_path).read_text(encoding="utf-8")
    for fn in ("apply_filter", "transfer_and_readback", "query_device", "run_pipeline"):
        marker = f"function {fn}("
        assert marker in html, f"function {fn} missing from artifact"
    assert html.count("// capability: GPU") >= 4


def test_pure_kernel_cannot_call_gpu_compute(tmp_path):
    """Capability enforcement: pure + GPU compute must be rejected."""
    bad = tmp_path / "pure_compute.omni"
    bad.write_text(
        "import OMNISYS.gpu\n"
        "import OMNISYS.collections\n"
        "fn bad_kernel(i: Number, input: List) -> Number:\n"
        "    pure\n"
        "    return omnisys.collections.list_get(input, 0)\n"
        "end\n"
        "fn pure_calls_gpu(data: List) -> List:\n"
        "    pure\n"
        "    return omnisys.gpu.compute(bad_kernel, data, 1)\n"
        "end\n"
        "when app starts:\n"
        "    show \"hello\"\n"
        "end\n",
        encoding="utf-8",
    )
    r = run_omni(["check", str(bad)])
    assert r.returncode != 0
    assert "E-EFFECT-001" in r.stdout
    assert "GPU" in r.stdout


def test_buffer_registered_pure(tmp_path):
    """gpu.buffer carries NO GPU capability, so a pure fn may call it (gap)."""
    ok = tmp_path / "pure_buffer.omni"
    ok.write_text(
        "import OMNISYS.gpu\n"
        "import OMNISYS.collections\n"
        "fn make_buffer(data: List) -> List:\n"
        "    pure\n"
        "    buf = omnisys.gpu.buffer(data)\n"
        "    return omnisys.collections.map_get(buf, \"data\")\n"
        "end\n"
        "when app starts:\n"
        "    show \"ok\"\n"
        "end\n",
        encoding="utf-8",
    )
    r = run_omni(["check", str(ok)])
    assert r.returncode == 0, f"unexpected failure:\n{r.stdout}\n{r.stderr}"