"""CLI Tool for OmniScript Compiler.

Commands: check, run, inspect, explain, build, verify, suggest, generate, trace, lsp.
"""

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.emitter import emit_js
from omni_compiler.formatter import FormatConfig, format_file
from omni_compiler.lexer import is_agent_mode, tokenize
from omni_compiler.mir import MIRModule, to_mir
from omni_compiler.parser import parse
from omni_compiler.wasm_emitter import emit_wasm, wasm_build_command


def _compile(file: Path, lang: str | None = None) -> tuple[Any, Any, MIRModule]:
    code = Path(file).read_text(encoding='utf-8')

    # Auto-detect agent mode if not specified
    if lang is None:
        lang = 'agent' if is_agent_mode(code) else 'en'

    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return ast, symbol_table, mir


def _mir_uses_omnisys(mir: MIRModule) -> bool:
    """Return True when the program actually invokes an ``omnisys.*`` function.

    Walks every MIR statement (entry point and function bodies) for a call node
    whose name begins with ``omnisys`` (the MIR normalizes ``OMNISYS.*`` to
    lowercase in :func:`omni_compiler.mir._normalize_call_name`).
    """

    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            if node.get('op') == 'call' and str(node.get('name', '')).startswith('omnisys'):
                return True
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return any(walk(v) for v in node)
        return False

    if walk(mir.entry_point):
        return True
    return any(walk(fn.body) for fn in mir.functions.values())


def _reject_omnisys_on_native_target(target: str, mir: MIRModule) -> None:
    """§8.3 per-capability gate: native lanes lack the OMNISYS runtime.

    The gate is capability-based, not import-based. ``import OMNISYS`` alone
    consumes no capability, so an import-only program may build on native
    targets (the documented §8.3 carve-out). Only a program that actually calls
    an ``omnisys.*`` function requires the JS lane — the reference OMNISYS
    back-end (spec §17.10.E/§17.10.R) — and is rejected with E-BACKEND-001.
    """
    if not _mir_uses_omnisys(mir):
        return
    click.echo(
        json.dumps(
            _diagnostic_from_exception(
                DiagnosticError(
                    'E-BACKEND-001',
                    'backend',
                    'error',
                    'OMNISYS functions require the JS lane.',
                    f"'{target}' does not provide the OMNISYS runtime. "
                    'The JS lane is the reference OMNISYS back-end (spec §17.10.E/§17.10.R). '
                    'Per spec §8.3 this gate is per-capability: an import-only program '
                    '(no `omnisys.*` call) builds on native targets.',
                    1,
                    1,
                    0,
                    0,
                    {'target': target, 'imports': mir.imports},
                    [
                        {
                            'id': 'target-js',
                            'kind': 'replace_span',
                            'applicability': 'automatic',
                            'description': 'Build with --target js, the OMNISYS reference '
                            'back-end.',
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': '--target js',
                            },
                        }
                    ],
                )
            ),
            indent=2,
        )
    )
    sys.exit(1)


def _diagnostic_from_exception(e: Exception) -> dict[str, Any]:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-SYNTAX-001',
            'category': 'syntax',
            'severity': 'error',
            'message': 'Syntax error.',
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'fix-syntax',
                    'kind': 'replace_span',
                    'applicability': 'suggested',
                    'description': 'Fix the reported syntax issue.',
                    'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    if isinstance(e, NameError):
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-NAME-001',
            'category': 'name',
            'severity': 'error',
            'message': str(e),
            'details': str(e),
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'define-name',
                    'kind': 'suggested',
                    'applicability': 'suggested',
                    'description': 'Define the missing name or check the spelling.',
                    'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    return {
        'schema': 'omni.diagnostic',
        'version': '1.0',
        'code': 'E-INTERNAL-001',
        'category': 'internal',
        'severity': 'error',
        'message': str(e),
        'details': f'{type(e).__name__}: {e}',
        'span': {'start': 0, 'end': 0},
        'location': {'line': 1, 'column': 1},
        'context': {},
        'fixes': [],
    }


@click.group()
@click.version_option(version='0.1.0', prog_name='omni')
def cli() -> None:
    """OmniScript Compiler - AI-first language with declared effects and live links."""
    pass


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def check(file: Path, lang: str | None) -> None:
    """Type-check and effect-check an OmniScript file."""
    try:
        _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(f'omni check: OK — {file.name}')
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def run(file: Path, lang: str | None) -> None:
    """Compile and execute an OmniScript file (Node.js required)."""
    import subprocess  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    try:
        _, _, mir = _compile(file, lang)
        html = emit_js(mir)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        html_path = f.name

    try:
        runner = Path(__file__).resolve().parents[1] / 'scripts' / 'run-omnisys.js'
        result = subprocess.run(
            ['node', str(runner), html_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        click.echo(
            json.dumps(
                {
                    'schema': 'omni.diagnostic',
                    'version': '1.0',
                    'code': 'E-RUNTIME-001',
                    'category': 'runtime',
                    'severity': 'error',
                    'message': 'Node.js not found.',
                    'details': '`omni run` requires Node.js on PATH to execute the emitted '
                    'program.',
                    'span': {'start': 0, 'end': 0},
                    'location': {'line': 1, 'column': 1},
                    'context': {},
                    'fixes': [],
                },
                indent=2,
            )
        )
        sys.exit(1)
    finally:
        with contextlib.suppress(OSError):
            Path(html_path).unlink()
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, err=True, nl=False)
    sys.exit(result.returncode)


@cli.command()
@click.argument('symbol')
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def inspect(symbol: str, file: Path, lang: str | None) -> None:
    """Inspect a symbol in an OmniScript file."""
    try:
        _, symbol_table, _ = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    rec = symbol_table.inspect_symbol(symbol)
    if rec is None:
        click.echo(
            json.dumps(
                {
                    'schema': 'omni.symbol',
                    'version': '1.0',
                    'name': symbol,
                    'kind': 'unknown',
                    'type': 'unknown',
                    'declared_effects': {'uses': [], 'reads': [], 'writes': []},
                    'span': {'start': 0, 'end': 0},
                    'location': {'line': 1, 'column': 1},
                    'dependencies': [],
                    'exported': False,
                },
                indent=2,
            )
        )
        sys.exit(1)
    click.echo(json.dumps(rec, indent=2))
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def explain(file: Path, lang: str | None) -> None:
    """Explain an error in an OmniScript file."""
    try:
        _compile(file, lang)
    except Exception as e:
        d = _diagnostic_from_exception(e)
        d['hint'] = d.get('message', '')
        click.echo(json.dumps(d, indent=2))
        sys.exit(1)
    click.echo('omni explain: no errors found')
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--target',
    default='js',
    show_default=True,
    type=click.Choice(['js', 'c', 'rust', 'wasm-browser', 'wasm-wasi']),
)
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    help='Output path (defaults to the input stem + target suffix).',
)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def build(file: Path, target: str, output: Path | None, lang: str | None) -> None:
    """Build an OmniScript file to a target artifact."""
    try:
        _, _, mir = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)

    mode = None
    if target == 'js':
        content = emit_js(mir)
        out = output or file.with_suffix('.html')
    elif target == 'c':
        _reject_omnisys_on_native_target(target, mir)
        content = emit_c(mir)
        out = output or file.with_suffix('.c')
    elif target == 'rust':
        _reject_omnisys_on_native_target(target, mir)
        try:
            from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415 - optional peer module

            content = emit_rust(mir)
        except ImportError:
            click.echo(
                'omni build: rust target unavailable (rust_emitter.py has not landed yet)',
                err=True,
            )
            sys.exit(1)
        out = output or file.with_suffix('.rs')
    elif target in ('wasm-browser', 'wasm-wasi'):
        _reject_omnisys_on_native_target(target, mir)
        mode = 'browser' if target == 'wasm-browser' else 'wasi'
        content = emit_wasm(mir, mode=mode)
        default_out = file.with_suffix('.html' if mode == 'browser' else '.c')
        out = output or default_out
    else:  # pragma: no cover - click restricts valid targets
        click.echo(f'omni build: unknown target: {target}', err=True)
        sys.exit(1)

    out.write_text(content, encoding='utf-8')
    click.echo(f'omni build: wrote {out} (target={target})')
    if mode is not None:
        click.echo(f'  {wasm_build_command(mode)}', err=True)
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def verify(file: Path, lang: str | None) -> None:
    """Prove require/ensure contracts statically with an SMT solver."""
    try:
        from omni_compiler.smt import verify_contracts  # noqa: PLC0415

        ast, _, _ = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    results = verify_contracts(ast)
    batch = {'schema': 'omni.verify.batch', 'version': '1.0', 'results': results}
    click.echo(json.dumps(batch, indent=2))
    failed = [r for r in results if r['status'] == 'failed']
    sys.exit(1 if failed else 0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def suggest(file: Path, lang: str | None) -> None:  # noqa: ARG001
    """Propose ranked fixes for errors in an OmniScript file."""
    try:
        from omni_compiler.ai_tools import suggest_fix  # noqa: PLC0415

        code = Path(file).read_text(encoding='utf-8')
        ast = parse(tokenize(code))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    fixes = suggest_fix(ast, None)
    if not fixes:
        click.echo('omni suggest: no errors found')
        sys.exit(0)
    click.echo(json.dumps({'schema': 'omni.suggest', 'version': '1.0', 'fixes': fixes}, indent=2))
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.argument('function')
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    help='Write the generated test to this path instead of stdout.',
)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def generate(file: Path, function: str, output: Path | None, lang: str | None) -> None:
    """Draft a pytest test file for a function."""
    try:
        from omni_compiler.ai_tools import generate_test  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file, lang)
        test_source = generate_test(ast, symbol_table, function, source_file=str(file))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    if output:
        output.write_text(test_source, encoding='utf-8')
        click.echo(f'omni generate: wrote {output}')
    else:
        click.echo(test_source)
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.argument('function', required=False)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def trace(file: Path, function: str | None, lang: str | None) -> None:
    """Step through a function (or the entry block) and print trace events."""
    try:
        from omni_compiler.ai_tools import trace_execution, trace_to_json  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file, lang)
        events = trace_execution(ast, symbol_table, function)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(trace_to_json(events))
    sys.exit(0)


@cli.command()
def lsp() -> None:
    """Run the OmniScript Language Server (stdio JSON-RPC)."""
    try:
        from omni_compiler.lsp import OmniLspServer  # noqa: PLC0415

        OmniLspServer().run()
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(0)


@cli.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--check', is_flag=True, help='Exit with code 1 if any file would be changed.')
@click.option('--write', is_flag=True, help='Write changes to files (default).')
@click.option('--diff', is_flag=True, help='Show diff instead of writing.')
@click.option('--indent', default=4, show_default=True, type=int, help='Indent size in spaces.')
@click.option('--tabs', is_flag=True, help='Use tabs for indentation.')
def fmt(  # noqa: PLR0913, PLR0917
    paths: tuple[Path, ...], check: bool, _write: bool, diff: bool, indent: int, tabs: bool
) -> None:
    """Format OmniScript (.omni) files to canonical layout."""
    if not paths:
        click.echo('omni fmt: no files specified', err=True)
        sys.exit(1)

    config = FormatConfig(indent_size=indent, use_tabs=tabs)
    any_changed = False
    any_error = False

    for path in paths:
        try:
            changed, formatted = format_file(str(path), config, check=check or diff, diff=diff)
        except Exception as e:
            click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
            any_error = True
            continue

        if changed:
            any_changed = True
            if diff:
                import difflib  # noqa: PLC0415

                original = Path(path).read_text(encoding='utf-8')
                diff_lines = list(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        formatted.splitlines(keepends=True),
                        fromfile=f'a/{path.name}',
                        tofile=f'b/{path.name}',
                    )
                )
                click.echo(''.join(diff_lines), nl=False)
            elif not check:
                click.echo(f'omni fmt: formatted {path}')
        elif not check and not diff:
            click.echo(f'omni fmt: unchanged {path}')

    if any_error:
        sys.exit(1)
    if check and any_changed:
        click.echo('omni fmt: some files would be reformatted', err=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    cli()
