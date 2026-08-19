"""Unit tests for OMNISYS.tool."""

from __future__ import annotations

import subprocess

import omnisys_tool as tool


def test_tokenize_keywords() -> None:
    tokens = tool.tokenize('when end if else then')
    assert all(token['kind'] == 'keyword' for token in tokens)
    assert [token['value'] for token in tokens] == ['when', 'end', 'if', 'else', 'then']


def test_tokenize_identifiers() -> None:
    tokens = tool.tokenize('foo bar _baz count1')
    assert all(token['kind'] == 'identifier' for token in tokens)
    assert len(tokens) == 4


def test_tokenize_numbers() -> None:
    tokens = tool.tokenize('1 2.5 100')
    assert all(token['kind'] == 'number' for token in tokens)


def test_tokenize_text() -> None:
    tokens = tool.tokenize('"hello" \'world\'')
    assert all(token['kind'] == 'text' for token in tokens)
    assert tokens[0]['value'] == '"hello"'
    assert tokens[1]['value'] == "'world'"


def test_tokenize_operators() -> None:
    tokens = tool.tokenize('=> >= <= = + * , .')
    values = [token['value'] for token in tokens]
    assert values == [
        '=>',
        '>=',
        '<=',
        '=',
        '+',
        '*',
        ',',
        '.',
    ]


def test_tokenize_skips_whitespace() -> None:
    tokens = tool.tokenize('  foo   bar\t\n')
    assert len(tokens) == 2


def test_tokenize_keyword_precedence() -> None:
    tokens = tool.tokenize('show when')
    assert tokens[0]['kind'] == 'keyword'
    assert tokens[1]['kind'] == 'keyword'


def test_tokenize_coerces_input_to_string() -> None:
    assert tool.tokenize(42) == [{'value': '42', 'kind': 'number'}]


def test_tokenize_mixed_program() -> None:
    code = 'fn add(a: Number) -> Number: return a + 1 end'
    tokens = tool.tokenize(code)
    kinds = [token['kind'] for token in tokens]
    assert kinds == [
        'keyword',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'identifier',
        'keyword',
        'identifier',
        'identifier',
        'number',
        'keyword',
    ]


def test_line_count_single_line() -> None:
    assert tool.line_count('hello') == 1


def test_line_count_empty() -> None:
    assert tool.line_count('') == 1


def test_line_count_multi_line() -> None:
    assert tool.line_count('a\nb\nc') == 3


def test_line_count_trailing_newline() -> None:
    assert tool.line_count('a\nb\n') == 3


def test_line_count_coerces() -> None:
    assert tool.line_count(42) == 1


def test_identifier_count() -> None:
    code = 'show foo; show bar'
    assert tool.identifier_count(code) == 2


def test_identifier_count_ignores_keywords() -> None:
    assert tool.identifier_count('when app starts') == 2


def test_identifier_count_empty() -> None:
    assert tool.identifier_count('') == 0


def test_check_ok_on_valid_file(tmp_path) -> None:
    valid = tmp_path / 'valid.omni'
    valid.write_text('when app starts:\n    show "hi"\nend\n', encoding='utf-8')
    result = tool.check(str(valid))
    assert result['path'] == str(valid)
    assert result['ok'] is True


def test_check_error_on_invalid_file(tmp_path) -> None:
    invalid = tmp_path / 'invalid.omni'
    invalid.write_text('when app starts:\n    show undefined_name\nend\n', encoding='utf-8')
    result = tool.check(str(invalid))
    assert result['ok'] is False
    assert result['diagnostic'] is not None
    assert 'code' in result['diagnostic']


def test_explain_ok_on_valid_file(tmp_path) -> None:
    valid = tmp_path / 'valid.omni'
    valid.write_text('when app starts:\n    show "hi"\nend\n', encoding='utf-8')
    result = tool.explain(str(valid))
    assert result['ok'] is True


def test_explain_error_on_invalid_file(tmp_path) -> None:
    invalid = tmp_path / 'invalid.omni'
    invalid.write_text('fn broken(:\nend\n', encoding='utf-8')
    result = tool.explain(str(invalid))
    assert result['ok'] is False
    assert result['diagnostic'] is not None


def test_check_fallback_on_oserror(monkeypatch, tmp_path) -> None:
    def boom(*_args, **_kwargs):
        raise OSError('no python')

    monkeypatch.setattr(subprocess, 'run', boom)
    result = tool.check(str(tmp_path / 'x.omni'))
    assert result['ok'] is False
    assert result['diagnostic'] is None
    assert result['stderr'] != ''


def test_check_fallback_on_timeout(monkeypatch, tmp_path) -> None:
    def slow(*_args, **_kwargs):
        raise subprocess.TimeoutExpired('omni', timeout=15)

    monkeypatch.setattr(subprocess, 'run', slow)
    result = tool.check(str(tmp_path / 'x.omni'))
    assert result['ok'] is False
    assert result['diagnostic'] is None
    assert result['stderr'] != ''
