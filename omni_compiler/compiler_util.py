"""Shared helpers reused across compiler modules (single source of truth)."""

from typing import Any

from omni_compiler.checker import DiagnosticError


def _is_style_open(html: str, i: int) -> bool:
    """Return True when the ``<style`` open tag begins at ``i`` in ``html``."""
    return html[i : i + 6].lower() == '<style' and (i + 6 >= len(html) or html[i + 6] in '> \t\r\n')


def _is_style_close(html: str, i: int) -> bool:
    """Return True when the ``</style`` close tag begins at ``i`` in ``html``."""
    return html[i : i + 7].lower() == '</style' and (
        i + 7 >= len(html) or html[i + 7] in '> \t\r\n'
    )


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
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-NAME-001',
            'category': 'name',
            'severity': 'error',
            'message': msg,
            'details': msg,
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
