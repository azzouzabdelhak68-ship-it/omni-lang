"""OMNISYS.net — networking.

Portable, in-process, synchronous request/response model: a server value
wraps a plain callable handler (or None), ``request`` drives it
deterministically, and ``middleware`` composes handlers. Mirrors the JS
reference lane ``omnisys/net.js`` as locked by the compiler registry
(``OMNISYS_MODULES["net"]``). ``response``/``response_json``/``status_of``/
``body_of`` are pure; the six transport functions declare the ``network``
capability. The wire (TCP/TLS/HTTP) is a future backend escape behind this
same semantic API.
"""

import json
from collections.abc import Callable
from typing import Any, TypeAlias, cast

__all__ = [
    'server',
    'start',
    'request',
    'get',
    'post',
    'middleware',
    'response',
    'response_json',
    'status_of',
    'body_of',
]

Request: TypeAlias = dict[str, Any]
Server: TypeAlias = dict[str, Any]
Response: TypeAlias = dict[str, Any]
Handler: TypeAlias = Callable[[Request], Response] | None
Middleware: TypeAlias = Callable[[Request, Callable[[Request], Response]], Response]


def server(handler: Handler = None) -> Server:
    """Return a new server value wrapping ``handler`` (or None)."""
    return {'tag': 'server', 'handler': handler, 'middlewares': []}


def start(server: Server) -> Server:
    """Mark ``server`` as running and return the same server value."""
    server['running'] = True
    return server


def request(server: Server, method: str, path: str, body: Any = None) -> Response:
    """Auto-start ``server``, build the request value, and run its handler."""
    if not server.get('running'):
        server['running'] = True
    req: Request = {
        'method': str(method).upper(),
        'path': str(path),
        'body': '' if body is None else str(body),
        'headers': {},
    }
    handler: Handler = cast(Handler, server.get('handler'))
    if not handler:
        return response(501, 'no handler')
    return handler(req)


def get(server: Server, path: str) -> Response:
    """Send a GET request to ``server`` with an empty body."""
    return request(server, 'GET', path, None)


def post(server: Server, path: str, body: Any = None) -> Response:
    """Send a POST request to ``server`` with ``body``."""
    return request(server, 'POST', path, body)


def middleware(
    handler: Callable[[Request], Response],
    middlewares: list[Middleware],
) -> Callable[[Request], Response]:
    """Compose ``middlewares`` around ``handler``; the first entry runs first."""
    wrapped: Callable[[Request], Response] = handler
    for mw in reversed(middlewares):
        wrapped = (lambda _mw, _nxt: lambda _req: _mw(_req, _nxt))(mw, wrapped)  # noqa: PLC3002 - contract-mandated closure form
    return lambda req: wrapped(req)  # noqa: PLW0108 - keeps returned function distinct from handler


def response(status: int, body: Any) -> Response:
    """Return a plain ``{"status": ..., "headers": {}, "body": ...}`` value."""
    return {'status': status, 'headers': {}, 'body': str(body)}


def response_json(status: int, value: Any) -> Response:
    """Return a JSON response with the ``content-type`` header set."""
    return {
        'status': status,
        'headers': {'content-type': 'application/json'},
        'body': json.dumps(value, ensure_ascii=False, separators=(',', ':')),
    }


def status_of(response: Response) -> int:
    """Return the status code of ``response``, or 0 when it is falsy."""
    if not response:
        return 0
    return cast(int, response['status'])


def body_of(response: Response) -> str:
    """Return the body of ``response``, or '' when it is falsy."""
    if not response:
        return ''
    return cast(str, response['body'])
