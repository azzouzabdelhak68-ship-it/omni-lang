"""OmniScript Formatter - produces canonical whitespace/layout for .omni files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omni_compiler.parser import (
    AppBlock,
    Assignment,
    AwaitExpr,
    BinaryExpr,
    BreakStmt,
    ContinueStmt,
    FieldAccess,
    ForBlock,
    FunctionCall,
    FunctionDef,
    GlobalDecl,
    GroupExpr,
    Identifier,
    IfBlock,
    ImportDecl,
    IndexExpr,
    ListLiteral,
    Literal,
    MapLiteral,
    Program,
    ReturnStmt,
    SceneBlock,
    SceneObject,
    ShowStmt,
    Slot,
    StructConstruct,
    TryBlock,
    TypeDecl,
    UnaryExpr,
    WhileBlock,
)


@dataclass
class FormatConfig:
    """Configuration options for the formatter."""

    indent_size: int = 4
    use_tabs: bool = False
    max_line_length: int = 100


class Formatter:
    """Formats an OmniScript AST into canonical source layout."""

    def __init__(self, config: FormatConfig | None = None) -> None:
        """Initialize the formatter with optional custom config."""
        self.config = config or FormatConfig()
        self.indent_level = 0
        self.output: list[str] = []

    def _indent(self) -> str:
        if self.config.use_tabs:
            return '\t' * self.indent_level
        return ' ' * (self.indent_level * self.config.indent_size)

    def _write(self, text: str) -> None:
        self.output.append(text)

    def _writeln(self, text: str = '') -> None:
        self.output.append(text + '\n')

    def format(self, node: Program) -> str:
        """Format an OmniScript program AST to a string."""
        self.output = []
        self.indent_level = 0
        self._format_program(node)
        return ''.join(self.output).rstrip() + '\n'

    def _format_program(self, node: Program) -> None:
        for imp in node.imports:
            self._format_import(imp)
        if node.imports:
            self._writeln()

        for type_decl in node.types:
            self._format_type_decl(type_decl)
        if node.types:
            self._writeln()

        for fn in node.functions:
            self._format_function(fn)
            self._writeln()

        if node.app_block:
            self._format_app_block(node.app_block)
            self._writeln()

        if node.scene_block:
            self._format_scene_block(node.scene_block)
            self._writeln()

        if node.ui_template is not None:
            self._format_ui_block(node.ui_template)

    def _format_import(self, node: ImportDecl) -> None:
        self._writeln(f'import {".".join(node.path)}')

    def _format_type_decl(self, node: TypeDecl) -> None:
        fields = ', '.join(f'{k}: {v}' for k, v in node.fields.items())
        self._writeln(f'type {node.name} = {{ {fields} }}')

    def _format_function(self, node: FunctionDef) -> None:
        params = ', '.join(f'{p.name}: {p.type}' for p in node.params)
        self._writeln(f'fn {node.name}({params}) -> {node.return_type}:')

        # Format effects (uses, reads, writes, pure) - each on its own line, no blank lines between
        if node.effects.get('pure'):
            self.indent_level += 1
            self._writeln(f'{self._indent()}pure')
            self.indent_level -= 1
        else:
            for key in ('uses', 'reads', 'writes', 'borrows'):
                effects = node.effects.get(key, [])
                if isinstance(effects, list) and effects:
                    self.indent_level += 1
                    effect_names = [e[0] if isinstance(e, tuple) else e for e in effects]
                    self._writeln(f'{self._indent()}{key} {" ".join(effect_names)}')
                    self.indent_level -= 1

        # Format requires
        for req in node.requires:
            self.indent_level += 1
            self._writeln(f'{self._indent()}require {self._format_expr(req)}')
            self.indent_level -= 1

        # Format ensures
        for ens in node.ensures:
            self.indent_level += 1
            self._writeln(f'{self._indent()}ensure {self._format_expr(ens)}')
            self.indent_level -= 1

        # Body
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1
        self._writeln(f'{self._indent()}end')

    def _format_app_block(self, node: AppBlock) -> None:
        self._writeln('when app starts:')
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1
        self._writeln('end')

    def _format_scene_block(self, node: SceneBlock) -> None:
        self._writeln('scene:')
        self.indent_level += 1
        for obj in node.objects:
            self._format_scene_object(obj)
        self.indent_level -= 1
        self._writeln('end')

    def _format_scene_object(self, obj: SceneObject) -> None:
        attrs = []
        for key, value in obj.attrs.items():
            if isinstance(value, Slot):
                attrs.append(f'{key}={{{self._format_expr(value.expr)}}}')
            elif isinstance(value, Literal):
                if value.value_type == 'Text':
                    attrs.append(f'{key}="{value.value}"')
                else:
                    attrs.append(f'{key}={value.value}')
            else:
                attrs.append(f'{key}={self._format_expr(value)}')
        self._writeln(f'{self._indent()}{obj.shape} {" ".join(attrs)}')

    def _format_ui_block(self, template: str) -> None:
        self._writeln('UI:')
        self._writeln(template.strip())
        self._writeln('end')

    def _format_statement(self, node: Any) -> None:  # noqa: PLR0912
        if isinstance(node, Assignment):
            self._writeln(f'{self._indent()}{node.name} = {self._format_expr(node.expr)}')
        elif isinstance(node, ReturnStmt):
            if node.expr:
                self._writeln(f'{self._indent()}return {self._format_expr(node.expr)}')
            else:
                self._writeln(f'{self._indent()}return')
        elif isinstance(node, ShowStmt):
            self._writeln(f'{self._indent()}show {self._format_expr(node.expr)}')
        elif isinstance(node, BreakStmt):
            self._writeln(f'{self._indent()}break')
        elif isinstance(node, ContinueStmt):
            self._writeln(f'{self._indent()}continue')
        elif isinstance(node, IfBlock):
            self._format_if_block(node)
        elif isinstance(node, ForBlock):
            self._format_for_block(node)
        elif isinstance(node, WhileBlock):
            self._format_while_block(node)
        elif isinstance(node, TryBlock):
            self._format_try_block(node)
        elif isinstance(node, GlobalDecl):
            self._writeln(f'{self._indent()}global {node.name}')
        elif isinstance(node, FunctionCall):
            self._writeln(f'{self._indent()}{self._format_expr(node)}')
        elif isinstance(node, Assignment):
            self._writeln(f'{self._indent()}{node.name} = {self._format_expr(node.expr)}')
        else:
            # Expression statement
            self._writeln(f'{self._indent()}{self._format_expr(node)}')

    def _format_if_block(self, node: IfBlock) -> None:
        self._writeln(f'{self._indent()}if {self._format_expr(node.condition)}:')
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1
        if node.else_body:
            self._writeln(f'{self._indent()}else:')
            self.indent_level += 1
            for stmt in node.else_body:
                self._format_statement(stmt)
            self.indent_level -= 1
        self._writeln(f'{self._indent()}end')

    def _format_for_block(self, node: ForBlock) -> None:
        var_part = f'{node.variable}: {node.var_type}' if node.var_type else node.variable
        self._writeln(f'{self._indent()}for {var_part} in {self._format_expr(node.iterable)}:')
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1
        self._writeln(f'{self._indent()}end')

    def _format_while_block(self, node: WhileBlock) -> None:
        self._writeln(f'{self._indent()}while {self._format_expr(node.condition)}:')
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1
        self._writeln(f'{self._indent()}end')

    def _format_try_block(self, node: TryBlock) -> None:
        self._writeln(f'{self._indent()}try:')
        self.indent_level += 1
        for stmt in node.body:
            self._format_statement(stmt)
        self.indent_level -= 1

        if node.on_error_body:
            self._writeln(f'{self._indent()}catch:')
            if node.error_var:
                self._writeln(f'{self._indent()}    {node.error_var}')
            self.indent_level += 1
            for stmt in node.on_error_body:
                self._format_statement(stmt)
            self.indent_level -= 1

        if node.finally_body:
            self._writeln(f'{self._indent()}finally:')
            self.indent_level += 1
            for stmt in node.finally_body:
                self._format_statement(stmt)
            self.indent_level -= 1

        self._writeln(f'{self._indent()}end')

    def _format_expr(self, node: Any) -> str:  # noqa: PLR0911, PLR0912
        if node is None:
            return ''

        if isinstance(node, Literal):
            if node.value_type == 'Text':
                # Escape quotes
                val = str(node.value).replace('"', '\\"')
                return f'"{val}"'
            if node.value_type == 'Boolean':
                return 'true' if node.value else 'false'
            if node.value_type == 'None':
                return 'none'
            return str(node.value)

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, BinaryExpr):
            left = self._format_expr(node.left)
            right = self._format_expr(node.right)
            op = node.op
            # Normalize operators
            if op == 'is':
                op = 'is'
            elif op == 'is not':
                op = 'is not'
            return f'{left} {op} {right}'

        if isinstance(node, UnaryExpr):
            operand = self._format_expr(node.operand)
            if node.op == 'not':
                return f'not {operand}'
            if node.op == 'neg':
                return f'-{operand}'
            return f'{node.op}{operand}'

        if isinstance(node, GroupExpr):
            return f'({self._format_expr(node.expr)})'

        if isinstance(node, FunctionCall):
            args = ', '.join(self._format_expr(arg) for arg in node.args)
            return f'{node.name}({args})'

        if isinstance(node, StructConstruct):
            args = ', '.join(f'{k}={self._format_expr(v)}' for k, v in node.args.items())
            return f'{node.name}({args})'

        if isinstance(node, FieldAccess):
            return f'{self._format_expr(node.object)}.{node.field}'

        if isinstance(node, IndexExpr):
            return f'{self._format_expr(node.object)}[{self._format_expr(node.index)}]'

        if isinstance(node, ListLiteral):
            items = ', '.join(self._format_expr(item) for item in node.items)
            return f'[{items}]'

        if isinstance(node, MapLiteral):
            items = ', '.join(f'{k}: {self._format_expr(v)}' for k, v in node.items.items())
            return f'{{{items}}}'

        if isinstance(node, AwaitExpr):
            return f'await {self._format_expr(node.expr)}'

        if isinstance(node, Slot):
            return self._format_expr(node.expr)

        # Fallback for unknown nodes
        return str(node)


def format_source(source: str, config: FormatConfig | None = None) -> str:
    """Format OmniScript source code."""
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    tokens = tokenize(source)
    ast = parse(tokens)
    formatter = Formatter(config)
    return formatter.format(ast)


def format_file(
    path: str, config: FormatConfig | None = None, check: bool = False, diff: bool = False
) -> tuple[bool, str]:
    """Format a file. Returns (changed, formatted_content)."""
    from pathlib import Path  # noqa: PLC0415

    source = Path(path).read_text(encoding='utf-8')
    formatted = format_source(source, config)

    if source == formatted:
        return False, formatted

    if check or diff:
        return True, formatted

    Path(path).write_text(formatted, encoding='utf-8')
    return True, formatted
