"""Lexical analysis for OmniScript source code."""

import re
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Types of tokens produced by the OmniScript lexer."""

    IDENTIFIER = 'IDENTIFIER'
    NUMBER = 'NUMBER'
    TEXT = 'TEXT'
    UI_CONTENT = 'UI_CONTENT'
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    NONE = 'NONE'

    # Keywords
    WHEN = 'when'
    END = 'end'
    IF = 'if'
    ELSE = 'else'
    THEN = 'then'
    FN = 'fn'
    RETURN = 'return'
    SHOW = 'show'
    USES = 'uses'
    READS = 'reads'
    WRITES = 'writes'
    PURE = 'pure'
    BORROWS = 'borrows'
    UI = 'UI'
    SCENE = 'scene'
    REQUIRE = 'require'
    ENSURE = 'ensure'
    AND = 'and'
    OR = 'or'
    NOT = 'not'
    IS = 'is'
    TYPE = 'type'
    FOR = 'for'
    IN = 'in'
    BREAK = 'break'
    CONTINUE = 'continue'
    IMPORT = 'import'
    WHILE = 'while'
    TRY = 'try'
    CATCH = 'catch'
    FINALLY = 'finally'
    ON = 'on'
    AWAIT = 'await'
    GLOBAL = 'global'

    # 3D scene shape keywords
    BOX = 'box'
    SPHERE = 'sphere'
    CYLINDER = 'cylinder'
    PLANE = 'plane'
    LIGHT = 'light'
    CAMERA = 'camera'

    # Symbols & Operators
    COLON = 'COLON'
    ASSIGN = 'ASSIGN'
    PLUS = 'PLUS'
    MINUS = 'MINUS'
    MULTIPLY = 'MULTIPLY'
    DIVIDE = 'DIVIDE'
    MODULO = 'MODULO'
    ARROW = 'ARROW'
    GREATER = 'GREATER'
    LESS = 'LESS'
    GREATER_OR_EQUAL = 'GREATER_OR_EQUAL'
    LESS_OR_EQUAL = 'LESS_OR_EQUAL'
    COMMA = 'COMMA'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    LBRACKET = 'LBRACKET'
    RBRACKET = 'RBRACKET'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    DOT = 'DOT'

    # Shorthand / agent mode operators
    FAT_ARROW = 'FAT_ARROW'
    PIPE = 'PIPE'
    QUESTION = 'QUESTION'
    AT = 'AT'
    HASH_LANG = 'HASH_LANG'
    NOT_EQUAL = 'NOT_EQUAL'

    EOF = 'EOF'


# Default (English) keyword table.
keyword_map = {
    'when': TokenType.WHEN,
    'end': TokenType.END,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'then': TokenType.THEN,
    'fn': TokenType.FN,
    'return': TokenType.RETURN,
    'show': TokenType.SHOW,
    'uses': TokenType.USES,
    'reads': TokenType.READS,
    'writes': TokenType.WRITES,
    'pure': TokenType.PURE,
    'borrows': TokenType.BORROWS,
    'UI': TokenType.UI,
    'scene': TokenType.SCENE,
    'require': TokenType.REQUIRE,
    'ensure': TokenType.ENSURE,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
    'is': TokenType.IS,
    'type': TokenType.TYPE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'import': TokenType.IMPORT,
    'while': TokenType.WHILE,
    'try': TokenType.TRY,
    'catch': TokenType.CATCH,
    'finally': TokenType.FINALLY,
    'on': TokenType.ON,
    'await': TokenType.AWAIT,
    'global': TokenType.GLOBAL,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'none': TokenType.NONE,
    'box': TokenType.BOX,
    'sphere': TokenType.SPHERE,
    'cylinder': TokenType.CYLINDER,
    'plane': TokenType.PLANE,
    'light': TokenType.LIGHT,
    'camera': TokenType.CAMERA,
}

# Localized keyword tables. Every table maps a localized word to the same
# TokenType as English, so the parser never changes. A file starting with
# `# lang: <code>` (en|ar|fr|es) selects the table; the English table always
# applies as a fallback (both are active simultaneously).
KEYWORDS_BY_LANG: dict[str, dict[str, TokenType]] = {
    'es': {
        'cuando': TokenType.WHEN,
        'fin': TokenType.END,
        'si': TokenType.IF,
        'sino': TokenType.ELSE,
        'entonces': TokenType.THEN,
        'funcion': TokenType.FN,
        'retornar': TokenType.RETURN,
        'mostrar': TokenType.SHOW,
        'usa': TokenType.USES,
        'lee': TokenType.READS,
        'escribe': TokenType.WRITES,
        'puro': TokenType.PURE,
        'requiere': TokenType.REQUIRE,
        'garantiza': TokenType.ENSURE,
        'y': TokenType.AND,
        'o': TokenType.OR,
        'no': TokenType.NOT,
        'es': TokenType.IS,
        'tipo': TokenType.TYPE,
        'para': TokenType.FOR,
        'en': TokenType.IN,
        'romper': TokenType.BREAK,
        'continuar': TokenType.CONTINUE,
        'importar': TokenType.IMPORT,
        'mientras': TokenType.WHILE,
        'intenta': TokenType.TRY,
        'captura': TokenType.CATCH,
        'finalmente': TokenType.FINALLY,
        'esperar': TokenType.AWAIT,
        'global': TokenType.GLOBAL,
        'verdadero': TokenType.TRUE,
        'falso': TokenType.FALSE,
        'nada': TokenType.NONE,
    },
    'fr': {
        'quand': TokenType.WHEN,
        'fin': TokenType.END,
        'si': TokenType.IF,
        'sinon': TokenType.ELSE,
        'alors': TokenType.THEN,
        'fonction': TokenType.FN,
        'retourner': TokenType.RETURN,
        'afficher': TokenType.SHOW,
        'utilise': TokenType.USES,
        'lit': TokenType.READS,
        'ecrit': TokenType.WRITES,
        'pur': TokenType.PURE,
        'exige': TokenType.REQUIRE,
        'assure': TokenType.ENSURE,
        'et': TokenType.AND,
        'ou': TokenType.OR,
        'pas': TokenType.NOT,
        'est': TokenType.IS,
        'type': TokenType.TYPE,
        'pour': TokenType.FOR,
        'dans': TokenType.IN,
        'rompre': TokenType.BREAK,
        'continuer': TokenType.CONTINUE,
        'importer': TokenType.IMPORT,
        'tantque': TokenType.WHILE,
        'essayer': TokenType.TRY,
        'attraper': TokenType.CATCH,
        'enfin': TokenType.FINALLY,
        'attendre': TokenType.AWAIT,
        'global': TokenType.GLOBAL,
        'vrai': TokenType.TRUE,
        'faux': TokenType.FALSE,
        'rien': TokenType.NONE,
    },
    'ar': {
        'عندما': TokenType.WHEN,
        'نهاية': TokenType.END,
        'إذا': TokenType.IF,
        'وإلا': TokenType.ELSE,
        'إذن': TokenType.THEN,
        'دالة': TokenType.FN,
        'أرجع': TokenType.RETURN,
        'أظهر': TokenType.SHOW,
        'يستخدم': TokenType.USES,
        'يقرأ': TokenType.READS,
        'يكتب': TokenType.WRITES,
        'نقي': TokenType.PURE,
        'يتطلب': TokenType.REQUIRE,
        'يضمن': TokenType.ENSURE,
        'و': TokenType.AND,
        'أو': TokenType.OR,
        'ليس': TokenType.NOT,
        'هو': TokenType.IS,
        'نوع': TokenType.TYPE,
        'لكل': TokenType.FOR,
        'في': TokenType.IN,
        'توقف': TokenType.BREAK,
        'واصل': TokenType.CONTINUE,
        'استيراد': TokenType.IMPORT,
        'طالما': TokenType.WHILE,
        'حاول': TokenType.TRY,
        'التقط': TokenType.CATCH,
        'أخيرا': TokenType.FINALLY,
        'انتظر': TokenType.AWAIT,
        'عام': TokenType.GLOBAL,
        'صحيح': TokenType.TRUE,
        'خطأ': TokenType.FALSE,
        'لا شيء': TokenType.NONE,
    },
}

# Localized top-level diagnostic strings (used by cli.py / ai_tools.py).
DIAGNOSTIC_STRINGS: dict[str, dict[str, str]] = {
    'en': {
        'syntax': 'Syntax error.',
        'name': 'Undefined variable or function',
        'internal': 'Internal compiler error.',
        'check-ok': 'omni check: OK',
        'runtime': 'Runtime error.',
    },
    'es': {
        'syntax': 'Error de sintaxis.',
        'name': 'Variable o funcion indefinida',
        'internal': 'Error interno del compilador.',
        'check-ok': 'omni check: OK',
        'runtime': 'Error de ejecucion.',
    },
    'fr': {
        'syntax': 'Erreur de syntaxe.',
        'name': 'Variable ou fonction non definie',
        'internal': 'Erreur interne du compilateur.',
        'check-ok': 'omni check: OK',
        'runtime': "Erreur d'execution.",
    },
    'ar': {
        'syntax': 'خطأ في بناء الجملة.',
        'name': 'متغير أو دالة غير معرفة',
        'internal': 'خطأ داخلي في المترجم.',
        'check-ok': 'omni check: OK',
        'runtime': 'خطأ في التنفيذ.',
    },
}

_LANG_DIRECTIVE = re.compile(r'^\s*#\s*lang\s*:\s*([a-zA-Z]+)')
_LANG_AGENT_DIRECTIVE = re.compile(r'^\s*#\s*lang\s+agent\b')


def detect_language(code: str) -> str:
    """Detect the active language from a leading ``# lang: xx`` directive."""
    if _LANG_AGENT_DIRECTIVE.match(code):
        return 'agent'
    match = _LANG_DIRECTIVE.match(code)
    if match:
        lang = match.group(1).lower()
        if lang in KEYWORDS_BY_LANG:
            return lang
    return 'en'


def is_agent_mode(code: str) -> bool:
    """Check if the code uses #lang agent shorthand syntax."""
    return _LANG_AGENT_DIRECTIVE.match(code) is not None


def keyword_tables_for(lang: str) -> dict[str, TokenType]:
    """Return the merged keyword table for a language (localized + English)."""
    table: dict[str, TokenType] = dict(keyword_map)
    table.update(KEYWORDS_BY_LANG.get(lang, {}))
    return table


@dataclass
class Token:
    """A single token with type, value, and location info."""

    type: TokenType
    value: str
    line: int
    column: int
    span_start: int
    span_end: int


def tokenize(code: str) -> list[Token]:  # noqa: PLR0912, PLR0915
    """Tokenize OmniScript source code into a list of tokens."""
    tokens = []
    line = 1
    column = 1
    pos = 0
    length = len(code)
    keywords = keyword_tables_for(detect_language(code))

    patterns = [
        ('HASH_LANG', r'^\s*#\s*lang\s+(\w+)'),
        ('COMMENT', r'#[^\r\n]*'),
        ('SLASH_COMMENT', r'//[^\r\n]*'),
        ('FAT_ARROW', r'=>'),
        ('PIPE', r'\|>'),
        ('QUESTION', r'\?'),
        ('AT', r'@'),
        ('NOT_EQUAL', r'!='),
        ('ARROW', r'->'),
        ('GREATER_OR_EQUAL', r'>='),
        ('LESS_OR_EQUAL', r'<='),
        ('GREATER', r'>'),
        ('LESS', r'<'),
        ('DOT', r'\.'),
        ('COLON', r':'),
        ('ASSIGN', r'='),
        ('PLUS', r'\+'),
        ('MINUS', r'-'),
        ('MULTIPLY', r'\*'),
        ('DIVIDE', r'/'),
        ('MODULO', r'%'),
        ('COMMA', r','),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('LBRACE', r'\{'),
        ('RBRACE', r'\}'),
        ('NUMBER', r'\d+(?:\.\d+)?(?:[eE][-+]?\d+)?'),
        ('TEXT', r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),
        ('IDENTIFIER', r'[^\W\d]\w*'),
        ('WHITESPACE', r'[ \t\r\n]+'),
    ]

    master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in patterns)
    compiled = re.compile(master_regex, re.DOTALL)

    while pos < length:
        # Check ahead for UI: block special handling
        if code.startswith('UI', pos):
            look_pos = pos + 2
            while look_pos < length and code[look_pos] in ' \t\r\n':
                look_pos += 1
            if look_pos < length and code[look_pos] == ':':
                # UI block detected
                tokens.append(Token(TokenType.UI, 'UI', line, column, pos, pos + 2))
                pos = look_pos + 1
                column += pos - pos  # adjust column if needed
                tokens.append(Token(TokenType.COLON, ':', line, column, look_pos, look_pos + 1))

                # Consume until 'end'
                html_start = pos
                end_match = re.search(r'\n\s*end\b', code[pos:])
                if end_match:
                    html_end = pos + end_match.start()
                    html_text = code[pos:html_end]
                    for ch in html_text:
                        if ch == '\n':
                            line += 1
                            column = 1
                        else:
                            column += 1
                    tokens.append(
                        Token(TokenType.UI_CONTENT, html_text, line, column, html_start, html_end)
                    )
                    pos = html_end
                else:
                    raise SyntaxError("Unterminated UI block: missing 'end'")
                continue

        match = compiled.match(code, pos)
        if not match:
            raise SyntaxError(f"Unexpected character '{code[pos]}' at line {line}, column {column}")

        kind = match.lastgroup
        value = match.group(kind) if kind is not None else match.group(0)
        span_start = pos
        span_end = pos + len(value)

        token_line = line
        token_col = column

        for ch in value:
            if ch == '\n':
                line += 1
                column = 1
            else:
                column += 1
        pos = span_end

        if kind in {'WHITESPACE', 'COMMENT', 'SLASH_COMMENT'}:
            continue
        if kind == 'HASH_LANG':
            tokens.append(
                Token(TokenType.HASH_LANG, value, token_line, token_col, span_start, span_end)
            )
            continue
        if kind == 'COLON':
            tokens.append(
                Token(TokenType.COLON, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'ASSIGN':
            tokens.append(
                Token(TokenType.ASSIGN, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'PLUS':
            tokens.append(Token(TokenType.PLUS, value, token_line, token_col, span_start, span_end))
        elif kind == 'MINUS':
            tokens.append(
                Token(TokenType.MINUS, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'MULTIPLY':
            tokens.append(
                Token(TokenType.MULTIPLY, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'DIVIDE':
            tokens.append(
                Token(TokenType.DIVIDE, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'MODULO':
            tokens.append(
                Token(TokenType.MODULO, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'ARROW':
            tokens.append(
                Token(TokenType.ARROW, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'FAT_ARROW':
            tokens.append(
                Token(TokenType.FAT_ARROW, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'PIPE':
            tokens.append(Token(TokenType.PIPE, value, token_line, token_col, span_start, span_end))
        elif kind == 'QUESTION':
            tokens.append(
                Token(TokenType.QUESTION, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'AT':
            tokens.append(Token(TokenType.AT, value, token_line, token_col, span_start, span_end))
        elif kind == 'NOT_EQUAL':
            tokens.append(
                Token(TokenType.NOT_EQUAL, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'GREATER_OR_EQUAL':
            tokens.append(
                Token(
                    TokenType.GREATER_OR_EQUAL, value, token_line, token_col, span_start, span_end
                )
            )
        elif kind == 'LESS_OR_EQUAL':
            tokens.append(
                Token(TokenType.LESS_OR_EQUAL, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'GREATER':
            tokens.append(
                Token(TokenType.GREATER, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'LESS':
            tokens.append(Token(TokenType.LESS, value, token_line, token_col, span_start, span_end))
        elif kind == 'COMMA':
            tokens.append(
                Token(TokenType.COMMA, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'LPAREN':
            tokens.append(
                Token(TokenType.LPAREN, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'RPAREN':
            tokens.append(
                Token(TokenType.RPAREN, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'LBRACKET':
            tokens.append(
                Token(TokenType.LBRACKET, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'RBRACKET':
            tokens.append(
                Token(TokenType.RBRACKET, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'LBRACE':
            tokens.append(
                Token(TokenType.LBRACE, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'RBRACE':
            tokens.append(
                Token(TokenType.RBRACE, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'DOT':
            tokens.append(Token(TokenType.DOT, value, token_line, token_col, span_start, span_end))
        elif kind == 'NUMBER':
            tokens.append(
                Token(TokenType.NUMBER, value, token_line, token_col, span_start, span_end)
            )
        elif kind == 'TEXT':
            tokens.append(Token(TokenType.TEXT, value, token_line, token_col, span_start, span_end))
        elif kind == 'IDENTIFIER':
            if value in ('greater', 'less'):
                rest = code[span_end:]
                stripped = rest.lstrip(' \t')
                if value == 'greater':
                    if stripped.startswith('or equal'):
                        tokens.append(
                            Token(
                                TokenType.GREATER_OR_EQUAL,
                                'greater or equal',
                                token_line,
                                token_col,
                                span_start,
                                span_end + len('greater') + len(stripped[: len('or equal')]),
                            )
                        )
                        pos += len(rest) - len(stripped) + len('or equal')
                        for ch in rest[: len(rest) - len(stripped) + len('or equal')]:
                            if ch == '\n':
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                    if stripped.startswith('than'):
                        tokens.append(
                            Token(
                                TokenType.GREATER,
                                'greater than',
                                token_line,
                                token_col,
                                span_start,
                                span_end + len('greater') + len(stripped[: len('than')]),
                            )
                        )
                        pos += len(rest) - len(stripped) + len('than')
                        for ch in rest[: len(rest) - len(stripped) + len('than')]:
                            if ch == '\n':
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                if value == 'less':
                    if stripped.startswith('or equal'):
                        tokens.append(
                            Token(
                                TokenType.LESS_OR_EQUAL,
                                'less or equal',
                                token_line,
                                token_col,
                                span_start,
                                span_end + len('less') + len(stripped[: len('or equal')]),
                            )
                        )
                        pos += len(rest) - len(stripped) + len('or equal')
                        for ch in rest[: len(rest) - len(stripped) + len('or equal')]:
                            if ch == '\n':
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
                    if stripped.startswith('than'):
                        tokens.append(
                            Token(
                                TokenType.LESS,
                                'less than',
                                token_line,
                                token_col,
                                span_start,
                                span_end + len('less') + len(stripped[: len('than')]),
                            )
                        )
                        pos += len(rest) - len(stripped) + len('than')
                        for ch in rest[: len(rest) - len(stripped) + len('than')]:
                            if ch == '\n':
                                line += 1
                                column = 1
                            else:
                                column += 1
                        continue
            if value in keywords:
                tokens.append(
                    Token(keywords[value], value, token_line, token_col, span_start, span_end)
                )
            else:
                tokens.append(
                    Token(TokenType.IDENTIFIER, value, token_line, token_col, span_start, span_end)
                )

    tokens.append(Token(TokenType.EOF, '', line, column, pos, pos))
    return tokens
