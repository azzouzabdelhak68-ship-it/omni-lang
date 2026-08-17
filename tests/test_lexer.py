from omni_compiler.lexer import TokenType, tokenize


def test_lexer_keywords_and_colon():
    code = 'when app starts:\nend\nUI:\n<h1>Hello</h1>\nend\nscene:\nbox size="2"\nend'
    tokens = tokenize(code)
    values = [t.value for t in tokens if t.type != TokenType.EOF]
    assert "when" in values
    assert "app" in values
    assert "starts" in values
    assert "UI" in values
    assert "scene" in values
    assert ":" in values
    assert "end" in values
    
    colon_tokens = [t for t in tokens if t.type == TokenType.COLON]
    assert len(colon_tokens) == 3

def test_lexer_literals_and_operators():
    code = 'x = 42 + 3.14 - "hello {name}" * [1, 2] / none true false is not -> , ( ) [ ] { }'
    tokens = tokenize(code)
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.IDENTIFIER in types
    assert TokenType.ASSIGN in types
    assert TokenType.NUMBER in types
    assert TokenType.PLUS in types
    assert TokenType.MINUS in types
    assert TokenType.TEXT in types
    assert TokenType.MULTIPLY in types
    assert TokenType.LBRACKET in types
    assert TokenType.RBRACKET in types
    assert TokenType.DIVIDE in types
    assert TokenType.NONE in types
    assert TokenType.TRUE in types
    assert TokenType.FALSE in types
    assert TokenType.IS in types
    assert TokenType.NOT in types
    assert TokenType.ARROW in types

def test_lexer_comments():
    code = "# comment line\nx = 10"
    tokens = tokenize(code)
    values = [t.value for t in tokens if t.type != TokenType.EOF]
    assert "comment" not in values
    assert values == ["x", "=", "10"]
