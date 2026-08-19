"""OMNISYS.tool — language-service tooling: lexer helpers and compiler bridge.

Python reference implementation of the OMNISYS ``tool`` module (v6),
mirroring the JS reference lane ``omnisys/tool.js`` and satisfying the
registry contract (``OMNISYS_MODULES["tool"]``). ``tokenize``,
``line_count`` and ``identifier_count`` are pure helpers; ``check`` and
``explain`` bridge to the ``omni_compiler.cli`` compiler CLI via subprocess
(the compiler's own diagnostics), declaring the ``process`` capability.
"""

import json
import re
import subprocess
import sys
from typing import Any, TypeAlias

__all__ = ['tokenize', 'check', 'explain', 'line_count', 'identifier_count']

Token: TypeAlias = dict[str, str]

_KEYWORDS = frozenset(
    {
        'when',
        'end',
        'if',
        'else',
        'then',
        'fn',
        'return',
        'show',
        'uses',
        'reads',
        'writes',
        'pure',
        'UI',
        'scene',
        'require',
        'ensure',
        'and',
        'or',
        'not',
        'is',
        'type',
        'for',
        'in',
        'break',
        'continue',
        'import',
        'true',
        'false',
        'none',
        'box',
        'sphere',
        'cylinder',
        'plane',
        'light',
        'camera',
    }
)

_TOKEN_PATTERN = re.compile(
    r'[A-Za-z_][A-Za-z0-9_]*|"[^"]*"|\'[^\']*\'|\d+(?:\.\d+)?|=>|>=|<=|[<>=:+*/,.\[\]{}()-]|\s+'
)


def tokenize(code: Any) -> list[Token]:
    """Tokenize ``code`` into ``{value, kind}`` dicts (whitespace skipped)."""
    tokens: list[Token] = []
    for match in _TOKEN_PATTERN.finditer(str(code)):
        value = match.group(0)
        if value.isspace():
            continue
        if value in _KEYWORDS:
            kind = 'keyword'
        elif value[0].isdigit():
            kind = 'number'
        elif value[0] in '"\'':
            kind = 'text'
        else:
            kind = 'identifier'
        tokens.append({'value': value, 'kind': kind})
    return tokens


def _run_omni(command: str, path: Any) -> dict[str, Any]:
    """Run ``python -m omni_compiler.cli <command> <path>`` and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'omni_compiler.cli', command, str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return {
            'status': result.returncode,
            'stdout': result.stdout or '',
            'stderr': result.stderr or '',
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'status': 1, 'stdout': '', 'stderr': str(exc)}


def _check_command(command: str, path: Any) -> dict[str, Any]:
    """Run a compiler CLI command and shape the result like the JS lane."""
    result = _run_omni(command, path)
    parsed = None
    try:
        parsed = json.loads(result['stdout'])
    except (ValueError, TypeError):
        parsed = None
    return {
        'path': str(path),
        'ok': result['status'] == 0,
        'diagnostic': parsed,
        'stderr': result['stderr'],
    }


def check(path: Any) -> dict[str, Any]:
    """Type/effect-check an OmniScript file via the compiler CLI."""
    return _check_command('check', path)


def explain(path: Any) -> dict[str, Any]:
    """Explain errors in an OmniScript file via the compiler CLI."""
    return _check_command('explain', path)


def line_count(code: Any) -> int:
    """Return the number of lines in ``code``."""
    return len(str(code).split('\n'))


def identifier_count(code: Any) -> int:
    """Return the number of identifier-kind tokens in ``code``."""
    return sum(1 for token in tokenize(code) if token['kind'] == 'identifier')
