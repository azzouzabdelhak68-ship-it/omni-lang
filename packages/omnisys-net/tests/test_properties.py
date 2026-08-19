"""Hypothesis property tests for OMNISYS.net invariants."""

import json
import string

import omnisys_net as net
from hypothesis import given, settings
from hypothesis import strategies as st

_SETTINGS = settings(max_examples=150, deadline=None)

_NAME = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=8)
_NAMES = st.lists(_NAME, unique=True, max_size=8)
_METHOD = st.text()
_PATH = st.text()
_BODY = st.one_of(st.none(), st.text())
_STATUS = st.integers()
_JSON_VALUE = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(), children, max_size=4)
    ),
    max_leaves=20,
)
_REQ = {'method': 'GET', 'path': '/', 'body': '', 'headers': {}}


@_SETTINGS
@given(_NAMES)
def test_middleware_runs_in_list_order(names: list[str]) -> None:
    log: list[str] = []

    def handler(_req: object) -> dict[str, object]:
        log.append('handler')
        return net.response(200, 'ok')

    middlewares: list[object] = []
    for name in names:

        def mw(req: object, next_fn: object, _tag: str = name) -> dict[str, object]:
            log.append(_tag)
            return next_fn(req)  # type: ignore[no-any-return]

        middlewares.append(mw)

    net.middleware(handler, middlewares)(_REQ)
    assert log == names + ['handler']


@_SETTINGS
@given(_NAMES)
def test_middleware_unwinds_in_reverse_order(names: list[str]) -> None:
    log: list[str] = []

    def handler(_req: object) -> dict[str, object]:
        log.append('handler')
        return net.response(200, 'ok')

    middlewares: list[object] = []
    for name in names:

        def mw(req: object, next_fn: object, _tag: str = name) -> dict[str, object]:
            log.append(_tag)
            result = next_fn(req)  # type: ignore[no-any-return]
            log.append(_tag)
            return result

        middlewares.append(mw)

    net.middleware(handler, middlewares)(_REQ)
    assert log == names + ['handler'] + list(reversed(names))


@_SETTINGS
@given(_NAMES)
def test_middleware_passes_same_request_through(names: list[str]) -> None:
    seen: list[int] = []

    def handler(_req: object) -> dict[str, object]:
        return net.response(200, 'ok')

    middlewares: list[object] = []
    for _name in names:

        def mw(req: object, next_fn: object) -> dict[str, object]:
            seen.append(id(req))
            return next_fn(req)  # type: ignore[no-any-return]

        middlewares.append(mw)

    req: dict[str, object] = {'method': 'GET', 'path': '/', 'body': '', 'headers': {}}
    net.middleware(handler, middlewares)(req)
    assert seen == [id(req)] * len(names)


@_SETTINGS
@given(_METHOD, _PATH)
def test_middleware_empty_is_passthrough(method: str, path: str) -> None:
    seen: list[str] = []

    def handler(req: dict[str, object]) -> dict[str, object]:
        seen.append(str(req['method']))
        return net.response(200, str(req['path']))

    req: dict[str, object] = {'method': method, 'path': path, 'body': '', 'headers': {}}
    result = net.middleware(handler, [])(req)
    assert seen == [method]
    assert result['body'] == path


@_SETTINGS
@given(_METHOD, _PATH, _BODY)
def test_request_normalizes_inputs(method: str, path: str, body: str | None) -> None:
    seen: dict[str, object] = {}

    def handler(req: dict[str, object]) -> dict[str, object]:
        seen.update(req)
        return net.response(200, 'ok')

    net.request(net.server(handler), method, path, body)
    assert seen['method'] == str(method).upper()
    assert seen['path'] == str(path)
    assert seen['body'] == ('' if body is None else str(body))
    assert seen['headers'] == {}


@_SETTINGS
@given(_METHOD, _PATH, _BODY)
def test_request_auto_starts_server(method: str, path: str, body: str | None) -> None:
    srv = net.server(lambda _req: net.response(200, 'ok'))
    net.request(srv, method, path, body)
    assert srv['running'] is True


@_SETTINGS
@given(_METHOD, _PATH, _BODY)
def test_request_preserves_true_running(method: str, path: str, body: str | None) -> None:
    srv = net.server(lambda _req: net.response(200, 'ok'))
    srv['running'] = True
    net.request(srv, method, path, body)
    assert srv['running'] is True


@_SETTINGS
@given(_METHOD, _PATH, _BODY)
def test_request_starts_server_with_false_running(method: str, path: str, body: str | None) -> None:
    srv = net.server(lambda _req: net.response(200, 'ok'))
    srv['running'] = False
    net.request(srv, method, path, body)
    assert srv['running'] is True


@_SETTINGS
@given(_PATH)
def test_get_delegates_with_empty_body(path: str) -> None:
    seen: dict[str, object] = {}

    def handler(req: dict[str, object]) -> dict[str, object]:
        seen.update(req)
        return net.response(200, 'ok')

    net.get(net.server(handler), path)
    assert seen['method'] == 'GET'
    assert seen['path'] == str(path)
    assert seen['body'] == ''


@_SETTINGS
@given(_PATH, _BODY)
def test_post_delegates_with_body(path: str, body: str | None) -> None:
    seen: dict[str, object] = {}

    def handler(req: dict[str, object]) -> dict[str, object]:
        seen.update(req)
        return net.response(200, 'ok')

    net.post(net.server(handler), path, body)
    assert seen['method'] == 'POST'
    assert seen['body'] == ('' if body is None else str(body))


@_SETTINGS
@given(_STATUS, st.text())
def test_response_shape_and_accessors(status: int, body: str) -> None:
    resp = net.response(status, body)
    assert resp == {'status': status, 'headers': {}, 'body': body}
    assert net.status_of(resp) == status
    assert net.body_of(resp) == body


@_SETTINGS
@given(_STATUS, _JSON_VALUE)
def test_response_json_roundtrips_value(status: int, value: object) -> None:
    resp = net.response_json(status, value)
    assert resp['status'] == status
    assert resp['headers'] == {'content-type': 'application/json'}
    assert json.loads(resp['body']) == value


def test_accessors_of_falsy_values() -> None:
    for falsy in (None, {}, [], '', 0):
        assert net.status_of(falsy) == 0
        assert net.body_of(falsy) == ''
