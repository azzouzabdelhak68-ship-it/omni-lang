"""OMNISYS.serde — JSON, CSV, hex, base64, and schema validation.

Python reference implementation of the OMNISYS ``serde`` module (v6). It
mirrors the JS reference implementation in ``omnisys/serde.js`` and satisfies
the registry contract declared in ``omni_compiler/omnisys_registry.py``: all
nine functions are pure and depend only on the Python standard library.
"""

import base64
import json
from typing import Any

__all__ = [
    'json_encode',
    'json_decode',
    'csv_encode',
    'csv_decode',
    'to_hex',
    'from_hex',
    'base64_encode',
    'base64_decode',
    'schema_validate',
]


def json_encode(value: Any) -> str:
    """Serialize ``value`` to a JSON text.

    Uses ``ensure_ascii=False`` so non-ASCII characters are emitted verbatim,
    matching JavaScript ``JSON.stringify`` which never escapes them. Raises
    ``TypeError`` for values that are not JSON-serializable (sets, bytes,
    cyclic structures, and so on).
    """
    return json.dumps(value, ensure_ascii=False)


def json_decode(text: str) -> Any:
    """Parse the JSON ``text`` and return the decoded Python value.

    Raises ``json.JSONDecodeError`` when ``text`` is not valid JSON; this
    mirrors the JS reference, which throws on a failed ``JSON.parse``.
    """
    return json.loads(text)


def csv_encode(rows: list[list[Any]]) -> str:
    """Serialize ``rows`` to CSV text with one line per row.

    Cells are joined with commas and rows with newlines; every cell is
    stringified with ``str`` exactly as the JS ``String(cell)`` does. No
    quoting or escaping is applied, so a cell containing a comma or newline
    breaks the round-trip (a documented limitation inherited from JS).
    """
    return '\n'.join(','.join(str(cell) for cell in row) for row in rows)


def csv_decode(text: str) -> list[list[str]]:
    """Parse the CSV ``text`` into a list of rows of string cells.

    Mirrors the JS reference exactly: the whole text is stripped, split on
    newlines, blank lines are dropped, and every cell is trimmed. Cells are
    always strings, matching JS which never type-coerces them back.
    """
    return [[cell.strip() for cell in line.split(',')] for line in text.strip().split('\n') if line]


def to_hex(text: str) -> str:
    """Encode ``text`` as lowercase hexadecimal of its UTF-8 bytes.

    Produces two lowercase hex digits per byte. For ASCII input this agrees
    with the JS reference, which encodes UTF-16 code units; for non-ASCII
    input the two encodings diverge (see RESEARCH.md for the rationale).
    """
    return text.encode('utf-8').hex()


def from_hex(hex_text: str) -> str:
    """Decode the hexadecimal ``hex_text`` back into text (UTF-8).

    Raises ``ValueError`` when ``hex_text`` is not valid hexadecimal (odd
    length or non-hex characters) and ``UnicodeDecodeError`` when the decoded
    bytes are not valid UTF-8. Note that ``bytes.fromhex`` also accepts
    upper-case digits and ASCII whitespace between bytes, unlike the JS
    reference which would silently misparse such input.
    """
    return bytes.fromhex(hex_text).decode('utf-8')


def base64_encode(text: str) -> str:
    """Encode ``text`` to standard base64 using its UTF-8 bytes.

    Uses the UTF-8 ``TextEncoder`` semantics of the JS reference so both
    lanes produce identical output for any Unicode input.
    """
    return base64.b64encode(text.encode('utf-8')).decode('ascii')


def base64_decode(b64: str) -> str:
    """Decode the base64 ``b64`` back into text (UTF-8).

    Raises ``binascii.Error`` (a ``ValueError`` subclass) when ``b64`` is not
    valid base64; ``validate=True`` rejects non-alphabet characters, mirroring
    the JS ``atob`` throw. UTF-8 decoding failures raise
    ``UnicodeDecodeError``.
    """
    return base64.b64decode(b64, validate=True).decode('utf-8')


def schema_validate(value: Any, schema: Any) -> bool:
    """Validate ``value`` against ``schema``, returning True on a match.

    ``schema`` is a dict; any non-dict schema validates everything to True
    (mirrors JS). A ``type`` key supports ``any``, ``text``, ``number``,
    ``boolean``, ``list`` and ``map``; unknown type names pass. A ``fields``
    dict requires every key to be present in ``value`` and recursively
    validated against its sub-schema.
    """
    if not isinstance(schema, dict):
        return True
    type_name = schema.get('type')
    if type_name and not _type_matches(value, type_name):
        return False
    fields = schema.get('fields')
    if isinstance(fields, dict):
        for key, sub_schema in fields.items():
            if key not in value:
                return False
            if not schema_validate(value[key], sub_schema):
                return False
    return True


def _type_matches(actual: Any, expected: Any) -> bool:
    if expected == 'any':
        result = True
    elif expected == 'text':
        result = isinstance(actual, str)
    elif expected == 'number':
        result = isinstance(actual, (int, float)) and not isinstance(actual, bool)
    elif expected == 'boolean':
        result = isinstance(actual, bool)
    elif expected == 'list':
        result = isinstance(actual, list)
    elif expected == 'map':
        result = isinstance(actual, dict) and not isinstance(actual, list)
    else:
        result = True
    return result
