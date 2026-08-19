"""Provide structured error values with codes and context for OmniScript.

OMNISYS.error mirrors ``omnisys/error.js``. Error values are plain dicts
(``{"tag": "error", "message": ..., "code": ..., "context": {...}, "stack": ...}``)
so they remain JSON-friendly, portable across backends, and machine-readable by AI
tooling. ``throw_error`` converts a value into a raised :class:`OmniError`
exception when an error must cross a call boundary.
"""

import traceback
from typing import Any

Error = dict[str, Any]

__all__ = [
    'OmniError',
    'error',
    'error_code',
    'error_message',
    'error_code_of',
    'error_stack',
    'error_with_context',
    'error_has_context',
    'error_to_dict',
    'throw_error',
    'is_error',
]


class OmniError(Exception):
    """A structured runtime error raised by ``throw_error``."""

    def __init__(
        self, message: str, code: str = 'E-OMNI', context: dict[str, Any] | None = None, stack: str = ''
    ) -> None:
        """Initialize the error from a message, code, and context map."""
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = dict(context) if context is not None else {}
        self.stack = stack

    def __str__(self) -> str:
        """Return the human-readable message."""
        return self.message


def _capture_stack() -> str:
    """Capture the current stack trace as a string."""
    return ''.join(traceback.format_stack()[:-1])  # Exclude the capture frame itself


def error(message: str) -> Error:
    """Create an error value with the default code ``E-OMNI`` and captured stack trace."""
    return {'tag': 'error', 'message': message, 'code': 'E-OMNI', 'context': {}, 'stack': _capture_stack()}


def error_code(message: str, code: str) -> Error:
    """Create an error value with an explicit code and captured stack trace."""
    return {'tag': 'error', 'message': message, 'code': code, 'context': {}, 'stack': _capture_stack()}


def error_message(err: object) -> str:
    """Return the message of an error value, falling back to ``str(err)``."""
    if isinstance(err, dict) and 'message' in err:
        return str(err['message'])
    return str(err)


def error_code_of(err: object) -> str:
    """Return the code of an error value, or ``''`` when absent."""
    if isinstance(err, dict):
        code = err.get('code')
        if code is not None:
            return str(code)
    return ''


def error_stack(err: object) -> str:
    """Return the stack trace of an error value, or ``''`` when absent."""
    if isinstance(err, dict):
        stack = err.get('stack')
        if stack is not None:
            return str(stack)
    return ''


def error_with_context(err: Error, key: str, value: Any) -> Error:
    """Return a new error with ``key`` added to its context; ``err`` is not mutated."""
    new_err = dict(err)
    existing = new_err.get('context', {})
    context: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    context[key] = value
    new_err['context'] = context
    return new_err


def error_has_context(err: Error, key: str) -> bool:
    """Return True when ``err``'s context contains ``key``."""
    context = err.get('context', {})
    return isinstance(context, dict) and key in context


def error_to_dict(err: Error) -> Error:
    """Return a normalized error dict built through the accessors."""
    return {
        'tag': 'error',
        'message': error_message(err),
        'code': error_code_of(err),
        'stack': error_stack(err),
        'context': err.get('context', {}),
    }


def throw_error(err: Error) -> None:
    """Raise ``err`` as an :class:`OmniError`."""
    context = err.get('context', {})
    raise OmniError(
        message=error_message(err),
        code=error_code_of(err),
        context=context if isinstance(context, dict) else {},
        stack=error_stack(err),
    )


def is_error(x: object) -> bool:
    """Return True when ``x`` is an error value dict."""
    return isinstance(x, dict) and x.get('tag') == 'error'
