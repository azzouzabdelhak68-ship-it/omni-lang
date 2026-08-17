"""CLI Tool for OmniScript Compiler.

Commands: check, run, inspect, explain, build, verify, suggest, generate, trace, lsp.
"""

import json
import sys
from pathlib import Path

import click

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse
from omni_compiler.wasm_emitter import emit_wasm, wasm_build_command


def _compile(file: Path):
    code = Path(file).read_text(encoding="utf-8")
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return ast, symbol_table, mir


def _reject_omnisys_on_native_target(target: str, mir) -> None:
    """§8.3 per-back-end capability check: OMNISYS is provided by the JS lane."""
    if not mir.imports:
        return
    click.echo(json.dumps(_diagnostic_from_exception(
        DiagnosticError(
            "E-BACKEND-001", "backend", "error",
            "OMNISYS modules require the JS lane.",
            f"'{target}' does not provide the OMNISYS runtime. The JS lane is the reference OMNISYS back-end (spec §17.10.E/§17.10.R).",
            1, 1, 0, 0,
            {"target": target, "imports": mir.imports},
            [{
                "id": "target-js",
                "kind": "replace_span",
                "applicability": "automatic",
                "description": "Build with --target js, the OMNISYS reference back-end.",
                "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": "--target js"}
            }]
        )
    ), indent=2))
    sys.exit(1)


def _diagnostic_from_exception(e: Exception) -> dict:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            "schema": "omni.diagnostic",
            "version": "1.0",
            "code": "E-SYNTAX-001",
            "category": "syntax",
            "severity": "error",
            "message": "Syntax error.",
            "details": msg,
            "span": {"start": 0, "end": 0},
            "location": {"line": 1, "column": 1},
            "context": {},
            "fixes": [
                {
                    "id": "fix-syntax",
                    "kind": "replace_span",
                    "applicability": "suggested",
                    "description": "Fix the reported syntax issue.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
                }
            ],
        }
    if isinstance(e, NameError):
        return {
            "schema": "omni.diagnostic",
            "version": "1.0",
            "code": "E-NAME-001",
            "category": "name",
            "severity": "error",
            "message": str(e),
            "details": str(e),
            "span": {"start": 0, "end": 0},
            "location": {"line": 1, "column": 1},
            "context": {},
            "fixes": [
                {
                    "id": "define-name",
                    "kind": "suggested",
                    "applicability": "suggested",
                    "description": "Define the missing name or check the spelling.",
                    "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": ""}
                }
            ],
        }
    return {
        "schema": "omni.diagnostic",
        "version": "1.0",
        "code": "E-INTERNAL-001",
        "category": "internal",
        "severity": "error",
        "message": str(e),
        "details": f"{type(e).__name__}: {e}",
        "span": {"start": 0, "end": 0},
        "location": {"line": 1, "column": 1},
        "context": {},
        "fixes": [],
    }


@click.group()
@click.version_option(version="0.1.0", prog_name="omni")
def cli():
    """OmniScript Compiler - AI-first language with declared effects and live links."""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def check(file: Path):
    """Type-check and effect-check an OmniScript file."""
    try:
        _compile(file)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(f"omni check: OK — {file.name}")
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def run(file: Path):
    """Run an OmniScript file."""
    try:
        _, _, mir = _compile(file)
        emit_js(mir)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo("omni run: OK")
    sys.exit(0)


@cli.command()
@click.argument("symbol")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def inspect(symbol: str, file: Path):
    """Inspect a symbol in an OmniScript file."""
    try:
        _, symbol_table, _ = _compile(file)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    rec = symbol_table.inspect_symbol(symbol)
    if rec is None:
        click.echo(json.dumps({
            "schema": "omni.symbol",
            "version": "1.0",
            "name": symbol,
            "kind": "unknown",
            "type": "unknown",
            "declared_effects": {"uses": [], "reads": [], "writes": []},
            "span": {"start": 0, "end": 0},
            "location": {"line": 1, "column": 1},
            "dependencies": [],
            "exported": False,
        }, indent=2))
        sys.exit(1)
    click.echo(json.dumps(rec, indent=2))
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def explain(file: Path):
    """Explain an error in an OmniScript file."""
    try:
        _compile(file)
    except Exception as e:
        d = _diagnostic_from_exception(e)
        d["hint"] = d.get("message", "")
        click.echo(json.dumps(d, indent=2))
        sys.exit(1)
    click.echo("omni explain: no errors found")
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--target",
    default="js",
    show_default=True,
    type=click.Choice(["js", "c", "rust", "wasm-browser", "wasm-wasi"]),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path (defaults to the input stem + target suffix).",
)
def build(file: Path, target: str, output: Path | None):
    """Build an OmniScript file to a target artifact."""
    try:
        _, _, mir = _compile(file)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)

    mode = None
    if target == "js":
        content = emit_js(mir)
        out = output or file.with_suffix(".html")
    elif target == "c":
        _reject_omnisys_on_native_target(target, mir)
        content = emit_c(mir)
        out = output or file.with_suffix(".c")
    elif target == "rust":
        _reject_omnisys_on_native_target(target, mir)
        try:
            from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415 - optional peer module

            content = emit_rust(mir)
        except ImportError:
            click.echo(
                "omni build: rust target unavailable (rust_emitter.py has not landed yet)",
                err=True,
            )
            sys.exit(1)
        out = output or file.with_suffix(".rs")
    elif target in ("wasm-browser", "wasm-wasi"):
        _reject_omnisys_on_native_target(target, mir)
        mode = "browser" if target == "wasm-browser" else "wasi"
        content = emit_wasm(mir, mode=mode)
        default_out = file.with_suffix(".html" if mode == "browser" else ".c")
        out = output or default_out
    else:  # pragma: no cover - click restricts valid targets
        click.echo(f"omni build: unknown target: {target}", err=True)
        sys.exit(1)

    out.write_text(content, encoding="utf-8")
    click.echo(f"omni build: wrote {out} (target={target})")
    if mode is not None:
        click.echo(f"  {wasm_build_command(mode)}", err=True)
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def verify(file: Path):
    """Prove require/ensure contracts statically with an SMT solver."""
    try:
        from omni_compiler.smt import verify_contracts  # noqa: PLC0415

        ast, _, _ = _compile(file)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    results = verify_contracts(ast)
    batch = {"schema": "omni.verify.batch", "version": "1.0", "results": results}
    click.echo(json.dumps(batch, indent=2))
    failed = [r for r in results if r["status"] == "failed"]
    sys.exit(1 if failed else 0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def suggest(file: Path):
    """Propose ranked fixes for errors in an OmniScript file."""
    try:
        from omni_compiler.ai_tools import suggest_fix  # noqa: PLC0415

        code = Path(file).read_text(encoding="utf-8")
        ast = parse(tokenize(code))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    fixes = suggest_fix(ast, None)
    if not fixes:
        click.echo("omni suggest: no errors found")
        sys.exit(0)
    click.echo(json.dumps({"schema": "omni.suggest", "version": "1.0", "fixes": fixes}, indent=2))
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.argument("function")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Write the generated test to this path instead of stdout.",
)
def generate(file: Path, function: str, output: Path | None):
    """Draft a pytest test file for a function."""
    try:
        from omni_compiler.ai_tools import generate_test  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file)
        test_source = generate_test(ast, symbol_table, function, source_file=str(file))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    if output:
        output.write_text(test_source, encoding="utf-8")
        click.echo(f"omni generate: wrote {output}")
    else:
        click.echo(test_source)
    sys.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.argument("function", required=False)
def trace(file: Path, function: str | None):
    """Step through a function (or the entry block) and print trace events."""
    try:
        from omni_compiler.ai_tools import trace_execution, trace_to_json  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file)
        events = trace_execution(ast, symbol_table, function)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(trace_to_json(events))
    sys.exit(0)


@cli.command()
def lsp():
    """Run the OmniScript Language Server (stdio JSON-RPC)."""
    try:
        from omni_compiler.lsp import OmniLspServer  # noqa: PLC0415

        OmniLspServer().run()
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    cli()