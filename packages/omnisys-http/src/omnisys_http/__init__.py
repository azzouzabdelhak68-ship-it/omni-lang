"""OMNISYS.http — high-level HTTP client/server over the OMNISYS.net transport.

``inproc://`` URLs dispatch to servers bound with :func:`register` (deterministic
and testable); any other URL is routed through the transport hook set with
:func:`register_transport`, mirroring the JS reference lane ``omnisys/http.js``
(``OMNISYS_MODULES["http"]``). ``redirect``/``not_found`` build response
values; ``json_get``/``json_post`` round-trip JSON bodies.
"""

import json
import re
from collections.abc import Callable
from typing import Any, NoReturn, TypeAlias

from omnisys_core import PanicError, panic
from omnisys_net import request as _net_request

__all__ = [
    'client',
    'send',
    'get',
    'post',
    'put',
    'delete',
    'json_get',
    'json_post',
    'redirect',
    'not_found',
    'response',
    'response_json',
    'register',
    'register_transport',
]

Client: TypeAlias = dict[str, Any]
Response: TypeAlias = dict[str, Any]
Server: TypeAlias = dict[str, Any]
Transport: TypeAlias = Callable[[str, str, Any], Response]

_REGISTRY: dict[str, Server] = {}
_transport: Transport | None = None

_URL_RE = re.compile(r'^([a-z][a-z0-9+.-]*):\/\/([^/]+)(.*)$')


def client() -> Client:
    """Create a portable HTTP client value."""
    return {'tag': 'http.client', 'transport': 'portable'}


def send(_client: Client, method: str, url: str, body: Any, timeout: float = 0) -> Response:
    """Send an arbitrary request; the client value is currently unused. ``timeout`` in milliseconds (0 = no timeout)."""
    return _dispatch(method, url, body, timeout)


def get(url: str, timeout: float = 0) -> Response:
    """Send a GET request to ``url``. ``timeout`` in milliseconds (0 = no timeout)."""
    return _dispatch('GET', url, None, timeout)


def post(url: str, body: Any, timeout: float = 0) -> Response:
    """Send a POST request to ``url`` with ``body``. ``timeout`` in milliseconds (0 = no timeout)."""
    return _dispatch('POST', url, body, timeout)


def put(url: str, body: Any, timeout: float = 0) -> Response:
    """Send a PUT request to ``url`` with ``body``. ``timeout`` in milliseconds (0 = no timeout)."""
    return _dispatch('PUT', url, body, timeout)


def delete(url: str, timeout: float = 0) -> Response:
    """Send a DELETE request to ``url``. ``timeout`` in milliseconds (0 = no timeout)."""
    return _dispatch('DELETE', url, None, timeout)


def json_get(url: str, timeout: float = 0) -> Any:
    """GET ``url`` and parse the JSON response body. ``timeout`` in milliseconds (0 = no timeout)."""
    return json.loads(get(url, timeout)['body'])


def json_post(url: str, value: Any, timeout: float = 0) -> Any:
    """POST ``value`` as JSON to ``url`` and parse the JSON response body. ``timeout`` in milliseconds (0 = no timeout)."""
    return json.loads(post(url, json.dumps(value), timeout)['body'])


def redirect(location: str, status: int | None) -> Response:
    """Build a redirect response to ``location`` (status 302 by default)."""
    return {'status': status or 302, 'headers': {'location': str(location)}, 'body': ''}


def not_found(body: str) -> Response:
    """Build a 404 response with ``body``."""
    return {'status': 404, 'headers': {}, 'body': str(body)}


def response(status: int, body: Any) -> Response:  # noqa: ANN401
    """Build a generic response with ``status`` and ``body``."""
    return {'status': status, 'headers': {}, 'body': str(body)}


def response_json(status: int, value: Any) -> Response:  # noqa: ANN401
    """Build a JSON response with ``status`` and JSON-serialized ``value``."""
    return {'status': status, 'headers': {'content-type': 'application/json'}, 'body': json.dumps(value)}


def register(name: str, server: Server) -> Server:
    """Bind an OMNISYS.net server to an ``inproc://`` host name."""
    _REGISTRY[str(name)] = server
    return server


def register_transport(fn: Transport | None) -> None:
    """Set or clear the transport hook used for non-inproc URLs."""
    globals()['_transport'] = fn


def _parse_url(url: str) -> dict[str, str]:
    """Split a URL into scheme, host and path components."""
    text = str(url)
    if text.startswith('inproc://'):
        rest = text[len('inproc://') :]
        slash = rest.find('/')
        if slash == -1:
            return {'host': rest, 'path': '/', 'scheme': 'inproc'}
        return {'host': rest[:slash], 'path': rest[slash:], 'scheme': 'inproc'}
    match = _URL_RE.match(text)
    if match is None:
        panic('http: malformed url: ' + url)
    return {'scheme': match.group(1), 'host': match.group(2), 'path': match.group(3) or '/'}


def _dispatch(method: str, url: str, body: Any, timeout: float = 0) -> Response:
    """Dispatch a request to an inproc server or the registered transport. ``timeout`` in milliseconds (0 = no timeout)."""
    target = _parse_url(url)
    if target['scheme'] == 'inproc':
        server = _REGISTRY.get(target['host'])
        if server is not None:
            return _net_request(server, method, target['path'], '' if body is None else str(body))
    if _transport is not None:
        return _transport(method, url, body, timeout)
    return _no_transport(target['scheme'])


def _no_transport(scheme: str) -> NoReturn:
    """Panic because no transport can handle the URL's scheme."""
    raise PanicError(
        "http: no transport for scheme '"
        + scheme
        + "' (register an inproc:// server or set a transport)"
    )
