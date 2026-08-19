# ruff: noqa: D101, D102, D103, D107

"""Hand-written recursive-descent parser for OmniScript.

The AST node classes are plain data holders without per-class docstrings;
their names and fields are the documentation.
"""

from dataclasses import dataclass, field
from typing import Any, TypeVar

from omni_compiler.lexer import Token, TokenType

T = TypeVar('T', bound='ASTNode')


@dataclass
class ASTNode:
    kind: str
    line: int = 1
    column: int = 1
    span_start: int = 0
    span_end: int = 0


@dataclass
class SceneObject:
    shape: str = ''
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneBlock(ASTNode):
    kind: str = 'scene_block'
    objects: list[SceneObject] = field(default_factory=list)


@dataclass
class Program(ASTNode):
    statements: list[Any] = field(default_factory=list)
    app_block: Any | None = None
    functions: list[Any] = field(default_factory=list)
    ui_template: str | None = None
    scene_block: SceneBlock | None = None
    types: list['TypeDecl'] = field(default_factory=list)
    imports: list['ImportDecl'] = field(default_factory=list)


@dataclass
class ImportDecl(ASTNode):
    kind: str = 'import_decl'
    path: list[str] = field(default_factory=list)


@dataclass
class TypeDecl(ASTNode):
    kind: str = 'type_decl'
    name: str = ''
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Assignment(ASTNode):
    kind: str = 'assignment'
    name: str = ''
    expr: Any = None


@dataclass
class AppBlock(ASTNode):
    kind: str = 'app_block'
    body: list[Any] = field(default_factory=list)


@dataclass
class Parameter:
    name: str
    type: str


@dataclass
class FunctionDef(ASTNode):
    kind: str = 'fn_block'
    name: str = ''
    params: list[Parameter] = field(default_factory=list)
    return_type: str = 'None'
    requires: list[Any] = field(default_factory=list)
    ensures: list[Any] = field(default_factory=list)
    effects: dict[str, list[tuple[str, str | None]] | bool] = field(
        default_factory=lambda: {
            'uses': [],
            'reads': [],
            'writes': [],
            'borrows': [],
            'pure': False,
        }
    )
    body: list[Any] = field(default_factory=list)


@dataclass
class FunctionLiteral(ASTNode):
    kind: str = 'fn_literal'
    params: list[Parameter] = field(default_factory=list)
    return_type: str = 'None'
    body: list[Any] = field(default_factory=list)


@dataclass
class ReturnStmt(ASTNode):
    kind: str = 'return'
    expr: Any = None


@dataclass
class ShowStmt(ASTNode):
    kind: str = 'show'
    expr: Any = None


@dataclass
class BreakStmt(ASTNode):
    kind: str = 'break'


@dataclass
class ContinueStmt(ASTNode):
    kind: str = 'continue'


@dataclass
class IfBlock(ASTNode):
    kind: str = 'if_block'
    condition: Any = None
    body: list[Any] = field(default_factory=list)
    else_body: list[Any] = field(default_factory=list)


@dataclass
class ForBlock(ASTNode):
    kind: str = 'for_block'
    variable: str = ''
    var_type: str = ''
    iterable: Any = None
    body: list[Any] = field(default_factory=list)


@dataclass
class WhileBlock(ASTNode):
    kind: str = 'while_block'
    condition: Any = None
    body: list[Any] = field(default_factory=list)


@dataclass
class TryBlock(ASTNode):
    kind: str = 'try_block'
    body: list[Any] = field(default_factory=list)
    on_error_body: list[Any] = field(default_factory=list)
    error_var: str = ''
    finally_body: list[Any] = field(default_factory=list)


@dataclass
class GlobalDecl(ASTNode):
    kind: str = 'global_decl'
    name: str = ''


@dataclass
class AwaitExpr(ASTNode):
    kind: str = 'await_expr'
    expr: Any = None


@dataclass
class IndexExpr(ASTNode):
    kind: str = 'index_expr'
    object: Any = None
    index: Any = None


@dataclass
class MapLiteral(ASTNode):
    kind: str = 'map_literal'
    items: dict[str, Any] = field(default_factory=dict)


@dataclass
class ListLiteral(ASTNode):
    kind: str = 'list_literal'
    items: list[Any] = field(default_factory=list)


@dataclass
class Slot(ASTNode):
    kind: str = 'slot'
    expr: Any = None


@dataclass
class FieldAccess(ASTNode):
    kind: str = 'field_access'
    object: Any = None
    field: str = ''


@dataclass
class StructConstruct(ASTNode):
    kind: str = 'struct_construct'
    name: str = ''
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class BinaryExpr(ASTNode):
    kind: str = 'binary_expr'
    op: str = ''
    left: Any = None
    right: Any = None


@dataclass
class GroupExpr(ASTNode):
    kind: str = 'group_expr'
    expr: Any = None


@dataclass
class UnaryExpr(ASTNode):
    kind: str = 'unary_expr'
    op: str = ''  # "not" | "neg"
    operand: Any = None


@dataclass
class Literal(ASTNode):
    kind: str = 'literal'
    value_type: str = ''
    value: Any = None


@dataclass
class Identifier(ASTNode):
    kind: str = 'identifier'
    name: str = ''


@dataclass
class FunctionCall(ASTNode):
    kind: str = 'function_call'
    name: str = ''
    args: list[Any] = field(default_factory=list)


def dotted_name(expr: Any) -> str | None:
    """Flatten a field-access chain into a dotted name, or None."""
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, FieldAccess):
        base = dotted_name(expr.object)
        if base is None:
            return None
        return f'{base}.{expr.field}'
    return None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def _mark(self, node: T, token: Token) -> T:
        """Attach a source location (line/column/span) to an AST node."""
        node.line = token.line
        node.column = token.column
        node.span_start = token.span_start
        node.span_end = token.span_end
        return node

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def consume(
        self, expected_type: TokenType | None = None, expected_value: str | None = None
    ) -> Token:
        token = self.peek()
        if expected_type and token.type != expected_type:
            raise SyntaxError(
                f'Expected token type {expected_type}, got {token.type} '
                f'({token.value!r}) at line {token.line}, col {token.column}'
            )
        if expected_value and token.value != expected_value:
            raise SyntaxError(
                f'Expected token value {expected_value!r}, got {token.value!r} '
                f'at line {token.line}, col {token.column}'
            )
        self.pos += 1
        return token

    def match(self, token_type: TokenType, value: str | None = None) -> bool:
        token = self.peek()
        if token.type != token_type:
            return False
        return not (value is not None and token.value != value)

    def _is_named_arg_start(self) -> bool:
        if not self.match(TokenType.IDENTIFIER):
            return False
        nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        return bool(nxt and nxt.type == TokenType.ASSIGN)

    def parse(self) -> Program:
        prog = Program(kind='program')
        while not self.match(TokenType.EOF):
            token = self.peek()

            # Check for UI block
            if token.type == TokenType.UI:
                self.consume(TokenType.UI)
                self.consume(TokenType.COLON)
                content_token = self.consume(TokenType.UI_CONTENT)
                prog.ui_template = content_token.value
                self.consume(TokenType.END)
                continue

            # Check for scene block
            if token.type == TokenType.SCENE:
                prog.scene_block = self.parse_scene_block()
                continue

            # Check for type declaration
            if token.type == TokenType.TYPE:
                prog.types.append(self.parse_type_decl())
                continue

            # Check for import declaration
            if token.type == TokenType.IMPORT:
                prog.imports.append(self.parse_import())
                continue

            # Check for when app starts:
            if token.type == TokenType.WHEN:
                self.consume(TokenType.WHEN)
                self.consume(TokenType.IDENTIFIER, 'app')
                self.consume(TokenType.IDENTIFIER, 'starts')
                self.consume(TokenType.COLON)
                body = []
                while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                    body.append(self.parse_statement())
                self.consume(TokenType.END)
                prog.app_block = AppBlock(body=body)
                continue

            # Check for fn definition
            if token.type == TokenType.FN:
                prog.functions.append(self.parse_function())
                continue

            prog.statements.append(self.parse_statement())

        return prog

    def parse_function(self) -> FunctionDef:  # noqa: PLR0912, PLR0915
        self.consume(TokenType.FN)
        name_token = self.consume(TokenType.IDENTIFIER)
        fn_name = name_token.value

        params = []
        ret_type = 'None'
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if not self.match(TokenType.RPAREN):
                while True:
                    p_name = self.consume(TokenType.IDENTIFIER).value
                    self.consume(TokenType.COLON)
                    # Handle optional types with ?
                    p_type = self._parse_type()
                    params.append(Parameter(name=p_name, type=p_type))
                    if self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                    else:
                        break
            self.consume(TokenType.RPAREN)
            self.consume(TokenType.ARROW)
            # Handle optional return type with ?
            ret_type = self._parse_type()
        self.consume(TokenType.COLON)

        requires = []
        ensures = []
        effects: dict[str, list[tuple[str, str | None]] | bool] = {
            'uses': [],
            'reads': [],
            'writes': [],
            'borrows': [],
            'pure': False,
        }

        # Parse effect clauses and requirements/ensures
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            t = self.peek()
            if t.type == TokenType.REQUIRE:
                self.consume()
                requires.append(self.parse_expression())
            elif t.type == TokenType.ENSURE:
                self.consume()
                ensures.append(self.parse_expression())
            elif t.type in (TokenType.USES, TokenType.READS, TokenType.WRITES, TokenType.BORROWS):
                clause = t.type
                self.consume()
                if clause == TokenType.USES:
                    key = 'uses'
                elif clause == TokenType.READS:
                    key = 'reads'
                elif clause == TokenType.BORROWS:
                    key = 'borrows'
                else:
                    key = 'writes'
                clause_line = self.peek().line
                while self.match(TokenType.IDENTIFIER):
                    nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                    if nxt and nxt.type == TokenType.ASSIGN:
                        break
                    if self.peek().line != clause_line:
                        break
                    capability = self.consume(TokenType.IDENTIFIER).value
                    # Check for parameterized form: capability("arg")
                    if self.match(TokenType.LPAREN):
                        self.consume(TokenType.LPAREN)
                        if self.match(TokenType.TEXT):
                            arg = self.consume(TokenType.TEXT).value
                            # Remove quotes
                            if len(arg) >= 2 and arg[0] in ('"', "'"):  # noqa: PLR2004
                                arg = arg[1:-1]
                        else:
                            arg = self.consume(TokenType.IDENTIFIER).value
                        self.consume(TokenType.RPAREN)
                        _effect_list = effects[key]
                        assert isinstance(_effect_list, list)
                        _effect_list.append((capability, arg))
                    else:
                        _effect_list = effects[key]
                        assert isinstance(_effect_list, list)
                        _effect_list.append((capability, None))
            elif t.type == TokenType.PURE:
                self.consume()
                effects['pure'] = True
            else:
                break

        # Determine if this is a single-expression function or multi-statement
        # Single-expression functions have no effect clauses (or only pure) and
        # their body is a single expression followed by END/EOF
        body = []

        # Check if next token starts a statement
        statement_starters = {
            TokenType.RETURN,
            TokenType.SHOW,
            TokenType.IF,
            TokenType.FOR,
            TokenType.WHILE,
            TokenType.TRY,
            TokenType.GLOBAL,
            TokenType.BREAK,
            TokenType.CONTINUE,
        }

        next_token = self.peek()
        is_statement = False
        if next_token.type in statement_starters:
            is_statement = True
        elif next_token.type == TokenType.IDENTIFIER:
            # Check if it's an assignment (identifier followed by =)
            nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if nxt and nxt.type == TokenType.ASSIGN:
                is_statement = True
            elif nxt and nxt.type == TokenType.LPAREN:
                # Function call as statement: foo()
                is_statement = True
            elif nxt and nxt.type == TokenType.DOT:
                # Method call chain as statement: obj.method() or obj.prop.method()
                # Scan ahead for a LPAREN after a chain of DOT IDENTIFIER
                look_pos = self.pos + 2
                while look_pos < len(self.tokens):
                    t = self.tokens[look_pos]
                    if t.type == TokenType.LPAREN:
                        is_statement = True
                        break
                    if t.type == TokenType.DOT:
                        look_pos += 1
                        continue
                    if t.type == TokenType.IDENTIFIER:
                        look_pos += 1
                        continue
                    break

        if is_statement:
            # Multi-statement function
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                body.append(self.parse_statement())
        # Try single-expression function
        elif not self.match(TokenType.EOF) and not self.match(TokenType.END):
            expr = self.parse_expression()
            body.append(ReturnStmt(expr=expr))
            # Implicit pure for single-expression functions without explicit effects
            if (
                not effects['uses']
                and not effects['reads']
                and not effects['writes']
                and not effects['borrows']
                and not any(
                    t.type == TokenType.PURE for t in self.tokens[max(0, self.pos - 5) : self.pos]
                )
            ):
                effects['pure'] = True

        if self.match(TokenType.END):
            self.consume(TokenType.END)
        return FunctionDef(
            name=fn_name,
            params=params,
            return_type=ret_type,
            requires=requires,
            ensures=ensures,
            effects=effects,
            body=body,
        )

    def parse_function_literal(self, start: Token) -> FunctionLiteral:  # noqa: PLR0912, PLR0915
        """Parse an inline function literal: fn(params) -> Type: body end."""
        self.consume(TokenType.FN)

        params = []
        ret_type = 'None'
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if not self.match(TokenType.RPAREN):
                while True:
                    p_name = self.consume(TokenType.IDENTIFIER).value
                    self.consume(TokenType.COLON)
                    p_type = self._parse_type()
                    params.append(Parameter(name=p_name, type=p_type))
                    if self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                    else:
                        break
            self.consume(TokenType.RPAREN)
            self.consume(TokenType.ARROW)
            ret_type = self._parse_type()
        self.consume(TokenType.COLON)

        body = []
        # Check if single expression or multi-statement
        statement_starters = {
            TokenType.RETURN,
            TokenType.SHOW,
            TokenType.IF,
            TokenType.FOR,
            TokenType.WHILE,
            TokenType.TRY,
            TokenType.GLOBAL,
            TokenType.BREAK,
            TokenType.CONTINUE,
        }

        next_token = self.peek()
        is_statement = False
        if next_token.type in statement_starters:
            is_statement = True
        elif next_token.type == TokenType.IDENTIFIER:
            nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if nxt and nxt.type == TokenType.ASSIGN:
                is_statement = True
            elif nxt and nxt.type == TokenType.LPAREN:
                # Function call as statement: foo()
                is_statement = True
            elif nxt and nxt.type == TokenType.DOT:
                # Method call chain as statement: obj.method() or obj.prop.method()
                # Scan ahead for a LPAREN after a chain of DOT IDENTIFIER
                look_pos = self.pos + 2
                while look_pos < len(self.tokens):
                    t = self.tokens[look_pos]
                    if t.type == TokenType.LPAREN:
                        is_statement = True
                        break
                    if t.type == TokenType.DOT:
                        look_pos += 1
                        continue
                    if t.type == TokenType.IDENTIFIER:
                        look_pos += 1
                        continue
                    break

        if is_statement:
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                body.append(self.parse_statement())
        elif not self.match(TokenType.EOF) and not self.match(TokenType.END):
            expr = self.parse_expression()
            body.append(ReturnStmt(expr=expr))

        if self.match(TokenType.END):
            self.consume(TokenType.END)
        return self._mark(
            FunctionLiteral(
                params=params,
                return_type=ret_type,
                body=body,
            ),
            start,
        )

    def _parse_type(self) -> str:
        """Parse a type annotation, handling optional types with ?."""
        if self.match(TokenType.IDENTIFIER):
            base_type = self.consume(TokenType.IDENTIFIER).value
            # Check for optional marker ?
            if self.match(TokenType.QUESTION):
                self.consume(TokenType.QUESTION)
                return base_type + '?'
            return base_type
        return 'None'

    def parse_statement(self) -> Any:  # noqa: PLR0911, PLR0912
        start = self.peek()
        node: Any
        t = self.peek()
        if t.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            expr = self.parse_expression()
            node = ReturnStmt(expr=expr)
        elif t.type == TokenType.SHOW:
            self.consume(TokenType.SHOW)
            expr = self.parse_expression()
            node = ShowStmt(expr=expr)
        elif t.type == TokenType.BREAK:
            self.consume(TokenType.BREAK)
            node = BreakStmt()
        elif t.type == TokenType.CONTINUE:
            self.consume(TokenType.CONTINUE)
            node = ContinueStmt()
        elif t.type == TokenType.IF:
            return self.parse_if_block()
        elif t.type == TokenType.FOR:
            return self.parse_for_block()
        elif t.type == TokenType.WHILE:
            return self.parse_while_block()
        elif t.type == TokenType.TRY:
            return self.parse_try_block()
        elif t.type == TokenType.GLOBAL:
            self.consume(TokenType.GLOBAL)
            name = self.consume(TokenType.IDENTIFIER).value
            node = GlobalDecl(name=name)
        elif t.type == TokenType.IDENTIFIER:
            next_t = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_t and next_t.type == TokenType.ASSIGN:
                name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.ASSIGN)
                expr = self.parse_expression()
                node = Assignment(name=name, expr=expr)
            else:
                return self._mark(self.parse_expression(), start)
        else:
            return self._mark(self.parse_expression(), start)
        return self._mark(node, start)

    def parse_while_block(self) -> WhileBlock:
        start = self.peek()
        self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        self.consume(TokenType.COLON)
        body: list[Any] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            body.append(self.parse_statement())
        self.consume(TokenType.END)
        return self._mark(WhileBlock(condition=condition, body=body), start)

    def parse_try_block(self) -> TryBlock:
        start = self.peek()
        self.consume(TokenType.TRY)
        self.consume(TokenType.COLON)
        body: list[Any] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            if (
                self.match(TokenType.CATCH)
                or self.match(TokenType.ON)
                or self.match(TokenType.FINALLY)
            ):
                break
            body.append(self.parse_statement())
        error_body: list[Any] = []
        error_var = ''
        if self.match(TokenType.CATCH):
            self.consume(TokenType.CATCH)
            if self.match(TokenType.IDENTIFIER):
                error_var = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.COLON)
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                if self.match(TokenType.FINALLY):
                    break
                error_body.append(self.parse_statement())
        elif self.match(TokenType.ON):
            # `on error:` is the OmniScript-flavoured alias for `catch`.
            self.consume(TokenType.ON)
            self.consume(TokenType.IDENTIFIER, 'error')
            self.consume(TokenType.COLON)
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                if self.match(TokenType.FINALLY):
                    break
                error_body.append(self.parse_statement())
        finally_body: list[Any] = []
        if self.match(TokenType.FINALLY):
            self.consume(TokenType.FINALLY)
            self.consume(TokenType.COLON)
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                finally_body.append(self.parse_statement())
        self.consume(TokenType.END)
        return self._mark(
            TryBlock(
                body=body, on_error_body=error_body, error_var=error_var, finally_body=finally_body
            ),
            start,
        )

    _IMPORT_SEGMENT_TYPES = {TokenType.IDENTIFIER, TokenType.SCENE, TokenType.AWAIT}
    # Extend this set if a future OMNISYS module name collides with a keyword.

    def _consume_import_segment(self) -> str:
        t = self.peek()
        if t.type in self._IMPORT_SEGMENT_TYPES:
            self.consume()
            return t.value
        raise SyntaxError(
            f'Expected an import path segment, got {t.type} ({t.value!r}) '
            f'at line {t.line}, col {t.column}'
        )

    def _consume_field_segment(self) -> str:
        t = self.peek()
        if t.type in self._IMPORT_SEGMENT_TYPES:
            self.consume()
            return t.value
        raise SyntaxError(
            f'Expected a field name, got {t.type} ({t.value!r}) at line {t.line}, col {t.column}'
        )

    def parse_import(self) -> ImportDecl:
        self.consume(TokenType.IMPORT)
        path = [self._consume_import_segment()]
        while self.match(TokenType.DOT):
            self.consume(TokenType.DOT)
            path.append(self._consume_import_segment())
        return ImportDecl(path=path)

    def parse_type_decl(self) -> TypeDecl:
        self.consume(TokenType.TYPE)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.ASSIGN)
        self.consume(TokenType.LBRACE)
        fields: dict[str, str] = {}
        if not self.match(TokenType.RBRACE):
            while True:
                fname = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.COLON)
                ftype = self.consume(TokenType.IDENTIFIER).value
                fields[fname] = ftype
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                else:
                    break
        self.consume(TokenType.RBRACE)
        return TypeDecl(name=name, fields=fields)

    def parse_if_block(self) -> IfBlock:
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.COLON)
        body: list[Any] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            if self.match(TokenType.ELSE):
                break
            body.append(self.parse_statement())
        else_body: list[Any] = []
        if self.match(TokenType.ELSE):
            self.consume(TokenType.ELSE)
            self.consume(TokenType.COLON)
            while not self.match(TokenType.EOF) and not self.match(TokenType.END):
                else_body.append(self.parse_statement())
        self.consume(TokenType.END)
        return IfBlock(condition=condition, body=body, else_body=else_body)

    def parse_for_block(self) -> ForBlock:
        start = self.peek()
        self.consume(TokenType.FOR)
        variable = self.consume(TokenType.IDENTIFIER).value
        var_type = ''
        if self.match(TokenType.COLON):
            self.consume(TokenType.COLON)
            var_type = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.IN)
        iterable = self.parse_expression()
        self.consume(TokenType.COLON)
        body: list[Any] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            body.append(self.parse_statement())
        self.consume(TokenType.END)
        return self._mark(
            ForBlock(variable=variable, var_type=var_type, iterable=iterable, body=body), start
        )

    SHAPE_TOKEN_TYPES = {
        TokenType.BOX,
        TokenType.SPHERE,
        TokenType.CYLINDER,
        TokenType.PLANE,
        TokenType.LIGHT,
        TokenType.CAMERA,
    }

    SCENE_ATTR_NAMES = {
        'size',
        'color',
        'pos',
        'rotation',
        'scale',
        'type',
        'intensity',
        'texture',
        'click',
    }

    def parse_scene_block(self) -> SceneBlock:
        self.consume(TokenType.SCENE)
        self.consume(TokenType.COLON)
        objects: list[SceneObject] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            shape_token = self.peek()
            if shape_token.type not in self.SHAPE_TOKEN_TYPES:
                raise SyntaxError(
                    f"Expected a scene shape keyword, got '{shape_token.value}' "
                    f'at line {shape_token.line}, col {shape_token.column}'
                )
            self.consume()
            attrs: dict[str, Any] = {}
            while self.match(TokenType.IDENTIFIER) or self.peek().value in self.SCENE_ATTR_NAMES:
                attr_tok = self.peek()
                name = attr_tok.value
                self.consume()
                self.consume(TokenType.ASSIGN)
                if self.match(TokenType.LBRACE):
                    self.consume(TokenType.LBRACE)
                    expr = self.parse_expression()
                    self.consume(TokenType.RBRACE)
                    attrs[name] = Slot(expr=expr)
                elif self.match(TokenType.TEXT):
                    text_tok = self.consume(TokenType.TEXT)
                    raw = text_tok.value
                    is_quoted = len(raw) >= 2 and raw[0] in ('"', "'")  # noqa: PLR2004
                    body = raw[1:-1] if is_quoted else raw
                    attrs[name] = Literal(value_type='Text', value=body)
                elif self.match(TokenType.NUMBER):
                    num_tok = self.consume(TokenType.NUMBER)
                    val = (
                        float(num_tok.value)
                        if '.' in num_tok.value or 'e' in num_tok.value.lower()
                        else int(num_tok.value)
                    )
                    attrs[name] = Literal(value_type='Number', value=val)
                else:
                    raise SyntaxError(
                        f"Expected a scene attribute value for '{name}' at line "
                        f'{self.peek().line}, col {self.peek().column}'
                    )
            objects.append(SceneObject(shape=shape_token.value, attrs=attrs))
        self.consume(TokenType.END)
        return SceneBlock(objects=objects)

    def parse_expression(self) -> Any:
        return self.parse_pipe()

    def parse_pipe(self) -> Any:
        """Parse pipe operator |> (lowest precedence)."""
        left = self.parse_or()
        while self.match(TokenType.PIPE):
            self.consume(TokenType.PIPE)
            right = self.parse_or()
            # Pipe: x |> f  becomes  f(x)
            left = BinaryExpr(op='|>', left=left, right=right)
        return left

    def parse_binary_expr(self) -> Any:
        return self.parse_or()

    def parse_or(self) -> Any:
        left = self.parse_and()
        while self.match(TokenType.OR):
            self.consume(TokenType.OR)
            right = self.parse_and()
            left = BinaryExpr(op='or', left=left, right=right)
        return left

    def parse_and(self) -> Any:
        left = self.parse_not()
        while self.match(TokenType.AND):
            self.consume(TokenType.AND)
            right = self.parse_not()
            left = BinaryExpr(op='and', left=left, right=right)
        return left

    def parse_not(self) -> Any:
        if self.match(TokenType.NOT):
            self.consume(TokenType.NOT)
            return UnaryExpr(op='not', operand=self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        left = self.parse_term()
        while (
            self.match(TokenType.IS)
            or self.match(TokenType.GREATER)
            or self.match(TokenType.LESS)
            or self.match(TokenType.GREATER_OR_EQUAL)
            or self.match(TokenType.LESS_OR_EQUAL)
            or self.match(TokenType.NOT_EQUAL)
        ):
            t = self.consume()
            if t.type == TokenType.IS and self.match(TokenType.NOT):
                self.consume(TokenType.NOT)
                op = 'is not'
            elif t.type == TokenType.NOT_EQUAL:
                op = 'is not'
            else:
                op = t.value
            right = self.parse_term()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_term(self) -> Any:
        left = self.parse_factor()
        while self.match(TokenType.PLUS) or self.match(TokenType.MINUS):
            op_token = self.peek()
            self.consume()
            op = op_token.value
            right = self.parse_factor()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_factor(self) -> Any:
        left = self.parse_unary()
        while (
            self.match(TokenType.MULTIPLY)
            or self.match(TokenType.DIVIDE)
            or self.match(TokenType.MODULO)
        ):
            op_token = self.peek()
            self.consume()
            op = op_token.value
            right = self.parse_unary()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_unary(self) -> Any:
        if self.match(TokenType.MINUS):
            self.consume(TokenType.MINUS)
            return UnaryExpr(op='neg', operand=self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Any:  # noqa: PLR0911, PLR0912, PLR0915
        t = self.peek()
        if t.type == TokenType.AWAIT:
            self.consume(TokenType.AWAIT)
            return self._mark(AwaitExpr(expr=self.parse_primary()), t)
        if t.type == TokenType.NUMBER:
            self.consume()
            number_val: int | float = (
                float(t.value) if '.' in t.value or 'e' in t.value.lower() else int(t.value)
            )
            return self._mark(Literal(value_type='Number', value=number_val), t)
        if t.type == TokenType.TEXT:
            self.consume()
            text_val = t.value
            if len(text_val) >= 2 and (  # noqa: PLR2004
                (text_val[0] == '"' and text_val[-1] == '"')
                or (text_val[0] == "'" and text_val[-1] == "'")
            ):
                text_val = text_val[1:-1]
                text_val = text_val.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            return self._mark(Literal(value_type='Text', value=text_val), t)
        if t.type == TokenType.TRUE:
            self.consume()
            return self._mark(Literal(value_type='Boolean', value=True), t)
        if t.type == TokenType.FALSE:
            self.consume()
            return self._mark(Literal(value_type='Boolean', value=False), t)
        if t.type == TokenType.NONE:
            self.consume()
            return self._mark(Literal(value_type='None', value=None), t)
        if t.type == TokenType.IDENTIFIER:
            name = t.value
            self.consume()
            expr: Any = self._mark(Identifier(name=name), t)
            while True:
                if self.match(TokenType.DOT):
                    self.consume(TokenType.DOT)
                    field = self._consume_field_segment()
                    expr = self._mark(FieldAccess(object=expr, field=field), t)
                elif self.match(TokenType.LBRACKET):
                    self.consume(TokenType.LBRACKET)
                    index = self.parse_expression()
                    self.consume(TokenType.RBRACKET)
                    expr = self._mark(IndexExpr(object=expr, index=index), t)
                elif self.match(TokenType.LPAREN):
                    self.consume(TokenType.LPAREN)
                    target_name = dotted_name(expr) or str(expr)
                    if self.match(TokenType.RPAREN):
                        self.consume(TokenType.RPAREN)
                        expr = self._mark(FunctionCall(name=target_name, args=[]), t)
                    elif self._is_named_arg_start():
                        args_dict: dict[str, Any] = {}
                        while True:
                            arg_name = self.consume(TokenType.IDENTIFIER).value
                            self.consume(TokenType.ASSIGN)
                            args_dict[arg_name] = self.parse_expression()
                            if self.match(TokenType.COMMA):
                                self.consume(TokenType.COMMA)
                            else:
                                break
                        self.consume(TokenType.RPAREN)
                        expr = self._mark(StructConstruct(name=target_name, args=args_dict), t)
                    else:
                        args_list: list[Any] = []
                        while True:
                            args_list.append(self.parse_expression())
                            if self.match(TokenType.COMMA):
                                self.consume(TokenType.COMMA)
                            else:
                                break
                        self.consume(TokenType.RPAREN)
                        expr = self._mark(FunctionCall(name=target_name, args=args_list), t)
                else:
                    break
            return expr
        if t.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return self._mark(GroupExpr(expr=expr), t)
        if t.type == TokenType.LBRACKET:
            self.consume(TokenType.LBRACKET)
            items = []
            if not self.match(TokenType.RBRACKET):
                while True:
                    items.append(self.parse_expression())
                    if self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                    else:
                        break
            self.consume(TokenType.RBRACKET)
            return self._mark(ListLiteral(items=items), t)
        if t.type == TokenType.LBRACE:
            return self.parse_map_literal(t)
        if t.type == TokenType.FN:
            return self.parse_function_literal(t)
        raise SyntaxError(
            f'Unexpected token {t.value!r} of type {t.type} at line {t.line}, col {t.column}'
        )

    def parse_map_literal(self, start: Token) -> MapLiteral:
        """Parse a ``{key: value, ...}`` map literal in expression context."""
        self.consume(TokenType.LBRACE)
        items: dict[str, Any] = {}
        if not self.match(TokenType.RBRACE):
            while True:
                key_tok = self.peek()
                if key_tok.type in (TokenType.IDENTIFIER, TokenType.TEXT, TokenType.NUMBER):
                    self.consume()
                    if key_tok.type == TokenType.TEXT:
                        key = key_tok.value
                        if len(key) >= 2 and key[0] in ('"', "'"):  # noqa: PLR2004
                            key = key[1:-1]
                    elif key_tok.type == TokenType.NUMBER:
                        key = str(key_tok.value)
                    else:
                        key = key_tok.value
                else:
                    raise SyntaxError(
                        f'Expected a map key, got {key_tok.type} ({key_tok.value!r}) '
                        f'at line {key_tok.line}, col {key_tok.column}'
                    )
                self.consume(TokenType.COLON)
                items[key] = self.parse_expression()
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                else:
                    break
        self.consume(TokenType.RBRACE)
        return self._mark(MapLiteral(items=items), start)


def parse(tokens: list[Token]) -> Program:
    """Parse tokens into an AST. Handles #lang agent shorthand syntax via preprocessing."""
    # Check if agent mode is enabled (first token might be HASH_LANG)
    agent_mode = False
    for token in tokens:
        if token.type == TokenType.HASH_LANG and token.value.strip() == '#lang agent':
            agent_mode = True
            break

    if agent_mode:
        tokens = _preprocess_agent_tokens(tokens)

    parser = Parser(tokens)
    return parser.parse()


def _preprocess_agent_tokens(tokens: list[Token]) -> list[Token]:  # noqa: PLR0912, PLR0915
    """Convert agent mode shorthand tokens to canonical tokens.

    Transformations:
    - `=>` -> `->` (FAT_ARROW -> ARROW)
    - `|>` -> pipe operator (handled in expression parsing)
    - `?` -> optional type marker (handled in type parsing)
    - `@require` -> `require` keyword
    - `@ensure` -> `ensure` keyword
    - Implicit `fn` for function definitions: `name(params) -> Type: body end`
    - Implicit `end` for single-expression functions: `add(a, b) -> Number: a + b`
    - Compact struct: `{x: 1, y: 2}` (already parsed as MapLiteral, converted in type context)
    """
    new_tokens = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Skip the #lang agent directive token
        if token.type == TokenType.HASH_LANG:
            i += 1
            continue

        # Convert FAT_ARROW (=>) to ARROW (->)
        if token.type == TokenType.FAT_ARROW:
            new_tokens.append(
                Token(
                    TokenType.ARROW,
                    '->',
                    token.line,
                    token.column,
                    token.span_start,
                    token.span_end,
                )
            )
            i += 1
            continue

        # Convert @require -> require keyword, @ensure -> ensure keyword
        if token.type == TokenType.AT:
            # Look ahead for "require" or "ensure" (as IDENTIFIER or keyword tokens)
            if i + 1 < len(tokens):
                next_token = tokens[i + 1]
                if next_token.type == TokenType.IDENTIFIER:
                    next_val = next_token.value
                    if next_val == 'require':
                        new_tokens.append(
                            Token(
                                TokenType.REQUIRE,
                                'require',
                                token.line,
                                token.column,
                                token.span_start,
                                next_token.span_end,
                            )
                        )
                        i += 2
                        continue
                    if next_val == 'ensure':
                        new_tokens.append(
                            Token(
                                TokenType.ENSURE,
                                'ensure',
                                token.line,
                                token.column,
                                token.span_start,
                                next_token.span_end,
                            )
                        )
                        i += 2
                        continue
                elif next_token.type == TokenType.REQUIRE:
                    # Already tokenized as REQUIRE keyword, just skip the @
                    new_tokens.append(next_token)
                    i += 2
                    continue
                elif next_token.type == TokenType.ENSURE:
                    # Already tokenized as ENSURE keyword, just skip the @
                    new_tokens.append(next_token)
                    i += 2
                    continue
            # Otherwise keep @ as-is (for other uses)
            new_tokens.append(token)
            i += 1
            continue

        # Handle implicit function definitions (no 'fn' keyword)
        # Pattern: IDENTIFIER LPAREN ... -> Type COLON ...
        # But only if the previous token is not already FN
        if (
            token.type == TokenType.IDENTIFIER
            and i + 1 < len(tokens)
            and tokens[i + 1].type == TokenType.LPAREN
            and (i == 0 or tokens[i - 1].type != TokenType.FN)
        ):
            # This looks like a function definition, check if it's followed by ->
            # We need to look ahead to find ARROW or FAT_ARROW after the closing paren
            j = i + 2
            paren_depth = 1
            found_arrow = False
            while j < len(tokens) and paren_depth > 0:
                if tokens[j].type == TokenType.LPAREN:
                    paren_depth += 1
                elif tokens[j].type == TokenType.RPAREN:
                    paren_depth -= 1
                j += 1
            # Now j is at the token after the closing paren (or end of tokens)
            # Check if the next token is ARROW or FAT_ARROW
            if j < len(tokens) and tokens[j].type in (TokenType.ARROW, TokenType.FAT_ARROW):
                found_arrow = True

            if found_arrow:
                # Insert 'fn' keyword before the function name
                new_tokens.append(
                    Token(
                        TokenType.FN,
                        'fn',
                        token.line,
                        token.column,
                        token.span_start,
                        token.span_end,
                    )
                )
                new_tokens.append(token)
                i += 1
                continue

        new_tokens.append(token)
        i += 1

    # Second pass: handle implicit 'end' for single-expression functions
    # and PIPE operator
    final_tokens = []
    i = 0
    while i < len(new_tokens):
        token = new_tokens[i]

        # Handle PIPE (|>) as a binary operator - keep as PIPE for parser to handle
        if token.type == TokenType.PIPE:
            final_tokens.append(token)
            i += 1
            continue

        # Handle QUESTION (?) for optional types - keep for parser
        if token.type == TokenType.QUESTION:
            final_tokens.append(token)
            i += 1
            continue

        final_tokens.append(token)
        i += 1

    return final_tokens
