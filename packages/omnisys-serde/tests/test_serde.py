import binascii
import json

import omnisys_serde as serde
import pytest


def test_json_encode_returns_valid_json() -> None:
    assert json.loads(serde.json_encode({'a': 1})) == {'a': 1}
    assert json.loads(serde.json_encode([1, 'x', None, True])) == [1, 'x', None, True]


def test_json_round_trip_primitives() -> None:
    for value in ('hello', 42, 3.5, True, False, None):
        assert serde.json_decode(serde.json_encode(value)) == value


def test_json_round_trip_nested() -> None:
    value = {
        'name': 'Omni',
        'nested': {'list': [1, 2, 3], 'flag': True},
        'none': None,
    }
    assert serde.json_decode(serde.json_encode(value)) == value


def test_json_encode_keeps_non_ascii() -> None:
    assert serde.json_encode('héllo wörld') == '"héllo wörld"'
    assert serde.json_encode({'ключ': 'значение'}) == '{"ключ": "значение"}'


def test_json_decode_returns_typed_values() -> None:
    assert serde.json_decode('42') == 42
    assert serde.json_decode('3.5') == 3.5
    assert serde.json_decode('true') is True
    assert serde.json_decode('null') is None


def test_json_decode_raises_on_invalid() -> None:
    with pytest.raises(json.JSONDecodeError):
        serde.json_decode('{not json')
    with pytest.raises(json.JSONDecodeError):
        serde.json_decode('')
    with pytest.raises(json.JSONDecodeError):
        serde.json_decode('{"a": }')


def test_json_encode_raises_on_non_serializable() -> None:
    with pytest.raises(TypeError):
        serde.json_encode({1, 2})
    with pytest.raises(TypeError):
        serde.json_encode(b'bytes')


def test_csv_encode_joins_rows() -> None:
    assert serde.csv_encode([['a', 'b'], ['c', 'd']]) == 'a,b\nc,d'
    assert serde.csv_encode([['only']]) == 'only'
    assert serde.csv_encode([]) == ''


def test_csv_encode_stringifies_cells() -> None:
    assert serde.csv_encode([[1, 2.5, True, None]]) == '1,2.5,True,None'


def test_csv_decode_round_trip() -> None:
    rows = [['a', 'b'], ['c', 'd']]
    assert serde.csv_decode(serde.csv_encode(rows)) == rows


def test_csv_decode_trims_cells() -> None:
    assert serde.csv_decode('  a , b  \n c ,d ') == [['a', 'b'], ['c', 'd']]


def test_csv_decode_skips_blank_lines() -> None:
    assert serde.csv_decode('a,b\n\nc,d') == [['a', 'b'], ['c', 'd']]
    assert serde.csv_decode('a,b\n\n\nc,d\n\n') == [['a', 'b'], ['c', 'd']]


def test_csv_decode_strips_surrounding_whitespace() -> None:
    assert serde.csv_decode('  a,b  ') == [['a', 'b']]


def test_csv_decode_single_column() -> None:
    assert serde.csv_decode('a\nb\nc') == [['a'], ['b'], ['c']]


def test_to_hex_known_vectors() -> None:
    assert serde.to_hex('abc') == '616263'
    assert serde.to_hex('hello') == '68656c6c6f'
    assert serde.to_hex('') == ''


def test_to_hex_utf8() -> None:
    assert serde.to_hex('héllo') == '68c3a96c6c6f'


def test_hex_round_trip() -> None:
    assert serde.from_hex(serde.to_hex('hello world')) == 'hello world'
    assert serde.to_hex(serde.from_hex('68656c6c6f')) == '68656c6c6f'


def test_from_hex_accepts_uppercase() -> None:
    assert serde.from_hex('616263') == 'abc'
    assert serde.from_hex('E4BDA0') == '你'


def test_from_hex_empty() -> None:
    assert serde.from_hex('') == ''


def test_from_hex_accepts_separator_whitespace() -> None:
    assert serde.from_hex('61 62') == 'ab'


def test_from_hex_raises_on_bad_hex() -> None:
    with pytest.raises(ValueError):
        serde.from_hex('zz')
    with pytest.raises(ValueError):
        serde.from_hex('abc')
    with pytest.raises(ValueError):
        serde.from_hex('6 1 2')


def test_base64_known_vectors() -> None:
    assert serde.base64_encode('hello') == 'aGVsbG8='
    assert serde.base64_decode('aGVsbG8=') == 'hello'


def test_base64_round_trip_unicode() -> None:
    for text in ('', 'hello world', 'héllo wörld', '你', '🚀'):
        assert serde.base64_decode(serde.base64_encode(text)) == text


def test_base64_decode_raises_on_invalid() -> None:
    with pytest.raises(binascii.Error):
        serde.base64_decode('!!!')
    with pytest.raises(binascii.Error):
        serde.base64_decode('a')


def test_schema_validate_type_text() -> None:
    assert serde.schema_validate('x', {'type': 'text'}) is True
    assert serde.schema_validate(5, {'type': 'text'}) is False
    assert serde.schema_validate([], {'type': 'text'}) is False


def test_schema_validate_type_number() -> None:
    assert serde.schema_validate(5, {'type': 'number'}) is True
    assert serde.schema_validate(5.5, {'type': 'number'}) is True
    assert serde.schema_validate(True, {'type': 'number'}) is False
    assert serde.schema_validate('5', {'type': 'number'}) is False


def test_schema_validate_type_boolean() -> None:
    assert serde.schema_validate(True, {'type': 'boolean'}) is True
    assert serde.schema_validate(False, {'type': 'boolean'}) is True
    assert serde.schema_validate(1, {'type': 'boolean'}) is False
    assert serde.schema_validate('true', {'type': 'boolean'}) is False


def test_schema_validate_type_list() -> None:
    assert serde.schema_validate([1, 2], {'type': 'list'}) is True
    assert serde.schema_validate([], {'type': 'list'}) is True
    assert serde.schema_validate({'a': 1}, {'type': 'list'}) is False


def test_schema_validate_type_map() -> None:
    assert serde.schema_validate({'a': 1}, {'type': 'map'}) is True
    assert serde.schema_validate({}, {'type': 'map'}) is True
    assert serde.schema_validate([1, 2], {'type': 'map'}) is False
    assert serde.schema_validate('x', {'type': 'map'}) is False


def test_schema_validate_type_any() -> None:
    assert serde.schema_validate([1, 'x', None], {'type': 'any'}) is True
    assert serde.schema_validate(None, {'type': 'any'}) is True
    assert serde.schema_validate({'a': 1}, {'type': 'any'}) is True


def test_schema_validate_required_fields() -> None:
    schema = {'fields': {'name': {'type': 'text'}, 'age': {'type': 'number'}}}
    assert serde.schema_validate({'name': 'a', 'age': 3}, schema) is True
    assert serde.schema_validate({'name': 'a'}, schema) is False
    assert serde.schema_validate({'name': 'a', 'age': 'x'}, schema) is False
    assert serde.schema_validate({}, schema) is False


def test_schema_validate_nested_fields() -> None:
    schema = {
        'type': 'map',
        'fields': {'user': {'type': 'map', 'fields': {'id': {'type': 'number'}}}},
    }
    assert serde.schema_validate({'user': {'id': 1}}, schema) is True
    assert serde.schema_validate({'user': {'id': 'x'}}, schema) is False
    assert serde.schema_validate({'user': {}}, schema) is False


def test_schema_validate_fields_on_non_container() -> None:
    assert serde.schema_validate('str', {'fields': {'a': {'type': 'text'}}}) is False


def test_schema_validate_non_dict_schema() -> None:
    for bad in (None, 'text', [{'type': 'text'}], 5, True):
        assert serde.schema_validate('anything', bad) is True


def test_schema_validate_empty_and_unknown_type() -> None:
    assert serde.schema_validate({'a': 1}, {}) is True
    assert serde.schema_validate({'a': 1}, {'type': 'weird'}) is True
    assert serde.schema_validate({'a': 1}, {'type': ''}) is True
    assert serde.schema_validate({'a': 1}, {'fields': None}) is True
