import json
import subprocess

import pytest


def test_cli_check_valid():
    """Test omni check on valid file."""
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "check", "tests/fixtures/valid/01_basic.omni"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0, f"Expected success, got: {result.stderr}"

def test_cli_check_invalid():
    """Test omni check on invalid file."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "omni_compiler.cli",
            "check",
            "tests/fixtures/invalid/01_missing_network_declaration.omni",
        ],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode != 0, "Expected failure for invalid file"

    # Should output omni.diagnostic JSON
    try:
        diagnostic = json.loads(result.stdout)
        assert diagnostic["schema"] == "omni.diagnostic"
        assert diagnostic["version"] == "1.0"
        assert "code" in diagnostic
        assert "fixes" in diagnostic
    except json.JSONDecodeError:
        pytest.fail("CLI output is not valid JSON")

def test_cli_run_valid():
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "run", "tests/fixtures/valid/01_basic.omni"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0

def test_cli_inspect_symbol():
    result = subprocess.run(
        [
            "python",
            "-m",
            "omni_compiler.cli",
            "inspect",
            "fetch",
            "tests/fixtures/valid/02_function_with_effects.omni",
        ],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0

    try:
        symbol = json.loads(result.stdout)
        assert symbol["schema"] == "omni.symbol"
        assert symbol["name"] == "fetch"
        assert symbol["kind"] == "function"
        assert "declared_effects" in symbol
    except json.JSONDecodeError:
        pytest.fail("CLI inspect output is not valid JSON")

def test_cli_explain_error():
    result = subprocess.run(
        [
            "python",
            "-m",
            "omni_compiler.cli",
            "explain",
            "tests/fixtures/invalid/01_missing_network_declaration.omni",
        ],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode != 0  # Should fail

    try:
        diagnostic = json.loads(result.stdout)
        assert diagnostic["schema"] == "omni.diagnostic"
        assert "hint" in diagnostic
        assert "fixes" in diagnostic
    except json.JSONDecodeError:
        pytest.fail("CLI explain output is not valid JSON")

def test_cli_help():
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "--help"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "check" in result.stdout.lower()

def test_cli_version():
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "--version"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout or "version" in result.stdout.lower()

def test_cli_invalid_file():
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "check", "nonexistent.omni"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode != 0

def _write_app(tmp_path):
    src = tmp_path / "app.omni"
    src.write_text("when app starts:\n    x = 1\nend\n", encoding="utf-8")
    return src

def test_cli_build_js(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "build", str(src), "--target", "js"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    assert (tmp_path / "app.html").exists()

def test_cli_build_wasm_browser(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        [
            "python",
            "-m",
            "omni_compiler.cli",
            "build",
            str(src),
            "--target",
            "wasm-browser",
        ],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    out = (tmp_path / "app.html").read_text(encoding="utf-8")
    assert "--target=wasm32" in out

def test_cli_build_wasm_wasi(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        [
            "python",
            "-m",
            "omni_compiler.cli",
            "build",
            str(src),
            "--target",
            "wasm-wasi",
        ],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    out = (tmp_path / "app.c").read_text(encoding="utf-8")
    assert "--target=wasm32-wasi" in out

def test_cli_build_c(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "build", str(src), "--target", "c"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode == 0
    assert (tmp_path / "app.c").exists()

def test_cli_build_invalid_target(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "build", str(src), "--target", "nope"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    assert result.returncode != 0

def test_cli_build_rust_guarded(tmp_path):
    src = _write_app(tmp_path)
    result = subprocess.run(
        ["python", "-m", "omni_compiler.cli", "build", str(src), "--target", "rust"],
        capture_output=True, text=True, cwd=".", check=False,
    )
    if result.returncode == 0:
        pytest.skip("rust_emitter.py has landed; rust target is available")
    assert result.returncode != 0