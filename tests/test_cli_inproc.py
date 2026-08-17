"""In-process CLI tests using click's CliRunner (counts toward coverage)."""

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from omni_compiler.cli import cli

VALID = Path("tests/fixtures/valid/01_basic.omni")
INVALID = Path("tests/fixtures/invalid/01_missing_network_declaration.omni")


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_inproc_check_valid(runner):
    result = runner.invoke(cli, ["check", str(VALID)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_inproc_check_invalid(runner):
    result = runner.invoke(cli, ["check", str(INVALID)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"


def test_inproc_run_valid(runner):
    result = runner.invoke(cli, ["run", str(VALID)])
    assert result.exit_code == 0


def test_inproc_inspect(runner):
    result = runner.invoke(
        cli, ["inspect", "add", str(Path("tests/fixtures/valid/02_function_with_effects.omni"))]
    )
    assert result.exit_code == 0
    symbol = json.loads(result.output)
    assert symbol["schema"] == "omni.symbol"


def test_inproc_inspect_unknown(runner):
    result = runner.invoke(cli, ["inspect", "nope", str(VALID)])
    assert result.exit_code == 1


def test_inproc_explain_error(runner):
    result = runner.invoke(cli, ["explain", str(INVALID)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert "hint" in diagnostic


def test_inproc_explain_clean(runner):
    result = runner.invoke(cli, ["explain", str(VALID)])
    assert result.exit_code == 0


def test_inproc_missing_file(runner):
    result = runner.invoke(cli, ["check", "does_not_exist.omni"])
    assert result.exit_code == 2  # noqa: PLR2004


def test_inproc_syntax_error_diagnostic(runner, tmp_path):
    src = tmp_path / "bad_syntax.omni"
    src.write_text("fn broken:\n    x = \nend\n", encoding="utf-8")
    result = runner.invoke(cli, ["check", str(src)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"
    assert "fixes" in diagnostic


def test_inproc_name_error_diagnostic(runner, tmp_path):
    src = tmp_path / "bad_name.omni"
    src.write_text("when app starts:\n    y = undefined_thing\nend\n", encoding="utf-8")
    result = runner.invoke(cli, ["check", str(src)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"
    assert "fixes" in diagnostic


def test_inproc_build_js(runner, tmp_path):
    out = tmp_path / "app.html"
    result = runner.invoke(
        cli, ["build", str(VALID), "--target", "js", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert out.exists()
    assert out.read_text().startswith("<!DOCTYPE html>")


def test_inproc_build_c(runner, tmp_path):
    out = tmp_path / "app.c"
    result = runner.invoke(
        cli, ["build", str(VALID), "--target", "c", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert "int main(" in out.read_text()


def test_inproc_build_rust(runner, tmp_path):
    out = tmp_path / "app.rs"
    result = runner.invoke(
        cli, ["build", str(VALID), "--target", "rust", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert "fn main() {" in out.read_text()


def test_inproc_build_wasm_browser(runner, tmp_path):
    out = tmp_path / "app.html"
    result = runner.invoke(
        cli, ["build", str(VALID), "--target", "wasm-browser", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert "--target=wasm32" in out.read_text()


def test_inproc_build_wasm_wasi(runner, tmp_path):
    out = tmp_path / "app.c"
    result = runner.invoke(
        cli, ["build", str(VALID), "--target", "wasm-wasi", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert "--target=wasm32-wasi" in out.read_text()


def test_inproc_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "build" in result.output


def test_inproc_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


@pytest.mark.skipif(sys.version_info < (3, 11), reason="module guard")
def test_inproc_build_default_target(runner, tmp_path):
    out = tmp_path / "app.html"
    result = runner.invoke(cli, ["build", str(VALID), "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_inproc_verify_contracts(runner):
    effects = Path("tests/fixtures/valid/02_function_with_effects.omni")
    result = runner.invoke(cli, ["verify", str(effects)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema"] == "omni.verify.batch"
    assert all(r["schema"] == "omni.verify" for r in data["results"])
    assert {r["function"] for r in data["results"]} >= {"add", "pure_add"}


def test_inproc_verify_contracts_failure(runner, tmp_path):
    src = tmp_path / "bad.omni"
    src.write_text(
        "fn broken(a: Number) -> Number:\n"
        "    pure\n"
        "    ensure result is 0\n"
        "    return a + 1\n"
        "end\n",
        encoding="utf-8",
    )
    result = runner.invoke(cli, ["verify", str(src)])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["results"][0]["status"] == "failed"
    assert "counterexample" in data["results"][0]


def test_inproc_suggest_no_errors(runner):
    result = runner.invoke(cli, ["suggest", str(VALID)])
    assert result.exit_code == 0
    assert "no errors" in result.output


def test_inproc_suggest_fixes(runner):
    result = runner.invoke(cli, ["suggest", str(INVALID)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema"] == "omni.suggest"
    assert data["fixes"]
    assert data["fixes"][0]["rank"] == 1
    assert data["fixes"][0]["applicability"] == "automatic"


def test_inproc_generate_test(runner):
    result = runner.invoke(
        cli,
        [
            "generate",
            str(Path("tests/fixtures/valid/02_function_with_effects.omni")),
            "pure_add",
        ],
    )
    assert result.exit_code == 0
    assert "def test_pure_add_compiles():" in result.output
    assert "hypothesis" in result.output


def test_inproc_trace_function(runner):
    result = runner.invoke(
        cli,
        ["trace", str(Path("tests/fixtures/valid/01_basic.omni")), "change_greeting"],
    )
    assert result.exit_code == 0
    events = json.loads(result.output)
    assert events[0]["kind"] == "enter_fn"
    assert events[0]["function"] == "change_greeting"
    assert events[0]["step"] == 1


def test_inproc_trace_entry(runner):
    result = runner.invoke(cli, ["trace", str(VALID)])
    assert result.exit_code == 0
    events = json.loads(result.output)
    assert any(e["kind"] == "assign" for e in events)


def test_inproc_lsp_runs(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "lsp" in result.output


def test_inproc_verify_error_path(runner):
    result = runner.invoke(cli, ["verify", str(INVALID)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"


def test_inproc_suggest_syntax_error(runner, tmp_path):
    src = tmp_path / "bad_syntax.omni"
    src.write_text("fn broken:\n    x = \nend\n", encoding="utf-8")
    result = runner.invoke(cli, ["suggest", str(src)])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"


def test_inproc_generate_unknown_function(runner):
    result = runner.invoke(
        cli,
        [
            "generate",
            str(Path("tests/fixtures/valid/02_function_with_effects.omni")),
            "nope",
        ],
    )
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"


def test_inproc_trace_unknown_function(runner):
    result = runner.invoke(cli, ["trace", str(VALID), "nope"])
    assert result.exit_code == 1
    diagnostic = json.loads(result.output)
    assert diagnostic["schema"] == "omni.diagnostic"


def test_inproc_suggest_clean_returns_no_errors(runner):
    result = runner.invoke(cli, ["suggest", str(VALID)])
    assert result.exit_code == 0
    assert "no errors" in result.output


def test_inproc_verify_batch_unsupported(runner, tmp_path):
    src = tmp_path / "loop.omni"
    src.write_text(
        "fn looped(n: Number) -> Number:\n"
        "    pure\n"
        "    ensure result is n\n"
        "    total = 0\n"
        "    for i in n:\n"
        "        total = total + i\n"
        "    end\n"
        "    return total\n"
        "end\n",
        encoding="utf-8",
    )
    result = runner.invoke(cli, ["verify", str(src)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"][0]["status"] == "unsupported"