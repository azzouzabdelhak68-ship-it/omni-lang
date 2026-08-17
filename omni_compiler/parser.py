from dataclasses import dataclass, field
from typing import Any

from omni_compiler.lexer import Token, TokenType


@dataclass
class ASTNode:
    kind: str

@dataclass
class SceneObject:
    shape: str = ""
    attrs: dict[str, Any] = field(default_factory=dict)

@dataclass
class SceneBlock(ASTNode):
    kind: str = "scene_block"
    objects: list[SceneObject] = field(default_factory=list)

@dataclass
class Program(ASTNode):
    statements: list[Any] = field(default_factory=list)
    app_block: Any | None = None
    functions: list[Any] = field(default_factory=list)
    ui_template: str | None = None
    scene_block: SceneBlock | None = None
    types: list["TypeDecl"] = field(default_factory=list)
    imports: list["ImportDecl"] = field(default_factory=list)

@dataclass
class ImportDecl(ASTNode):
    kind: str = "import_decl"
    path: list[str] = field(default_factory=list)

@dataclass
class TypeDecl(ASTNode):
    kind: str = "type_decl"
    name: str = ""
    fields: dict[str, str] = field(default_factory=dict)

@dataclass
class Assignment(ASTNode):
    kind: str = "assignment"
    name: str = ""
    expr: Any = None

@dataclass
class AppBlock(ASTNode):
    kind: str = "app_block"
    body: list[Any] = field(default_factory=list)

@dataclass
class Parameter:
    name: str
    type: str

@dataclass
class FunctionDef(ASTNode):
    kind: str = "fn_block"
    name: str = ""
    params: list[Parameter] = field(default_factory=list)
    return_type: str = "None"
    requires: list[Any] = field(default_factory=list)
    ensures: list[Any] = field(default_factory=list)
    effects: dict[str, list[str]] = field(default_factory=lambda: {"uses": [], "reads": [], "writes": [], "pure": False})
    body: list[Any] = field(default_factory=list)

@dataclass
class ReturnStmt(ASTNode):
    kind: str = "return"
    expr: Any = None

@dataclass
class ShowStmt(ASTNode):
    kind: str = "show"
    expr: Any = None

@dataclass
class BreakStmt(ASTNode):
    kind: str = "break"

@dataclass
class ContinueStmt(ASTNode):
    kind: str = "continue"

@dataclass
class IfBlock(ASTNode):
    kind: str = "if_block"
    condition: Any = None
    body: list[Any] = field(default_factory=list)
    else_body: list[Any] = field(default_factory=list)

@dataclass
class ForBlock(ASTNode):
    kind: str = "for_block"
    variable: str = ""
    iterable: Any = None
    body: list[Any] = field(default_factory=list)

@dataclass
class ListLiteral(ASTNode):
    kind: str = "list_literal"
    items: list[Any] = field(default_factory=list)

@dataclass
class Slot(ASTNode):
    kind: str = "slot"
    expr: Any = None

@dataclass
class FieldAccess(ASTNode):
    kind: str = "field_access"
    object: Any = None
    field: str = ""

@dataclass
class StructConstruct(ASTNode):
    kind: str = "struct_construct"
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)

@dataclass
class BinaryExpr(ASTNode):
    kind: str = "binary_expr"
    op: str = ""
    left: Any = None
    right: Any = None

@dataclass
class Literal(ASTNode):
    kind: str = "literal"
    value_type: str = ""
    value: Any = None

@dataclass
class Identifier(ASTNode):
    kind: str = "identifier"
    name: str = ""

@dataclass
class FunctionCall(ASTNode):
    kind: str = "function_call"
    name: str = ""
    args: list[Any] = field(default_factory=list)


def dotted_name(expr: Any) -> str | None:
    """Flatten a field-access chain into a dotted name, or None."""
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, FieldAccess):
        base = dotted_name(expr.object)
        if base is None:
            return None
        return f"{base}.{expr.field}"
    return None

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def consume(self, expected_type: TokenType | None = None, expected_value: str | None = None) -> Token:
        token = self.peek()
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected token type {expected_type}, got {token.type} ('{token.value}') at line {token.line}, col {token.column}")
        if expected_value and token.value != expected_value:
            raise SyntaxError(f"Expected token value '{expected_value}', got '{token.value}' at line {token.line}, col {token.column}")
        self.pos += 1
        return token

    def match(self, token_type: TokenType, value: str | None = None) -> bool:
        token = self.peek()
        if token.type != token_type:
            return False
        if value is not None and token.value != value:
            return False
        return True

    def _is_named_arg_start(self) -> bool:
        if not self.match(TokenType.IDENTIFIER):
            return False
        nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        return bool(nxt and nxt.type == TokenType.ASSIGN)

    def parse(self) -> Program:
        prog = Program(kind="program")
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
                self.consume(TokenType.IDENTIFIER, "app")
                self.consume(TokenType.IDENTIFIER, "starts")
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

    def parse_function(self) -> FunctionDef:
        self.consume(TokenType.FN)
        name_token = self.consume(TokenType.IDENTIFIER)
        fn_name = name_token.value
        
        params = []
        ret_type = "None"
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if not self.match(TokenType.RPAREN):
                while True:
                    p_name = self.consume(TokenType.IDENTIFIER).value
                    self.consume(TokenType.COLON)
                    p_type = self.consume(TokenType.IDENTIFIER).value
                    params.append(Parameter(name=p_name, type=p_type))
                    if self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                    else:
                        break
            self.consume(TokenType.RPAREN)
            self.consume(TokenType.ARROW)
            ret_type = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.COLON)
        
        requires = []
        ensures = []
        effects = {"uses": [], "reads": [], "writes": [], "pure": False}
        
        # Parse effect clauses and requirements/ensures
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            t = self.peek()
            if t.type == TokenType.REQUIRE:
                self.consume()
                requires.append(self.parse_expression())
            elif t.type == TokenType.ENSURE:
                self.consume()
                ensures.append(self.parse_expression())
            elif t.type in (TokenType.USES, TokenType.READS, TokenType.WRITES):
                clause = t.type
                self.consume()
                if clause == TokenType.USES:
                    key = "uses"
                elif clause == TokenType.READS:
                    key = "reads"
                else:
                    key = "writes"
                clause_line = self.peek().line
                while self.match(TokenType.IDENTIFIER):
                    nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                    if nxt and nxt.type == TokenType.ASSIGN:
                        break
                    if self.peek().line != clause_line:
                        break
                    effects[key].append(self.consume(TokenType.IDENTIFIER).value)
            elif t.type == TokenType.PURE:
                self.consume()
                effects["pure"] = True
            else:
                break
                
        body = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            body.append(self.parse_statement())
            
        self.consume(TokenType.END)
        return FunctionDef(name=fn_name, params=params, return_type=ret_type, requires=requires, ensures=ensures, effects=effects, body=body)

    def parse_statement(self) -> Any:
        t = self.peek()
        if t.type == TokenType.RETURN:
            self.consume(TokenType.RETURN)
            expr = self.parse_expression()
            return ReturnStmt(expr=expr)
        if t.type == TokenType.SHOW:
            self.consume(TokenType.SHOW)
            expr = self.parse_expression()
            return ShowStmt(expr=expr)
        if t.type == TokenType.BREAK:
            self.consume(TokenType.BREAK)
            return BreakStmt()
        if t.type == TokenType.CONTINUE:
            self.consume(TokenType.CONTINUE)
            return ContinueStmt()
        if t.type == TokenType.IF:
            return self.parse_if_block()
        if t.type == TokenType.FOR:
            return self.parse_for_block()
        if t.type == TokenType.IDENTIFIER:
            next_t = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_t and next_t.type == TokenType.ASSIGN:
                name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.ASSIGN)
                expr = self.parse_expression()
                return Assignment(name=name, expr=expr)
            return self.parse_expression()
        return self.parse_expression()

    def parse_import(self) -> ImportDecl:
        self.consume(TokenType.IMPORT)
        path = [self.consume(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.consume(TokenType.DOT)
            path.append(self.consume(TokenType.IDENTIFIER).value)
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
        self.consume(TokenType.FOR)
        variable = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.IN)
        iterable = self.parse_expression()
        self.consume(TokenType.COLON)
        body: list[Any] = []
        while not self.match(TokenType.EOF) and not self.match(TokenType.END):
            body.append(self.parse_statement())
        self.consume(TokenType.END)
        return ForBlock(variable=variable, iterable=iterable, body=body)

    SHAPE_TOKEN_TYPES = {
        TokenType.BOX,
        TokenType.SPHERE,
        TokenType.CYLINDER,
        TokenType.PLANE,
        TokenType.LIGHT,
        TokenType.CAMERA,
    }

    SCENE_ATTR_NAMES = {
        "size", "color", "pos", "rotation", "scale", "type", "intensity", "texture", "click",
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
                    f"at line {shape_token.line}, col {shape_token.column}"
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
                    body = raw[1:-1] if len(raw) >= 2 and raw[0] in ('"', "'") else raw
                    attrs[name] = Literal(value_type="Text", value=body)
                elif self.match(TokenType.NUMBER):
                    num_tok = self.consume(TokenType.NUMBER)
                    val = float(num_tok.value) if "." in num_tok.value or "e" in num_tok.value.lower() else int(num_tok.value)
                    attrs[name] = Literal(value_type="Number", value=val)
                else:
                    raise SyntaxError(
                        f"Expected a scene attribute value for '{name}' at line "
                        f"{self.peek().line}, col {self.peek().column}"
                    )
            objects.append(SceneObject(shape=shape_token.value, attrs=attrs))
        self.consume(TokenType.END)
        return SceneBlock(objects=objects)

    def parse_expression(self) -> Any:
        return self.parse_binary_expr()

    def parse_binary_expr(self) -> Any:
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        left = self.parse_term()
        while (self.match(TokenType.IS) or self.match(TokenType.GREATER) or
               self.match(TokenType.LESS) or self.match(TokenType.GREATER_OR_EQUAL) or
               self.match(TokenType.LESS_OR_EQUAL)):
            t = self.consume()
            if t.type == TokenType.IS and self.match(TokenType.NOT):
                self.consume(TokenType.NOT)
                op = "is not"
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
        left = self.parse_primary()
        while self.match(TokenType.MULTIPLY) or self.match(TokenType.DIVIDE):
            op_token = self.peek()
            self.consume()
            op = op_token.value
            right = self.parse_primary()
            left = BinaryExpr(op=op, left=left, right=right)
        return left

    def parse_primary(self) -> Any:
        t = self.peek()
        if t.type == TokenType.NUMBER:
            self.consume()
            val = float(t.value) if "." in t.value or "e" in t.value.lower() else int(t.value)
            return Literal(value_type="Number", value=val)
        if t.type == TokenType.TEXT:
            self.consume()
            return Literal(value_type="Text", value=t.value)
        if t.type == TokenType.TRUE:
            self.consume()
            return Literal(value_type="Boolean", value=True)
        if t.type == TokenType.FALSE:
            self.consume()
            return Literal(value_type="Boolean", value=False)
        if t.type == TokenType.NONE:
            self.consume()
            return Literal(value_type="None", value=None)
        if t.type == TokenType.IDENTIFIER:
            name = t.value
            self.consume()
            expr: Any = Identifier(name=name)
            while True:
                if self.match(TokenType.DOT):
                    self.consume(TokenType.DOT)
                    field = self.consume(TokenType.IDENTIFIER).value
                    expr = FieldAccess(object=expr, field=field)
                elif self.match(TokenType.LPAREN):
                    self.consume(TokenType.LPAREN)
                    target_name = dotted_name(expr) or str(expr)
                    if self.match(TokenType.RPAREN):
                        self.consume(TokenType.RPAREN)
                        expr = FunctionCall(name=target_name, args=[])
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
                        expr = StructConstruct(name=target_name, args=args_dict)
                    else:
                        args_list: list[Any] = []
                        while True:
                            args_list.append(self.parse_expression())
                            if self.match(TokenType.COMMA):
                                self.consume(TokenType.COMMA)
                            else:
                                break
                        self.consume(TokenType.RPAREN)
                        expr = FunctionCall(name=target_name, args=args_list)
                else:
                    break
            return expr
        if t.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr
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
            return ListLiteral(items=items)
        raise SyntaxError(f"Unexpected token '{t.value}' of type {t.type} at line {t.line}, col {t.column}")

def parse(tokens: list[Token]) -> Program:
    parser = Parser(tokens)
    return parser.parse()
