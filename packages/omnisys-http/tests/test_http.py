"""Unit tests for OMNISYS.http."""

import omnisys_core as core
import omnisys_http as http
import omnisys_net as net
import pytest


@pytest.fixture(autouse=True)
def clean_module_state() -> None:
    http._REGISTRY.clear()
    http.register_transport(None)
    yield
    http._REGISTRY.clear()
    http.register_transport(None)


def test_client_shape() -> None:
    assert http.client() == {'tag': 'http.client', 'transport': 'portable'}


def test_get_via_inproc_server() -> None:
    server = net.server(lambda req: net.response(200, 'ok:' + req['path']))
    http.register('svc', server)
    res = http.get('inproc://svc/hello')
    assert res['status'] == 200
    assert res['body'] == 'ok:/hello'


def test_post_via_inproc_server() -> None:
    def handler(req: dict) -> dict:
        return net.response(200, req['method'] + ':' + req['body'])

    http.register('svc', net.server(handler))
    res = http.post('inproc://svc/items', 'data')
    assert res['body'] == 'POST:data'


def test_put_and_delete() -> None:
    def handler(req: dict) -> dict:
        return net.response(200, req['method'])

    http.register('svc', net.server(handler))
    assert http.put('inproc://svc/x', 'b')['body'] == 'PUT'
    assert http.delete('inproc://svc/x')['body'] == 'DELETE'


def test_send_dispatches_and_ignores_client() -> None:
    def handler(req: dict) -> dict:
        return net.response(200, req['method'])

    http.register('svc', net.server(handler))
    res = http.send(http.client(), 'PATCH', 'inproc://svc/x', '')
    assert res['body'] == 'PATCH'


def test_host_without_slash_defaults_to_root() -> None:
    def handler(req: dict) -> dict:
        return net.response(200, req['path'])

    http.register('svc', net.server(handler))
    assert http.get('inproc://svc')['body'] == '/'


def test_inproc_server_auto_starts() -> None:
    server = net.server(lambda req: net.response(200, 'x'))
    http.register('svc', server)
    http.get('inproc://svc/p')
    assert server['running'] is True


def test_transport_hook_receives_request() -> None:
    seen: list[tuple] = []

    def transport(method: str, url: str, body: object, timeout: float = 0) -> dict:
        seen.append((method, url, body, timeout))
        return {'status': 200, 'headers': {}, 'body': 't'}

    http.register_transport(transport)
    res = http.get('http://example.com/x')
    assert res['body'] == 't'
    assert seen == [('GET', 'http://example.com/x', None, 0)]


def test_cleared_transport_panics_for_external_scheme() -> None:
    def transport(_method: str, _url: str, _body: object) -> dict:
        return {'status': 200, 'headers': {}, 'body': 'x'}

    http.register_transport(transport)
    http.register_transport(None)
    with pytest.raises(core.PanicError):
        http.get('http://example.com/')


def test_malformed_url_panics() -> None:
    with pytest.raises(core.PanicError):
        http.get('not a url')


def test_unregistered_inproc_host_panics() -> None:
    with pytest.raises(core.PanicError):
        http.get('inproc://nope/x')


def test_json_get_parses_body() -> None:
    def handler(_req: dict) -> dict:
        return net.response_json(200, {'a': 1})

    http.register('svc', net.server(handler))
    assert http.json_get('inproc://svc/data') == {'a': 1}


def test_json_post_round_trips_value() -> None:
    def handler(req: dict) -> dict:
        return net.response_json(201, req['body'])

    http.register('svc', net.server(handler))
    assert http.json_post('inproc://svc/data', {'b': 2}) == '{"b": 2}'


def test_redirect_defaults_to_302() -> None:
    assert http.redirect('/next', None) == {
        'status': 302,
        'headers': {'location': '/next'},
        'body': '',
    }


def test_redirect_with_explicit_status() -> None:
    assert http.redirect('/next', 301)['status'] == 301


def test_redirect_coerces_location() -> None:
    assert http.redirect(7, None)['headers'] == {'location': '7'}


def test_not_found() -> None:
    assert http.not_found('missing') == {'status': 404, 'headers': {}, 'body': 'missing'}
