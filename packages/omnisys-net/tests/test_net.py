"""Unit tests for every OMNISYS.net function."""

import json

import omnisys_net as net

_REQ = {'method': 'GET', 'path': '/', 'body': '', 'headers': {}}


def _echo_server() -> tuple[dict[str, object], dict[str, object]]:
    seen: dict[str, object] = {}

    def handler(req: dict[str, object]) -> dict[str, object]:
        seen.update(req)
        return net.response(200, 'ok')

    return net.server(handler), seen


def test_server_builds_value_shape() -> None:
    assert net.server(None) == {'tag': 'server', 'handler': None, 'middlewares': []}


def test_server_defaults_handler_to_none() -> None:
    assert net.server()['handler'] is None


def test_server_keeps_callable_handler() -> None:
    def handler(_req: dict[str, object]) -> dict[str, object]:
        return net.response(200, 'ok')

    result = net.server(handler)
    assert result['handler'] is handler


def test_start_marks_running_and_returns_same_server() -> None:
    srv = net.server(None)
    assert net.start(srv) is srv
    assert srv['running'] is True


def test_start_is_idempotent() -> None:
    srv = net.server(None)
    net.start(srv)
    net.start(srv)
    assert srv['running'] is True


def test_request_auto_starts_fresh_server() -> None:
    srv, _seen = _echo_server()
    assert 'running' not in srv
    net.request(srv, 'GET', '/', None)
    assert srv['running'] is True


def test_request_keeps_true_running() -> None:
    srv, _seen = _echo_server()
    srv['running'] = True
    net.request(srv, 'GET', '/', None)
    assert srv['running'] is True


def test_request_turns_false_running_to_true() -> None:
    srv, _seen = _echo_server()
    srv['running'] = False
    net.request(srv, 'GET', '/', None)
    assert srv['running'] is True


def test_request_builds_normalized_request_value() -> None:
    srv, seen = _echo_server()
    net.request(srv, 'GET', '/items', None)
    assert seen == {'method': 'GET', 'path': '/items', 'body': '', 'headers': {}}


def test_request_uppercases_method() -> None:
    srv, seen = _echo_server()
    net.request(srv, 'get', '/', None)
    assert seen['method'] == 'GET'


def test_request_stringifies_method() -> None:
    srv, seen = _echo_server()
    net.request(srv, 42, '/', None)
    assert seen['method'] == '42'


def test_request_stringifies_path() -> None:
    srv, seen = _echo_server()
    net.request(srv, 'GET', 42, None)
    assert seen['path'] == '42'


def test_request_stringifies_body() -> None:
    srv, seen = _echo_server()
    net.request(srv, 'POST', '/', 123)
    assert seen['body'] == '123'


def test_request_none_body_becomes_empty_string() -> None:
    srv, seen = _echo_server()
    net.request(srv, 'POST', '/', None)
    assert seen['body'] == ''


def test_request_no_handler_returns_501() -> None:
    result = net.request(net.server(None), 'GET', '/', 'x')
    assert result == {'status': 501, 'headers': {}, 'body': 'no handler'}


def test_request_falsy_handler_returns_501() -> None:
    for falsy in (0, '', [], False):
        result = net.request(net.server(falsy), 'GET', '/', None)
        assert result == {'status': 501, 'headers': {}, 'body': 'no handler'}


def test_request_returns_handler_response() -> None:
    def handler(_req: dict[str, object]) -> dict[str, object]:
        return net.response(202, 'hi')

    result = net.request(net.server(handler), 'GET', '/', None)
    assert result == {'status': 202, 'headers': {}, 'body': 'hi'}


def test_get_delegates_with_empty_body() -> None:
    srv, seen = _echo_server()
    net.get(srv, '/x')
    assert seen['method'] == 'GET'
    assert seen['path'] == '/x'
    assert seen['body'] == ''


def test_get_stringifies_path() -> None:
    srv, seen = _echo_server()
    net.get(srv, 7)
    assert seen['path'] == '7'


def test_post_delegates_with_body() -> None:
    srv, seen = _echo_server()
    net.post(srv, '/x', 'payload')
    assert seen['method'] == 'POST'
    assert seen['path'] == '/x'
    assert seen['body'] == 'payload'


def test_post_none_body_becomes_empty_string() -> None:
    srv, seen = _echo_server()
    net.post(srv, '/x', None)
    assert seen['body'] == ''


def test_middleware_empty_returns_new_wrapper() -> None:
    def handler(_req: dict[str, object]) -> dict[str, object]:
        return net.response(200, 'ok')

    wrapped = net.middleware(handler, [])
    assert wrapped is not handler
    assert wrapped(_REQ) == handler(_REQ)


def test_middleware_single_runs_middleware_then_handler() -> None:
    log: list[str] = []

    def handler(_req: dict[str, object]) -> dict[str, object]:
        log.append('handler')
        return net.response(200, 'ok')

    def mw(req: dict[str, object], next_fn: object) -> dict[str, object]:
        log.append('mw')
        return next_fn(req)  # type: ignore[no-any-return]

    wrapped = net.middleware(handler, [mw])
    assert wrapped(_REQ) == {'status': 200, 'headers': {}, 'body': 'ok'}
    assert log == ['mw', 'handler']


def test_middleware_runs_in_list_order() -> None:
    log: list[str] = []

    def handler(_req: dict[str, object]) -> dict[str, object]:
        log.append('handler')
        return net.response(200, 'ok')

    def make(tag: str) -> object:
        def mw(req: dict[str, object], next_fn: object) -> dict[str, object]:
            log.append(tag)
            return next_fn(req)  # type: ignore[no-any-return]

        return mw

    wrapped = net.middleware(handler, [make('a'), make('b'), make('c')])
    wrapped(_REQ)
    assert log == ['a', 'b', 'c', 'handler']


def test_middleware_can_short_circuit() -> None:
    called: list[str] = []

    def handler(_req: dict[str, object]) -> dict[str, object]:
        called.append('handler')
        return net.response(200, 'ok')

    def mw(_req: dict[str, object], _next_fn: object) -> dict[str, object]:
        called.append('mw')
        return net.response(403, 'denied')

    wrapped = net.middleware(handler, [mw])
    assert wrapped(_REQ) == {'status': 403, 'headers': {}, 'body': 'denied'}
    assert called == ['mw']


def test_middleware_passes_same_request_through() -> None:
    seen: list[int] = []

    def handler(_req: dict[str, object]) -> dict[str, object]:
        return net.response(200, 'ok')

    def mw(req: dict[str, object], next_fn: object) -> dict[str, object]:
        seen.append(id(req))
        return next_fn(req)  # type: ignore[no-any-return]

    wrapped = net.middleware(handler, [mw, mw, mw])
    wrapped(_REQ)
    assert seen == [id(_REQ)] * 3


def test_middleware_response_flows_back_up() -> None:
    log: list[str] = []

    def handler(_req: dict[str, object]) -> dict[str, object]:
        log.append('handler')
        return net.response(200, 'ok')

    def make(tag: str) -> object:
        def mw(req: dict[str, object], next_fn: object) -> dict[str, object]:
            log.append(tag)
            result = next_fn(req)  # type: ignore[no-any-return]
            log.append(tag)
            return result

        return mw

    wrapped = net.middleware(handler, [make('a'), make('b')])
    assert wrapped(_REQ) == {'status': 200, 'headers': {}, 'body': 'ok'}
    assert log == ['a', 'b', 'handler', 'b', 'a']


def test_response_builds_plain_shape() -> None:
    assert net.response(404, 'nope') == {'status': 404, 'headers': {}, 'body': 'nope'}


def test_response_stringifies_body() -> None:
    assert net.response(200, 42) == {'status': 200, 'headers': {}, 'body': '42'}


def test_response_json_builds_shape() -> None:
    result = net.response_json(201, {'a': 1})
    assert result == {
        'status': 201,
        'headers': {'content-type': 'application/json'},
        'body': '{"a":1}',
    }


def test_response_json_list_body() -> None:
    result = net.response_json(200, [1, 2])
    assert result['body'] == '[1,2]'


def test_response_json_keeps_non_ascii() -> None:
    result = net.response_json(200, {'k': 'héllo'})
    assert result['body'] == '{"k":"héllo"}'


def test_response_json_roundtrips_value() -> None:
    value = {'items': [1, 2.5, True, None, 'x']}
    result = net.response_json(200, value)
    assert json.loads(result['body']) == value


def test_status_of_returns_status() -> None:
    assert net.status_of(net.response(202, 'x')) == 202


def test_status_of_none_is_zero() -> None:
    assert net.status_of(None) == 0


def test_status_of_falsy_values_is_zero() -> None:
    for falsy in ({}, [], '', 0):
        assert net.status_of(falsy) == 0


def test_body_of_returns_body() -> None:
    assert net.body_of(net.response(200, 'hi')) == 'hi'


def test_body_of_none_is_empty() -> None:
    assert net.body_of(None) == ''


def test_body_of_falsy_values_is_empty() -> None:
    for falsy in ({}, [], '', 0):
        assert net.body_of(falsy) == ''
