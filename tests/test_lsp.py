"""v4.2: minimal OmniScript LSP server - framing, handshake, diagnostics, hover."""

import io
import sys

from omni_compiler.lsp import OmniLspServer, content_length_header, read_message, write_message

VALID_SRC = """
fn pure_add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    greeting = "hello"
end
"""

INVALID_SRC = """
fn get_data(url: Text) -> Text:
    return fetch(url)
end

when app starts:
    result = get_data("http://example.com")
end
"""


def _open_doc(server, uri="file:///app.omni", text=VALID_SRC):
    return server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": uri, "text": text}},
        }
    )


def _position_of(text, needle):
    idx = text.index(needle)
    line = text.count("\n", 0, idx)
    col = idx - text.rfind("\n", 0, idx) - 1
    return {"line": line, "character": col}


# ---- framing ----


def test_content_length_header():
    assert content_length_header(10) == "Content-Length: 10\r\n\r\n"


def test_framing_roundtrip():
    msg = {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}}
    buf = io.BytesIO()
    write_message(buf, msg)
    buf.seek(0)
    assert read_message(buf) == msg


def test_read_message_eof_returns_none():
    assert read_message(io.BytesIO()) is None


def test_read_message_empty_body_returns_none():
    buf = io.BytesIO(b"Content-Length: 0\r\n\r\n")
    assert read_message(buf) is None


# ---- handshake ----


def test_initialize_returns_capabilities():
    server = OmniLspServer()
    responses = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert responses is not None
    resp = responses[0]
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert resp["result"]["capabilities"] == {"textDocumentSync": 1, "hoverProvider": True}
    assert resp["result"]["serverInfo"] == {"name": "omni-lsp", "version": "0.1.0"}


def test_initialized_is_noop():
    server = OmniLspServer()
    assert server.handle_message({"jsonrpc": "2.0", "method": "initialized", "params": {}}) == []


# ---- diagnostics ----


def test_did_open_valid_publishes_empty_diagnostics():
    server = OmniLspServer()
    responses = _open_doc(server)
    assert responses is not None
    notif = responses[0]
    assert notif["method"] == "textDocument/publishDiagnostics"
    assert notif["params"]["uri"] == "file:///app.omni"
    assert notif["params"]["diagnostics"] == []


def test_did_open_invalid_publishes_diagnostics():
    server = OmniLspServer()
    responses = _open_doc(server, text=INVALID_SRC)
    assert responses is not None
    notif = responses[0]
    diagnostics = notif["params"]["diagnostics"]
    assert len(diagnostics) >= 1
    first = diagnostics[0]
    assert first["code"] == "E-EFFECT-003"
    assert first["severity"] == 1
    assert first["source"] == "omni"
    assert "network" in first["message"]
    rng = first["range"]
    assert rng["start"]["line"] >= 0
    assert rng["start"]["character"] >= 0


def test_did_open_syntax_error_publishes_syntax_diagnostic():
    server = OmniLspServer()
    responses = _open_doc(server, text="fn broken:\n    x = \nend\n")
    assert responses is not None
    diagnostics = responses[0]["params"]["diagnostics"]
    assert len(diagnostics) >= 1
    assert diagnostics[0]["code"] == "E-SYNTAX-001"


def test_did_open_name_error_publishes_name_diagnostic():
    server = OmniLspServer()
    responses = _open_doc(server, text="when app starts:\n    y = undefined_thing\nend\n")
    assert responses is not None
    diagnostics = responses[0]["params"]["diagnostics"]
    assert len(diagnostics) >= 1
    assert diagnostics[0]["code"] == "E-NAME-001"


# ---- hover ----


def test_hover_known_symbol_returns_markdown():
    server = OmniLspServer()
    _open_doc(server)
    pos = _position_of(VALID_SRC, "pure_add")
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {"textDocument": {"uri": "file:///app.omni"}, "position": pos},
        }
    )
    assert responses is not None
    resp = responses[0]
    assert resp["id"] == 2  # noqa: PLR2004
    contents = resp["result"]["contents"]
    assert contents["kind"] == "markdown"
    assert "pure_add" in contents["value"]


def test_hover_unknown_symbol_returns_empty():
    server = OmniLspServer()
    _open_doc(server)
    pos = _position_of(VALID_SRC, "greeting")
    pos["character"] = 0  # point at leading whitespace -> no identifier
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {"textDocument": {"uri": "file:///app.omni"}, "position": pos},
        }
    )
    assert responses is not None
    assert responses[0]["result"]["contents"]["value"] == ""


def test_hover_on_valid_identifier_not_in_table_returns_empty():
    server = OmniLspServer()
    _open_doc(server)
    pos = _position_of(VALID_SRC, "pure_add")
    pos["line"] = 0  # point at 'fn' keyword, not a symbol table entry
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "textDocument/hover",
            "params": {"textDocument": {"uri": "file:///app.omni"}, "position": pos},
        }
    )
    assert responses is not None
    assert responses[0]["result"]["contents"]["value"] == ""


def test_hover_out_of_range_line_returns_empty():
    server = OmniLspServer()
    _open_doc(server)
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///app.omni"},
                "position": {"line": 999, "character": 0},
            },
        }
    )
    assert responses is not None
    assert responses[0]["result"]["contents"]["value"] == ""


def test_hover_out_of_range_character_returns_empty():
    server = OmniLspServer()
    _open_doc(server)
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///app.omni"},
                "position": {"line": 0, "character": 999},
            },
        }
    )
    assert responses is not None
    assert responses[0]["result"]["contents"]["value"] == ""


def test_unknown_method_with_id_returns_null():
    server = OmniLspServer()
    responses = server.handle_message(
        {"jsonrpc": "2.0", "id": 8, "method": "textDocument/unknown", "params": {}}
    )
    assert responses is not None
    assert responses[0]["result"] is None


def test_unknown_notification_returns_none():
    server = OmniLspServer()
    msg = {"jsonrpc": "2.0", "method": "some/notification", "params": {}}
    assert server.handle_message(msg) is None


def test_hover_on_unopened_document_returns_empty():
    server = OmniLspServer()
    responses = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///nope.omni"},
                "position": {"line": 0, "character": 0},
            },
        }
    )
    assert responses is not None
    assert responses[0]["result"]["contents"]["value"] == ""


# ---- shutdown / exit / run loop ----


def test_shutdown_returns_null():
    server = OmniLspServer()
    responses = server.handle_message(
        {"jsonrpc": "2.0", "id": 9, "method": "shutdown", "params": {}}
    )
    assert responses is not None
    assert responses[0]["id"] == 9  # noqa: PLR2004
    assert responses[0]["result"] is None


def test_exit_returns_none():
    server = OmniLspServer()
    assert server.handle_message({"jsonrpc": "2.0", "method": "exit"}) is None


class _FakeStream:
    def __init__(self, buf):
        self.buffer = buf


def test_run_loop_serves_request_then_exits(monkeypatch):
    incoming = io.BytesIO()
    write_message(incoming, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    write_message(incoming, {"jsonrpc": "2.0", "method": "exit"})
    incoming.seek(0)
    outgoing = io.BytesIO()
    monkeypatch.setattr(sys, "stdin", _FakeStream(incoming))
    monkeypatch.setattr(sys, "stdout", _FakeStream(outgoing))
    OmniLspServer().run()
    outgoing.seek(0)
    resp = read_message(outgoing)
    assert resp["id"] == 1
    assert resp["result"]["capabilities"] == {"textDocumentSync": 1, "hoverProvider": True}


def test_run_loop_stops_at_eof(monkeypatch):
    incoming = io.BytesIO()
    incoming.seek(0)
    outgoing = io.BytesIO()
    monkeypatch.setattr(sys, "stdin", _FakeStream(incoming))
    monkeypatch.setattr(sys, "stdout", _FakeStream(outgoing))
    OmniLspServer().run()
    assert outgoing.getvalue() == b""
