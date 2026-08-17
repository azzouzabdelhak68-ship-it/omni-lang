import re
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    TEXT = "TEXT"
    UI_CONTENT = "UI_CONTENT"
    TRUE = "TRUE"
    FALSE = "FALSE"
    NONE = "NONE"
    
    # Keywords
    WHEN = "when"
    END = "end"
    IF = "if"
    ELSE = "else"
    THEN = "then"
    FN = "fn"
    RETURN = "return"
    SHOW = "show"
    USES = "uses"
    READS = "reads"
    WRITES = "writes"
    PURE = "pure"
    UI = "UI"
    SCENE = "scene"
    REQUIRE = "require"
    ENSURE = "ensure"
    AND = "and"
    OR = "or"
    NOT = "not"
    IS = "is"
    TYPE = "type"
    FOR = "for"
    IN = "in"
    BREAK = "break"
    CONTINUE = "continue"
    IMPORT = "import"

    # 3D scene shape keywords
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    PLANE = "plane"
    LIGHT = "light"
    CAMERA = "camera"
    
    # Symbols & Operators
    COLON = "COLON"
    ASSIGN = "ASSIGN"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    ARROW = "ARROW"
    GREATER = "GREATER"
    LESS = "LESS"
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"
    COMMA = "COMMA"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    DOT = "DOT"
    
    EOF = "EOF"

keyword_map = {
    "when": TokenType.WHEN,
    "end": TokenType.END,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "then": TokenType.THEN,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "show": TokenType.SHOW,
    "uses": TokenType.USES,
    "reads": TokenType.READS,
    "writes": TokenType.WRITES,
    "pure": TokenType.PURE,
    "UI": TokenType.UI,
    "scene": TokenType.SCENE,
    "require": TokenType.REQUIRE,
    "ensure": TokenType.ENSURE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "is": TokenType.IS,
    "type": TokenType.TYPE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "import": TokenType.IMPORT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "none": TokenType.NONE,
    "box": TokenType.BOX,
    "sphere": TokenType.SPHERE,
    "cylinder": TokenType.CYLINDER,
    "plane": TokenType.PLANE,
    "light": TokenType.LIGHT,
    "camera": TokenType.CAMERA,
}

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    span_start: int
    span_end: int

def tokenize(code: str) -> list[Token]:
    tokens = []
    line = 1
    column = 1
    pos = 0
    length = len(code)
    
    patterns = [
        ("COMMENT", r"#[^\r\n]*"),
        ("ARROW", r"->"),
        ("GREATER_OR_EQUAL", r">="),
        ("LESS_OR_EQUAL", r"<="),
        ("GREATER", r">"),
        ("LESS", r"<"),
        ("DOT", r"\."),
        ("COLON", r":"),
        ("ASSIGN", r"="),
        ("PLUS", r"\+"),
        ("MINUS", r"-"),
        ("MULTIPLY", r"\*"),
        ("DIVIDE", r"/"),
        ("COMMA", r","),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACKET", r"\["),
        ("RBRACKET", r"\]"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("NUMBER", r"\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"),
        ("TEXT", r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("WHITESPACE", r"[ \t\r\n]+"),
    ]
    
    master_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in patterns)
    compiled = re.compile(master_regex, re.DOTALL)
    
    while pos < length:
        # Check ahead for UI: block special handling
        if code.startswith("UI", pos):
            look_pos = pos + 2
            while look_pos < length and code[look_pos] in " \t\r\n":
                look_pos += 1
            if look_pos < length and code[look_pos] == ":":
                # UI block detected
                tokens.append(Token(TokenType.UI, "UI", line, column, pos, pos + 2))
                pos = look_pos + 1
                column += (pos - pos) # adjust column if needed
                tokens.append(Token(TokenType.COLON, ":", line, column, look_pos, look_pos + 1))
                
                # Consume until 'end'
                html_start = pos
                end_match = re.search(r"\n\s*end\b", code[pos:])
                if end_match:
                    html_end = pos + end_match.start()
                    html_text = code[pos:html_end]
                    for ch in html_text:
                        if ch == "\n":
                            line += 1
                            column = 1
                        else:
                            column += 1
                    tokens.append(Token(TokenType.UI_CONTENT, html_text, line, column, html_start, html_end))
                    pos = html_end
                else:
                    raise SyntaxError("Unterminated UI block: missing 'end'")
                continue

        match = compiled.match(code, pos)
        if not match:
            raise SyntaxError(f"Unexpected character '{code[pos]}' at line {line}, column {column}")
        
        kind = match.lastgroup
        value = match.group(kind)
        span_start = pos
        span_end = pos + len(value)
        
        token_line = line
        token_col = column
        
        for ch in value:
            if ch == "\n":
                line += 1
                column = 1
            else:
                column += 1
        pos = span_end
        
        if kind == "WHITESPACE" or kind == "COMMENT":
            continue
        if kind == "COLON":
            tokens.append(Token(TokenType.COLON, value, token_line, token_col, span_start, span_end))
        elif kind == "ASSIGN":
            tokens.append(Token(TokenType.ASSIGN, value, token_line, token_col, span_start, span_end))
        elif kind == "PLUS":
            tokens.append(Token(TokenType.PLUS, value, token_line, token_col, span_start, span_end))
        elif kind == "MINUS":
            tokens.append(Token(TokenType.MINUS, value, token_line, token_col, span_start, span_end))
        elif kind == "MULTIPLY":
            tokens.append(Token(TokenType.MULTIPLY, value, token_line, token_col, span_start, span_end))
        elif kind == "DIVIDE":
            tokens.append(Token(TokenType.DIVIDE, value, token_line, token_col, span_start, span_end))
        elif kind == "ARROW":
            tokens.append(Token(TokenType.ARROW, value, token_line, token_col, span_start, span_end))
        elif kind == "GREATER_OR_EQUAL":
            tokens.append(Token(TokenType.GREATER_OR_EQUAL, value, token_line, token_col, span_start, span_end))
        elif kind == "LESS_OR_EQUAL":
            tokens.append(Token(TokenType.LESS_OR_EQUAL, value, token_line, token_col, span_start, span_end))
        elif kind == "GREATER":
            tokens.append(Token(TokenType.GREATER, value, token_line, token_col, span_start, span_end))
        elif kind == "LESS":
            tokens.append(Token(TokenType.LESS, value, token_line, token_col, span_start, span_end))
        elif kind == "COMMA":
            tokens.append(Token(TokenType.COMMA, value, token_line, token_col, span_start, span_end))
        elif kind == "LPAREN":
            tokens.append(Token(TokenType.LPAREN, value, token_line, token_col, span_start, span_end))
        elif kind == "RPAREN":
            tokens.append(Token(TokenType.RPAREN, value, token_line, token_col, span_start, span_end))
        elif kind == "LBRACKET":
            tokens.append(Token(TokenType.LBRACKET, value, token_line, token_col, span_start, span_end))
        elif kind == "RBRACKET":
            tokens.append(Token(TokenType.RBRACKET, value, token_line, token_col, span_start, span_end))
        elif kind == "LBRACE":
            tokens.append(Token(TokenType.LBRACE, value, token_line, token_col, span_start, span_end))
        elif kind == "RBRACE":
            tokens.append(Token(TokenType.RBRACE, value, token_line, token_col, span_start, span_end))
        elif kind == "DOT":
            tokens.append(Token(TokenType.DOT, value, token_line, token_col, span_start, span_end))
        elif kind == "NUMBER":
            tokens.append(Token(TokenType.NUMBER, value, token_line, token_col, span_start, span_end))
        elif kind == "TEXT":
            tokens.append(Token(TokenType.TEXT, value, token_line, token_col, span_start, span_end))
        elif kind == "IDENTIFIER":
            if value in ("greater", "less"):
                rest = code[span_end:]
                stripped = rest.lstrip(" \t")
                if value == "greater":
                    if stripped.startswith("or equal"):
                        tokens.append(Token(TokenType.GREATER_OR_EQUAL, "greater or equal", token_line, token_col, span_start, span_end + len("greater") + len(stripped[:len("or equal")])))
                        pos += len(rest) - len(stripped) + len("or equal")
                        for ch in rest[:len(rest) - len(stripped) + len("or equal")]:
                            if ch == "\n":
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                    if stripped.startswith("than"):
                        tokens.append(Token(TokenType.GREATER, "greater than", token_line, token_col, span_start, span_end + len("greater") + len(stripped[:len("than")])))
                        pos += len(rest) - len(stripped) + len("than")
                        for ch in rest[:len(rest) - len(stripped) + len("than")]:
                            if ch == "\n":
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                if value == "less":
                    if stripped.startswith("or equal"):
                        tokens.append(Token(TokenType.LESS_OR_EQUAL, "less or equal", token_line, token_col, span_start, span_end + len("less") + len(stripped[:len("or equal")])))
                        pos += len(rest) - len(stripped) + len("or equal")
                        for ch in rest[:len(rest) - len(stripped) + len("or equal")]:
                            if ch == "\n":
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                    if stripped.startswith("than"):
                        tokens.append(Token(TokenType.LESS, "less than", token_line, token_col, span_start, span_end + len("less") + len(stripped[:len("than")])))
                        pos += len(rest) - len(stripped) + len("than")
                        for ch in rest[:len(rest) - len(stripped) + len("than")]:
                            if ch == "\n":
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
            if value in keyword_map:
                tokens.append(Token(keyword_map[value], value, token_line, token_col, span_start, span_end))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, value, token_line, token_col, span_start, span_end))
                
    tokens.append(Token(TokenType.EOF, "", line, column, pos, pos))
    return tokens
