"""v4.2: minimal OmniScript Language Server Protocol implementation (stdlib only)."""

import json
import sys
from typing import Any, BinaryIO, cast

from omni_compiler.checker import DiagnosticError, SymbolTable, analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse

SERVER_NAME = 'omni-lsp'
SERVER_VERSION = '0.1.0'


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


def content_length_header(body_len: int) -> str:
    """Build the LSP Content-Length framing header for a message body."""
    return f'Content-Length: {body_len}\r\n\r\n'


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    """Read a Content-Length framed JSON-RPC message, or None at EOF."""
    headers: dict[bytes, bytes] = {}
    while True:
        raw = stream.readline()
        if not raw:
            return None
        raw = raw.rstrip(b'\r\n')
        if not raw:
            break
        key, _, value = raw.partition(b':')
        headers[key.strip().lower()] = value.strip()
    raw_length = headers.get(b'content-length', b'0')
    body = stream.read(int(raw_length))
    if not body:
        return None
    return cast(dict[str, Any], json.loads(body))


def write_message(stream: BinaryIO, msg: dict[str, Any]) -> None:
    """Write a JSON-RPC message to a stream using Content-Length framing."""
    body = json.dumps(msg).encode('utf-8')
    header = content_length_header(len(body)).encode('ascii')
    stream.write(header + body)
    stream.flush()


def _diagnostic_to_lsp(d: dict[str, Any]) -> dict[str, Any]:
    loc = d.get('location') or {'line': 1, 'column': 1}
    line = max(int(loc.get('line', 1)) - 1, 0)
    column = max(int(loc.get('column', 1)) - 1, 0)
    return {
        'range': {
            'start': {'line': line, 'character': column},
            'end': {'line': line, 'character': column},
        },
        'severity': 1,
        'code': d.get('code', ''),
        'message': d.get('message', ''),
        'source': 'omni',
    }


def _identifier_at(text: str, line: int, character: int) -> str | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    content = lines[line]
    if character < 0 or character > len(content):
        return None
    start = character
    while start > 0 and (content[start - 1].isalnum() or content[start - 1] in '_.'):
        start -= 1
    end = character
    while end < len(content) and (content[end].isalnum() or content[end] in '_.'):
        end += 1
    token = content[start:end]
    if not token or not (token[0].isalpha() or token[0] == '_'):
        return None
    return token


class OmniLspServer:
    """Minimal LSP server exposing OmniScript diagnostics and hover support."""

    def __init__(self) -> None:
        """Create a server with no open documents."""
        self._docs: dict[str, dict[str, Any]] = {}
        self._exiting = False

    def _response(self, msg_id: Any, result: Any) -> dict[str, Any]:
        return {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    def _notification(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {'jsonrpc': '2.0', 'method': method, 'params': params}

    def _analyze_document(self, text: str) -> tuple[list[dict[str, Any]], SymbolTable | None]:
        try:
            ast = parse(tokenize(text))
            table = analyze(ast)
            return [], table
        except Exception as e:
            diagnostic = _diagnostic_from_exception(e)
            return [_diagnostic_to_lsp(diagnostic)], None

    def _hover(self, uri: str, line: int, character: int) -> dict[str, Any]:
        doc = self._docs.get(uri)
        if doc is None:
            return {'kind': 'markdown', 'value': ''}
        ident = _identifier_at(str(doc['text']), line, character)
        table = doc['symbol_table']
        if ident is None or table is None:
            return {'kind': 'markdown', 'value': ''}
        symbol = table.inspect_symbol(ident)
        if symbol is None:
            return {'kind': 'markdown', 'value': ''}
        value = f'**{symbol["name"]}**\n\n- kind: {symbol["kind"]}\n- type: {symbol["type"]}'
        return {'kind': 'markdown', 'value': value}

    def handle_message(self, msg: dict[str, Any]) -> list[dict[str, Any]] | None:
        """Handle one JSON-RPC message; return responses/notifications to send."""
        method = msg.get('method')
        msg_id = msg.get('id')
        result: list[dict[str, Any]] | None
        if method == 'initialize':
            result = [
                self._response(
                    msg_id,
                    {
                        'capabilities': {'textDocumentSync': 1, 'hoverProvider': True},
                        'serverInfo': {'name': SERVER_NAME, 'version': SERVER_VERSION},
                    },
                )
            ]
        elif method == 'initialized':
            result = []
        elif method == 'textDocument/didOpen':
            params = msg.get('params') or {}
            text_document = params.get('textDocument') or {}
            uri = str(text_document.get('uri', ''))
            text = str(text_document.get('text', ''))
            diagnostics, table = self._analyze_document(text)
            self._docs[uri] = {'text': text, 'symbol_table': table}
            result = [
                self._notification(
                    'textDocument/publishDiagnostics',
                    {'uri': uri, 'diagnostics': diagnostics},
                )
            ]
        elif method == 'textDocument/hover':
            params = msg.get('params') or {}
            text_document = params.get('textDocument') or {}
            position = params.get('position') or {}
            uri = str(text_document.get('uri', ''))
            line = int(position.get('line', 0))
            character = int(position.get('character', 0))
            contents = self._hover(uri, line, character)
            result = [self._response(msg_id, {'contents': contents})]
        elif method == 'shutdown':
            result = [self._response(msg_id, None)]
        elif method == 'exit':
            self._exiting = True
            result = None
        elif msg_id is not None:
            result = [self._response(msg_id, None)]
        else:
            result = None
        return result

    def run(self) -> None:
        """Serve requests from stdin until an exit message or EOF."""
        stdin = cast(BinaryIO, sys.stdin.buffer)
        stdout = cast(BinaryIO, sys.stdout.buffer)
        while not self._exiting:
            msg = read_message(stdin)
            if msg is None:
                break
            outputs = self.handle_message(msg)
            if outputs:
                for out in outputs:
                    write_message(stdout, out)


if __name__ == '__main__':
    OmniLspServer().run()
