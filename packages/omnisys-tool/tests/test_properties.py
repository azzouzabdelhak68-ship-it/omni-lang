"""Property tests for OMNISYS.tool."""

from __future__ import annotations

import omnisys_tool as tool
from hypothesis import given
from hypothesis import strategies as st

_SIMPLE = st.text(alphabet='abcdefghijklmnopqrstuvwxyz_', max_size=32)
_PROG = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789 +-*.,()[]\n\t', max_size=64)


@given(_SIMPLE)
def test_tokenize_identifiers_have_no_whitespace(word: str) -> None:
    tokens = tool.tokenize(word)
    assert all(not token['value'].isspace() for token in tokens)


@given(_PROG)
def test_tokenize_never_returns_whitespace(code: str) -> None:
    tokens = tool.tokenize(code)
    assert all(not token['value'].isspace() for token in tokens)


@given(st.text(max_size=64))
def test_tokenize_kinds_are_known(code: str) -> None:
    kinds = {token['kind'] for token in tool.tokenize(code)}
    assert kinds <= {'keyword', 'number', 'text', 'identifier'}


@given(st.text(max_size=64))
def test_line_count_matches_newlines(code: str) -> None:
    assert tool.line_count(code) == code.count('\n') + 1


@given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', max_size=64))
def test_identifier_count_nonnegative(code: str) -> None:
    assert tool.identifier_count(code) >= 0


@given(_PROG)
def test_identifier_count_equals_filtered_tokens(code: str) -> None:
    expected = sum(1 for token in tool.tokenize(code) if token['kind'] == 'identifier')
    assert tool.identifier_count(code) == expected
