"""Property-based tests for OMNISYS.http."""

import json

import omnisys_http as http
import omnisys_net as net
from hypothesis import given, settings
from hypothesis import strategies as st

_ALPHABET = 'abcdefghijklmnopqrstuvwxyz'


@given(st.text(alphabet=_ALPHABET, min_size=1, max_size=12))
def test_inproc_host_round_trip(host: str) -> None:
    def handler(req: dict) -> dict:
        return net.response(200, req['path'])

    http._REGISTRY.clear()
    http.register(host, net.server(handler))
    res = http.get('inproc://' + host + '/x')
    assert res['status'] == 200
    assert res['body'] == '/x'


@settings(max_examples=50)
@given(
    st.one_of(
        st.integers(),
        st.text(),
        st.booleans(),
        st.lists(st.integers(), max_size=5),
        st.none(),
    )
)
def test_json_post_echo_round_trip(value: object) -> None:
    def handler(req: dict) -> dict:
        return net.response_json(200, req['body'])

    http.register('svc', net.server(handler))
    assert http.json_post('inproc://svc/data', value) == json.dumps(value)


@given(st.text(), st.integers(min_value=100, max_value=599))
def test_redirect_shape(location: str, status: int) -> None:
    res = http.redirect(location, status)
    assert res['status'] == status
    assert res['headers'] == {'location': location}
    assert res['body'] == ''
