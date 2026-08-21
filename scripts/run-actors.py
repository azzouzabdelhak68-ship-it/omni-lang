"""v5.3 distributed systems bridge.

Standalone `omni run-actors`-style entry point: compile an OmniScript actor
program through the normal pipeline (lexer -> parser -> checker -> MIR ->
JS emitter) and execute the emitted JS under the `sim.actor` runtime using the
Node harness (`scripts/run-actors.js`).

Usage:
    python scripts/run-actors.py examples/actors.omni
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
if str(_REPO) not in sys.path:  # allow running as `python scripts/run-actors.py`
    sys.path.insert(0, str(_REPO))

from omni_compiler.checker import analyze  # noqa: E402
from omni_compiler.emitter import emit_js  # noqa: E402
from omni_compiler.lexer import tokenize  # noqa: E402
from omni_compiler.mir import to_mir  # noqa: E402
from omni_compiler.parser import parse  # noqa: E402

_HARNESS = _HERE / 'run-actors.js'


def compile_actors_html(source: str) -> str:
    """Compile an OmniScript actor program to the emitted JS HTML document."""
    tokens = tokenize(source)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def run_actors(
    source: str,
    *,
    node: str = 'node',
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    """Compile ``source`` and run it under Node; return the subprocess result."""
    html = compile_actors_html(source)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', encoding='utf-8', delete=False) as f:
        f.write(html)
        html_path = Path(f.name)
    try:
        return subprocess.run(
            [node, str(_HARNESS), str(html_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    finally:
        html_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: compile and run one .omni actor program."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print('usage: python scripts/run-actors.py <file.omni>', file=sys.stderr)  # noqa: T201
        return 2
    if shutil.which('node') is None:
        print("run-actors: 'node' is required but was not found on PATH", file=sys.stderr)  # noqa: T201
        return 3
    omni_file = Path(args[0])
    try:
        source = omni_file.read_text(encoding='utf-8')
    except OSError as exc:
        print(f'run-actors: cannot read {omni_file}: {exc}', file=sys.stderr)  # noqa: T201
        return 1
    try:
        proc = run_actors(source)
    except Exception as exc:  # compile error
        print(f'run-actors: compile failed for {omni_file.name}: {exc}', file=sys.stderr)  # noqa: T201
        return 1
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())