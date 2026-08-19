"""Semantic analysis for OmniScript programs."""

import re
from typing import Any

from omni_compiler.omnisys_registry import (
    OMNISYS_MODULES,
    is_omnisys_call,
    module_name_of,
    module_names,
    omnisys_effects,
    resolve_import,
)
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

BUILTIN_CAPABILITIES = {
    'fetch': 'network',
    'http_get': 'network',
    'http_post': 'network',
    'http_request': 'network',
    'open_file': 'filesystem',
    'read_file': 'filesystem',
    'write_file': 'filesystem',
    'db_query': 'database',
    'read_secret': 'secrets',
}

MEMORY_EFFECTS = {'allocates', 'mutates_heap'}

BUILTIN_FUNCTIONS = {
    'join': {
        'kind': 'function',
        'type': 'fn(List, Text) -> Text',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'range': {
        'kind': 'function',
        'type': 'fn(Number) -> List',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'length': {
        'kind': 'function',
        'type': 'fn(Text) -> Number',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'contains': {
        'kind': 'function',
        'type': 'fn(Text, Text) -> Boolean',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'starts_with': {
        'kind': 'function',
        'type': 'fn(Text, Text) -> Boolean',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'ends_with': {
        'kind': 'function',
        'type': 'fn(Text, Text) -> Boolean',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'substring': {
        'kind': 'function',
        'type': 'fn(Text, Number, Number) -> Text',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
    'regex_match': {
        'kind': 'function',
        'type': 'fn(Text, Text) -> Boolean',
        'declared_effects': {'uses': [], 'reads': [], 'writes': []},
        'exported': True,
        'dependencies': [],
    },
}

SCENE_SHAPES = {'box', 'sphere', 'cylinder', 'plane', 'light', 'camera'}
SCENE_ATTRIBUTES = {
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
SCENE_NUMERIC_ATTRS = {'size', 'rotation', 'scale', 'intensity'}
SCENE_TEXT_ATTRS = {'color', 'pos', 'texture', 'click'}


def _assigned_names_ast(stmts: list[Any]) -> set[str]:
    """Recursively collect all assignment targets in an AST statement list.

    Includes names first assigned inside nested if/for blocks and for-loop
    variables.
    """
    names: set[str] = set()
    for stmt in stmts:
        if isinstance(stmt, Assignment):
            names.add(stmt.name)
        elif isinstance(stmt, IfBlock):
            names |= _assigned_names_ast(stmt.body)
            names |= _assigned_names_ast(stmt.else_body)
        elif isinstance(stmt, ForBlock):
            names.add(stmt.variable)
            names |= _assigned_names_ast(stmt.body)
        elif isinstance(stmt, WhileBlock):
            names |= _assigned_names_ast(stmt.body)
        elif isinstance(stmt, TryBlock):
            names |= _assigned_names_ast(stmt.body)
            names |= _assigned_names_ast(stmt.on_error_body)
            names |= _assigned_names_ast(stmt.finally_body)
    return names


def _loop_vars_ast(stmts: list[Any]) -> set[str]:
    """Recursively collect for-loop iteration variable names.

    Loop variables are block-scoped in the emitted code (`for (const v of
    ...)`), so they shadow module-scope names and never count as module reads
    or writes.
    """
    names: set[str] = set()
    for stmt in stmts:
        if isinstance(stmt, ForBlock):
            names.add(stmt.variable)
            names |= _loop_vars_ast(stmt.body)
        elif isinstance(stmt, IfBlock):
            names |= _loop_vars_ast(stmt.body)
            names |= _loop_vars_ast(stmt.else_body)
        elif isinstance(stmt, WhileBlock):
            names |= _loop_vars_ast(stmt.body)
        elif isinstance(stmt, TryBlock):
            names |= _loop_vars_ast(stmt.body)
            names |= _loop_vars_ast(stmt.on_error_body)
            names |= _loop_vars_ast(stmt.finally_body)
    return names


def _param_types_of(sig: str) -> list[str] | None:
    """Extract parameter type list from an ``fn(A, B) -> R`` signature."""
    if not sig.startswith('fn('):
        return None
    body = sig[3:]
    end = body.find(')')
    if end < 0:
        return None
    params_part = body[:end]
    if params_part.strip() == '':
        return []
    return [p.strip() for p in params_part.split(',')]


def _line_of(text: str, pos: int) -> int:
    return text.count('\n', 0, pos) + 1


def _column_of(text: str, pos: int) -> int:
    line_start = text.rfind('\n', 0, pos) + 1
    return pos - line_start + 1


def _is_style_open(html: str, i: int) -> bool:
    """Return True when the ``<style`` open tag begins at ``i`` in ``html``."""
    return html[i : i + 6].lower() == '<style' and (i + 6 >= len(html) or html[i + 6] in '> \t\r\n')


def _is_style_close(html: str, i: int) -> bool:
    """Return True when the ``</style`` close tag begins at ``i`` in ``html``."""
    return html[i : i + 7].lower() == '</style' and (
        i + 7 >= len(html) or html[i + 7] in '> \t\r\n'
    )


def _loc_of(node: Any) -> tuple[int, int, int, int] | None:
    """Return (line, column, span_start, span_end) from an AST node if present."""
    if node is None:
        return None
    line = getattr(node, 'line', None)
    if line is None:
        return None
    return (
        line,
        getattr(node, 'column', 1),
        getattr(node, 'span_start', 0),
        getattr(node, 'span_end', 0),
    )


_LOC_RE = re.compile(r'\bat line (\d+), (?:col|column) (\d+)\b')


def location_from_exception(e: Exception) -> tuple[int, int, int, int]:
    """Extract (line, column, span_start, span_end) from a compiler exception.

    SyntaxError messages from the lexer/parser embed ``at line N, col M``.
    NameError instances raised by the checker carry explicit attributes.
    """
    if isinstance(e, DiagnosticError):
        return e.line, e.column, e.span_start, e.span_end
    if isinstance(e, SyntaxError):
        match = _LOC_RE.search(str(e))
        if match:
            return int(match.group(1)), int(match.group(2)), 0, 0
    line = getattr(e, 'line', None)
    if isinstance(line, int):
        return (
            line,
            int(getattr(e, 'column', 1)),
            int(getattr(e, 'span_start', 0)),
            int(getattr(e, 'span_end', 0)),
        )
    return 1, 1, 0, 0


class DiagnosticError(Exception):
    """Raised when semantic analysis finds a diagnostic issue."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        code: str,
        category: str,
        severity: str,
        message: str,
        details: str,
        line: int = 1,
        column: int = 1,
        span_start: int = 0,
        span_end: int = 0,
        context: dict[str, Any] | None = None,
        fixes: list[Any] | None = None,
    ) -> None:
        """Initialize the diagnostic with code, location, and optional fixes."""
        super().__init__(message)
        self.code = code
        self.category = category
        self.severity = severity
        self.message = message
        self.details = details
        self.line = line
        self.column = column
        self.span_start = span_start
        self.span_end = span_end
        self.context = context or {}
        self.fixes = fixes or []

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diagnostic to a dictionary."""
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': self.code,
            'category': self.category,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'span': {'start': self.span_start, 'end': self.span_end},
            'location': {'line': self.line, 'column': self.column},
            'context': self.context,
            'fixes': self.fixes,
        }


class SymbolTable:
    """A scope-aware symbol table built during semantic analysis."""

    def __init__(self) -> None:
        """Initialize an empty symbol table with a single scope."""
        self.symbols: dict[str, dict[str, Any]] = {}
        self.scopes: list[set[str]] = [set()]

    def push_scope(self) -> None:
        """Push a new nested scope."""
        self.scopes.append(set())

    def pop_scope(self) -> None:
        """Pop the innermost scope, if more than one exists."""
        if len(self.scopes) > 1:
            self.scopes.pop()

    def define(self, name: str, symbol_info: dict[str, Any]) -> None:
        """Define a symbol in the innermost scope."""
        self.symbols[name] = symbol_info
        self.scopes[-1].add(name)

    def lookup(self, name: str) -> dict[str, Any] | None:
        """Look up a symbol from innermost to outermost scope."""
        for scope in reversed(self.scopes):
            if name in scope:
                return self.symbols[name]
        if name in self.symbols:
            return self.symbols[name]
        return None

    def inspect_symbol(self, name: str) -> dict[str, Any] | None:
        """Inspect a symbol and return its serialized form."""
        sym = self.lookup(name)
        if not sym:
            return None
        return {
            'schema': 'omni.symbol',
            'version': '1.0',
            'name': name,
            'kind': sym.get('kind', 'variable'),
            'type': sym.get('type', 'Number'),
            'declared_effects': sym.get(
                'declared_effects', {'uses': [], 'reads': [], 'writes': []}
            ),
            'span': {'start': sym.get('start', 0), 'end': sym.get('end', 0)},
            'location': {'line': sym.get('line', 1), 'column': sym.get('column', 1)},
            'dependencies': sym.get('dependencies', []),
            'exported': sym.get('exported', True),
        }


class SemanticAnalyzer:
    """Performs scope-aware semantic analysis over a parsed program."""

    def __init__(self) -> None:
        """Initialize the analyzer with an empty symbol table."""
        self.symbol_table = SymbolTable()
        self.loop_depth = 0
        self.custom_types: dict[str, dict[str, str]] = {}
        self.imported_modules: set[str] = set()
        self.module_scope: set[str] = set()
        self._provided_caps: set[str] = set()

    def analyze(self, prog: Program) -> SymbolTable:
        """Analyze a program, returning its populated symbol table."""
        for name, info in BUILTIN_FUNCTIONS.items():
            self.symbol_table.define(name, dict(info))
        entry_stmts: list[Any] = []
        if prog.app_block:
            entry_stmts.extend(prog.app_block.body)
        entry_stmts.extend(prog.statements)
        self.module_scope = _assigned_names_ast(entry_stmts)
        for imp in prog.imports:
            self.validate_import(imp)
        for td in prog.types:
            self.analyze_type_decl(td)
        for fn in prog.functions:
            param_types = [p.type for p in fn.params]
            fn_type = f'fn({", ".join(param_types)}) -> {fn.return_type}'
            declared_effects = fn.effects
            if 'uses' in declared_effects:
                declared_effects = {
                    'uses': [cap for cap, _ in declared_effects['uses']],
                    'reads': [cap for cap, _ in declared_effects['reads']],
                    'writes': [cap for cap, _ in declared_effects['writes']],
                    'borrows': [cap for cap, _ in declared_effects['borrows']],
                    'pure': declared_effects.get('pure', False),
                }
            self.symbol_table.define(
                fn.name,
                {
                    'kind': 'function',
                    'type': fn_type,
                    'declared_effects': declared_effects,
                    'exported': True,
                    'dependencies': [],
                },
            )

        if prog.app_block:
            self.analyze_app_block(prog.app_block)
            self.enforce_app_block_effects(prog.app_block)

        if prog.ui_template:
            self.validate_ui_template(prog.ui_template)

        for fn in prog.functions:
            self.analyze_function(fn)
            self.enforce_function_effects(fn)

        for stmt in prog.statements:
            self.analyze_statement(stmt)

        if prog.scene_block:
            self.analyze_scene_block(prog.scene_block)

        return self.symbol_table

    def validate_ui_template(self, template: str) -> None:
        """Validate the ``ui:`` HTML template block.

        Reports unclosed ``{slot}`` placeholders and duplicate/unclosed tags.
        Braces inside ``<style>`` blocks are literal CSS and are skipped.
        """
        i = 0
        in_style = False
        while i < len(template):
            if template[i] == '<':
                if not in_style and _is_style_open(template, i):
                    in_style = True
                elif in_style and _is_style_close(template, i):
                    in_style = False
            if in_style:
                i += 1
                continue
            if template[i] == '{':
                if i + 1 < len(template) and template[i + 1] == '{':
                    i += 2
                    continue
                j = template.find('}', i)
                if j == -1:
                    raise DiagnosticError(
                        'E-UI-001',
                        'ui',
                        'error',
                        "Unclosed '{' in UI template.",
                        "Every '{' in the ui: block must be closed with '}'.",
                        _line_of(template, i),
                        _column_of(template, i),
                        i,
                        i + 1,
                        {},
                        [
                            {
                                'id': 'close-brace',
                                'kind': 'replace_span',
                                'applicability': 'suggested',
                                'description': "Add the missing '}' to close the placeholder.",
                                'edit': {
                                    'operation': 'replace',
                                    'span': {'start': i, 'end': i + 1},
                                    'text': '}',
                                },
                            }
                        ],
                    )
                i = j + 1
                continue
            if template[i] == '}':
                if i + 1 < len(template) and template[i + 1] == '}':
                    i += 2
                    continue
                raise DiagnosticError(
                    'E-UI-002',
                    'ui',
                    'error',
                    "Stray '}' in UI template.",
                    f"Found '}}' at position {i} with no matching '{{'. Use '{{' or '}}' to escape literal braces.",  # noqa: E501
                    _line_of(template, i),
                    _column_of(template, i),
                    i,
                    i + 1,
                    {},
                    [
                        {
                            'id': 'escape-brace',
                            'kind': 'replace_span',
                            'applicability': 'automatic',
                            'description': "Escape the literal brace as '}}'.",
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': i, 'end': i + 1},
                                'text': '}}',
                            },
                        }
                    ],
                )
            i += 1

    def validate_import(self, imp: ImportDecl) -> None:
        """Validate an import declaration."""
        if not imp.path:
            return
        if imp.path[0] != 'OMNISYS':
            raise DiagnosticError(
                'E-IMPORT-001',
                'import',
                'error',
                f"Unknown import root '{imp.path[0]}'.",
                "Only the OMNISYS platform root may be imported: 'import OMNISYS' or 'import OMNISYS.<module>'.",  # noqa: E501
                1,
                1,
                0,
                0,
                {'root': imp.path[0]},
                [
                    {
                        'id': 'use-omnisys',
                        'kind': 'replace_span',
                        'applicability': 'automatic',
                        'description': "Replace the import root with 'OMNISYS'.",
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': 'import OMNISYS',
                        },
                    }
                ],
            )
        resolved = resolve_import(tuple(imp.path))
        if resolved is None:
            raise DiagnosticError(
                'E-IMPORT-002',
                'import',
                'error',
                f"Unknown OMNISYS module '{'.'.join(imp.path)}'.",
                f"The OMNISYS module tree is: {', '.join(sorted(module_names()))}. 'import OMNISYS' alone imports the implicit core root.",  # noqa: E501
                1,
                1,
                0,
                0,
                {'module': '.'.join(imp.path)},
                [
                    {
                        'id': 'use-known-module',
                        'kind': 'replace_span',
                        'applicability': 'automatic',
                        'description': 'Use a module from the OMNISYS tree.',
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': 'import OMNISYS.core',
                        },
                    }
                ],
            )
        self.imported_modules.add(module_name_of(resolved.js_file))

    def analyze_type_decl(self, td: TypeDecl) -> None:
        """Analyze a custom type declaration."""
        self.custom_types[td.name] = td.fields
        self.symbol_table.define(
            td.name,
            {
                'kind': 'type',
                'type': td.name,
                'declared_effects': {'uses': [], 'reads': [], 'writes': []},
                'exported': True,
                'dependencies': [],
            },
        )
        for ftype in td.fields.values():
            if (
                ftype not in {'Number', 'Text', 'Boolean', 'List', 'None'}
                and ftype not in self.custom_types
            ):
                raise DiagnosticError(
                    'E-TYPE-001',
                    'type',
                    'error',
                    f"Unknown type '{ftype}' in fields of '{td.name}'.",
                    f"The field type '{ftype}' is neither a built-in type nor a declared custom type.",  # noqa: E501
                    1,
                    1,
                    0,
                    0,
                    {'type': td.name, 'field_type': ftype},
                    [
                        {
                            'id': 'declare-type',
                            'kind': 'add_declaration',
                            'applicability': 'suggested',
                            'description': f"Declare a custom type named '{ftype}' or use a built-in type.",  # noqa: E501
                            'edit': {
                                'operation': 'insert',
                                'span': {'start': 0, 'end': 0},
                                'text': f'type {ftype} = {{ }}\n',
                            },
                        }
                    ],
                )

    def analyze_scene_block(self, scene: SceneBlock) -> None:
        """Analyze the scene block."""
        for obj in scene.objects:
            self.analyze_scene_object(obj)

    def analyze_scene_object(self, obj: SceneObject) -> None:
        """Analyze a single scene object."""
        if obj.shape not in SCENE_SHAPES:
            raise DiagnosticError(
                'E-SCENE-001',
                'scene',
                'error',
                f"Unknown scene shape '{obj.shape}'.",
                f"'{obj.shape}' is not a built-in shape. Use one of: {', '.join(sorted(SCENE_SHAPES))}.",  # noqa: E501
                1,
                1,
                0,
                0,
                {'shape': obj.shape},
                [
                    {
                        'id': 'use-known-shape',
                        'kind': 'replace_span',
                        'applicability': 'automatic',
                        'description': f"Replace '{obj.shape}' with a built-in shape such as 'sphere'.",  # noqa: E501
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': 'sphere',
                        },
                    }
                ],
            )
        for name, value in obj.attrs.items():
            if name not in SCENE_ATTRIBUTES:
                raise DiagnosticError(
                    'E-SCENE-002',
                    'scene',
                    'error',
                    f"Unknown attribute '{name}' on scene shape '{obj.shape}'.",
                    f'Supported attributes are: {", ".join(sorted(SCENE_ATTRIBUTES))}.',
                    1,
                    1,
                    0,
                    0,
                    {'shape': obj.shape, 'attribute': name},
                    [
                        {
                            'id': 'use-known-attribute',
                            'kind': 'replace_span',
                            'applicability': 'automatic',
                            'description': f"Replace '{name}' with a supported attribute such as 'color'.",  # noqa: E501
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': 'color',
                            },
                        }
                    ],
                )
            self._analyze_scene_attr_value(obj, name, value)

    def _analyze_scene_attr_value(self, obj: SceneObject, name: str, value: Any) -> None:
        if isinstance(value, Slot):
            self.analyze_expr(value.expr)
            return
        if name in SCENE_TEXT_ATTRS and value.value_type == 'Number':
            raise DiagnosticError(
                'E-SCENE-003',
                'scene',
                'error',
                f"Attribute '{name}' expects a Text value.",
                f"Scene attribute '{name}' on '{obj.shape}' must be text, got a Number literal.",
                1,
                1,
                0,
                0,
                {'shape': obj.shape, 'attribute': name},
                [
                    {
                        'id': 'quote-value',
                        'kind': 'replace_span',
                        'applicability': 'automatic',
                        'description': f"Quote the '{name}' value to make it Text.",
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': f'"{value.value}"',
                        },
                    }
                ],
            )

    def analyze_app_block(self, app_block: AppBlock) -> None:
        """Analyze the app entry block."""
        self.symbol_table.push_scope()
        for stmt in app_block.body:
            self.analyze_statement(stmt)
        self.symbol_table.pop_scope()

    def analyze_function(self, fn: FunctionDef) -> None:
        """Analyze a function definition."""
        self.symbol_table.push_scope()
        for p in fn.params:
            self.symbol_table.define(
                p.name, {'kind': 'parameter', 'type': p.type, 'exported': False, 'dependencies': []}
            )
        self.symbol_table.define(
            'result',
            {'kind': 'variable', 'type': fn.return_type, 'exported': False, 'dependencies': []},
        )

        for req in fn.requires:
            self.analyze_expr(req)
        for ens in fn.ensures:
            self.analyze_expr(ens)
        for stmt in fn.body:
            self.analyze_statement(stmt)
        self.symbol_table.pop_scope()

    def analyze_statement(self, stmt: Any) -> None:  # noqa: PLR0912, PLR0915
        """Analyze a single statement node."""
        if isinstance(stmt, Assignment):
            self.analyze_expr(stmt.expr)
            self.symbol_table.define(
                stmt.name,
                {
                    'kind': 'variable',
                    'type': self._resolve_type_of(stmt.expr),
                    'exported': False,
                    'dependencies': [],
                },
            )
        elif isinstance(stmt, (ShowStmt, ReturnStmt)):
            self.analyze_expr(stmt.expr)
        elif isinstance(stmt, BreakStmt):
            if self.loop_depth == 0:
                raise DiagnosticError(
                    'E-LOOP-001',
                    'loop',
                    'error',
                    "'break' used outside a loop.",
                    "'break' is only valid inside a 'for' block.",
                    1,
                    1,
                    0,
                    0,
                    {},
                    [
                        {
                            'id': 'move-break',
                            'kind': 'replace_span',
                            'applicability': 'suggested',
                            'description': "Move the 'break' inside a 'for' block.",
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': '',
                            },
                        }
                    ],
                )
        elif isinstance(stmt, ContinueStmt):
            if self.loop_depth == 0:
                raise DiagnosticError(
                    'E-LOOP-002',
                    'loop',
                    'error',
                    "'continue' used outside a loop.",
                    "'continue' is only valid inside a 'for' block.",
                    1,
                    1,
                    0,
                    0,
                    {},
                    [
                        {
                            'id': 'move-continue',
                            'kind': 'replace_span',
                            'applicability': 'suggested',
                            'description': "Move the 'continue' inside a 'for' block.",
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': '',
                            },
                        }
                    ],
                )
        elif isinstance(stmt, IfBlock):
            self.analyze_expr(stmt.condition)
            for s in stmt.body:
                self.analyze_statement(s)
            for s in stmt.else_body:
                self.analyze_statement(s)
        elif isinstance(stmt, ForBlock):
            self.analyze_expr(stmt.iterable)
            self.symbol_table.push_scope()
            iterable_type = self._resolve_type_of(stmt.iterable)
            if stmt.var_type:
                loop_type = 'any' if stmt.var_type == 'List' else stmt.var_type
            elif iterable_type == 'List':
                loop_type = 'any'
            else:
                loop_type = iterable_type
            self.symbol_table.define(
                stmt.variable,
                {'kind': 'variable', 'type': loop_type, 'exported': False, 'dependencies': []},
            )
            self.loop_depth += 1
            for s in stmt.body:
                self.analyze_statement(s)
            self.loop_depth -= 1
            self.symbol_table.pop_scope()
        elif isinstance(stmt, WhileBlock):
            self.analyze_expr(stmt.condition)
            self.loop_depth += 1
            for s in stmt.body:
                self.analyze_statement(s)
            self.loop_depth -= 1
        elif isinstance(stmt, TryBlock):
            self.symbol_table.push_scope()
            for s in stmt.body:
                self.analyze_statement(s)
            if stmt.error_var:
                self.symbol_table.define(
                    stmt.error_var,
                    {'kind': 'variable', 'type': 'any', 'exported': False, 'dependencies': []},
                )
            for s in stmt.on_error_body:
                self.analyze_statement(s)
            for s in stmt.finally_body:
                self.analyze_statement(s)
            self.symbol_table.pop_scope()
        elif isinstance(stmt, GlobalDecl):
            self.module_scope.add(stmt.name)
            self.symbol_table.define(
                stmt.name,
                {'kind': 'variable', 'type': 'any', 'exported': False, 'dependencies': []},
            )
        elif isinstance(stmt, Identifier):
            self.check_identifier(stmt.name, stmt)
        elif isinstance(stmt, FunctionCall):
            self.check_identifier(stmt.name, stmt)
            for arg in stmt.args:
                self.analyze_expr(arg)
            self._check_call_site(stmt)
            self._check_call_site(stmt)
        elif isinstance(stmt, BinaryExpr):
            self.analyze_expr(stmt.left)
            self.analyze_expr(stmt.right)
        elif isinstance(stmt, GroupExpr):
            self.analyze_expr(stmt.expr)
        elif isinstance(stmt, UnaryExpr):
            self.analyze_expr(stmt.operand)
        elif isinstance(stmt, (FieldAccess, StructConstruct)):
            self.analyze_expr(stmt)

    def analyze_expr(self, expr: Any) -> None:  # noqa: PLR0912
        """Analyze a single expression node."""
        if isinstance(expr, Identifier):
            self.check_identifier(expr.name, expr)
        elif isinstance(expr, FieldAccess):
            self._analyze_field_access(expr)
        elif isinstance(expr, IndexExpr):
            self.analyze_expr(expr.object)
            self.analyze_expr(expr.index)
        elif isinstance(expr, StructConstruct):
            self._analyze_struct_construct(expr)
        elif isinstance(expr, FunctionCall):
            self.check_identifier(expr.name, expr)
            for arg in expr.args:
                self.analyze_expr(arg)
            self._check_call_site(expr)
        elif isinstance(expr, AwaitExpr):
            self.analyze_expr(expr.expr)
        elif isinstance(expr, MapLiteral):
            for value in expr.items.values():
                self.analyze_expr(value)
        elif isinstance(expr, BinaryExpr):
            self.analyze_expr(expr.left)
            self.analyze_expr(expr.right)
            if expr.op == '%':
                left_t = self._resolve_type_of(expr.left)
                right_t = self._resolve_type_of(expr.right)
                numeric = {'Number', 'unknown', 'any'}
                if left_t not in numeric or right_t not in numeric:
                    raise DiagnosticError(
                        'E-TYPE-006',
                        'type',
                        'error',
                        "The '%' operator requires Number operands.",
                        f"Got '{left_t}' and '{right_t}'. Modulo is only defined for numbers.",
                        expr.line,
                        expr.column,
                        expr.span_start,
                        expr.span_end,
                        {},
                        [
                            {
                                'id': 'fix-modulo-operands',
                                'kind': 'replace_span',
                                'applicability': 'suggested',
                                'description': "Convert the operands to Number before using '%'.",
                                'edit': {
                                    'operation': 'replace',
                                    'span': {'start': 0, 'end': 0},
                                    'text': '',
                                },
                            }
                        ],
                    )
        elif isinstance(expr, GroupExpr):
            self.analyze_expr(expr.expr)
        elif isinstance(expr, UnaryExpr):
            self.analyze_expr(expr.operand)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self.analyze_expr(item)

    def _check_call_site(self, call: FunctionCall) -> None:
        """Check arity and parameter types for direct function calls."""
        sym = self.symbol_table.lookup(call.name)
        if sym is None or sym.get('kind') != 'function':
            self._check_omnisys_call_site(call)
            return
        sig = str(sym.get('type', ''))
        param_types = _param_types_of(sig)
        if param_types is None:
            return
        expected = len(param_types)
        actual = len(call.args)
        if actual != expected:
            raise DiagnosticError(
                'E-CALL-001',
                'call',
                'error',
                f"Function '{call.name}' expects {expected} argument(s), got {actual}.",
                f'Signature: {sig}',
                call.line,
                call.column,
                call.span_start,
                call.span_end,
                {'function': call.name, 'expected': expected, 'actual': actual},
                [
                    {
                        'id': 'fix-arity',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': f"Pass exactly {expected} argument(s) to '{call.name}'.",
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )
        for i, (expected_t, arg) in enumerate(zip(param_types, call.args, strict=False)):
            actual_t = self._resolve_type_of(arg)
            if expected_t == 'any' or actual_t == 'unknown':
                continue
            if actual_t not in ('Number', 'Text', 'Boolean', 'List', 'Map', 'None'):
                continue
            if expected_t not in ('Number', 'Text', 'Boolean', 'List', 'Map', 'None'):
                continue
            if actual_t != expected_t:
                raise DiagnosticError(
                    'E-CALL-002',
                    'call',
                    'error',
                    f"Argument {i + 1} to '{call.name}' expects {expected_t}, got {actual_t}.",
                    f'Signature: {sig}',
                    call.line,
                    call.column,
                    call.span_start,
                    call.span_end,
                    {'function': call.name, 'index': i, 'expected': expected_t, 'actual': actual_t},
                    [
                        {
                            'id': 'fix-arg-type',
                            'kind': 'replace_span',
                            'applicability': 'suggested',
                            'description': f'Pass a {expected_t} value as argument {i + 1}.',
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': '',
                            },
                        }
                    ],
                )

    def _check_omnisys_call_site(self, call: FunctionCall) -> None:
        """Check arity and types for OMNISYS standard-library calls."""
        if not is_omnisys_call(call.name):
            return
        parts = call.name.split('.')
        fn = OMNISYS_MODULES[parts[1]].functions[parts[2]]
        param_types = _param_types_of(fn.type)
        if param_types is None:
            return
        expected = len(param_types)
        actual = len(call.args)
        if actual != expected:
            raise DiagnosticError(
                'E-CALL-003',
                'call',
                'error',
                f"OMNISYS call '{call.name}' expects {expected} argument(s), got {actual}.",
                f'Signature: {fn.type}',
                call.line,
                call.column,
                call.span_start,
                call.span_end,
                {'function': call.name, 'expected': expected, 'actual': actual},
                [
                    {
                        'id': 'fix-arity',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': f"Pass exactly {expected} argument(s) to '{call.name}'.",
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )

    def check_identifier(self, name: str, node: Any = None) -> None:  # noqa: PLR0911, PLR0912
        """Check that an identifier is declared and imported."""
        if name in BUILTIN_CAPABILITIES or name in BUILTIN_FUNCTIONS or name.startswith('sim.'):
            return
        if is_omnisys_call(name):
            parts = name.split('.')
            module = parts[1]
            if module not in self.imported_modules:
                loc = _loc_of(node) or (1, 1, 0, 0)
                raise DiagnosticError(
                    'E-IMPORT-003',
                    'import',
                    'error',
                    f"OMNISYS module '{module}' used without being imported.",
                    f"Add 'import OMNISYS.{module}' before using 'omnisys.{module}.*'.",
                    loc[0],
                    loc[1],
                    loc[2],
                    loc[3],
                    {'module': module, 'call': name},
                    [
                        {
                            'id': 'import-module',
                            'kind': 'add_declaration',
                            'applicability': 'automatic',
                            'description': f'Import OMNISYS.{module}.',
                            'edit': {
                                'operation': 'insert',
                                'span': {'start': 0, 'end': 0},
                                'text': f'import OMNISYS.{module}\n',
                            },
                        }
                    ],
                )
            return
        if not self.symbol_table.lookup(name):
            err = NameError(f"Undefined variable or function '{name}'")
            if node is not None:
                setattr(err, 'line', getattr(node, 'line', 1))  # noqa: B010
                setattr(err, 'column', getattr(node, 'column', 1))  # noqa: B010
                setattr(err, 'span_start', getattr(node, 'span_start', 0))  # noqa: B010
                setattr(err, 'span_end', getattr(node, 'span_end', 0))  # noqa: B010
            raise err

    def _resolve_type_of(self, expr: Any) -> str:  # noqa: PLR0911, PLR0912
        if isinstance(expr, GroupExpr):
            return self._resolve_type_of(expr.expr)
        if isinstance(expr, UnaryExpr):
            return self._resolve_type_of(expr.operand)
        if isinstance(expr, AwaitExpr):
            return self._resolve_type_of(expr.expr)
        if isinstance(expr, IndexExpr):
            base = self._resolve_type_of(expr.object)
            if base == 'List':
                return 'any'
            if base == 'Map':
                return 'any'
            return 'unknown'
        if isinstance(expr, MapLiteral):
            return 'Map'
        if isinstance(expr, ListLiteral):
            return 'List'
        if isinstance(expr, StructConstruct):
            return expr.name
        if isinstance(expr, FieldAccess):
            base = self._resolve_type_of(expr.object)
            fields = self.custom_types.get(base)
            if fields is None:
                return 'unknown'
            return fields.get(expr.field, 'unknown')
        if isinstance(expr, Identifier):
            sym = self.symbol_table.lookup(expr.name)
            if sym and sym.get('kind') == 'type':
                return expr.name
            if sym:
                return str(sym.get('type', 'Number'))
            return 'unknown'
        if isinstance(expr, Literal):
            return expr.value_type
        if isinstance(expr, FunctionCall):
            sym = self.symbol_table.lookup(expr.name)
            if sym:
                sig = str(sym.get('type', ''))
                if sig.startswith('fn(') and '->' in sig:
                    return sig.split('->', 1)[1].strip()
            if expr.name in BUILTIN_CAPABILITIES:
                return 'Text'
            return 'unknown'
        return 'unknown'

    def _analyze_field_access(self, expr: FieldAccess) -> None:
        self.analyze_expr(expr.object)
        obj_type = self._resolve_type_of(expr.object)
        fields = self.custom_types.get(obj_type)
        if fields is None:
            raise DiagnosticError(
                'E-TYPE-002',
                'type',
                'error',
                f"Cannot access field '{expr.field}' on a non-struct value.",
                f"'{obj_type}' is not a declared custom type, so field access is not allowed.",
                1,
                1,
                0,
                0,
                {'object_type': obj_type, 'field': expr.field},
                [
                    {
                        'id': 'use-struct',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': 'Access fields only on values of a declared custom type.',
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )
        if expr.field not in fields:
            raise DiagnosticError(
                'E-TYPE-003',
                'type',
                'error',
                f"Unknown field '{expr.field}' on type '{obj_type}'.",
                f"'{obj_type}' has no field named '{expr.field}'. Available: {', '.join(fields)}.",
                1,
                1,
                0,
                0,
                {'object_type': obj_type, 'field': expr.field},
                [
                    {
                        'id': 'use-known-field',
                        'kind': 'replace_span',
                        'applicability': 'automatic',
                        'description': f'Use one of the declared fields: {", ".join(fields)}.',
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': next(iter(fields)),
                        },
                    }
                ],
            )

    def _analyze_struct_construct(self, expr: StructConstruct) -> None:
        fields = self.custom_types.get(expr.name)
        if fields is None:
            raise NameError(f"Undefined variable or function '{expr.name}'")
        for arg_name, arg_value in expr.args.items():
            if arg_name not in fields:
                raise DiagnosticError(
                    'E-TYPE-004',
                    'type',
                    'error',
                    f"Unknown field '{arg_name}' in '{expr.name}' construction.",
                    f"'{expr.name}' has no field named '{arg_name}'. Available: {', '.join(fields)}.",  # noqa: E501
                    1,
                    1,
                    0,
                    0,
                    {'type': expr.name, 'field': arg_name},
                    [
                        {
                            'id': 'use-known-field',
                            'kind': 'replace_span',
                            'applicability': 'automatic',
                            'description': f'Use one of the declared fields: {", ".join(fields)}.',
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': next(iter(fields)),
                            },
                        }
                    ],
                )
            self.analyze_expr(arg_value)
        missing = set(fields) - set(expr.args)
        if missing:
            raise DiagnosticError(
                'E-TYPE-005',
                'type',
                'error',
                f"Missing field(s) in '{expr.name}' construction: {', '.join(sorted(missing))}.",
                f"Constructing '{expr.name}' requires all fields: {', '.join(fields)}.",
                1,
                1,
                0,
                0,
                {'type': expr.name, 'missing': sorted(missing)},
                [
                    {
                        'id': 'add-fields',
                        'kind': 'add_declaration',
                        'applicability': 'automatic',
                        'description': f'Add the missing field(s): {", ".join(sorted(missing))}.',
                        'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
                    }
                ],
            )

    # ---- Effect enforcement ----

    def enforce_app_block_effects(self, app_block: AppBlock) -> None:  # noqa: PLR0912
        """Enforce declared effects in the app block."""
        actual: set[str] = set()
        for stmt in app_block.body:
            self._walk_stmt(stmt, actual, inherit=False, app_scope=True)
        self._enforce('app starts', {'uses': [], 'reads': [], 'writes': [], 'pure': False}, actual)

    def enforce_function_effects(self, fn: FunctionDef) -> None:  # noqa: PLR0912
        """Enforce declared effects in a function."""
        actual: set[str] = set()
        cap = BUILTIN_CAPABILITIES.get(fn.name)
        if cap:
            actual.add(cap)
        for kind in ('uses', 'reads', 'writes', 'borrows'):
            declared = fn.effects.get(kind, [])
            for item in declared if isinstance(declared, list) else []:
                self._provided_caps.add(item if isinstance(item, str) else item[0])
        for stmt in fn.body:
            self._walk_stmt(stmt, actual, inherit=True, app_scope=False)
        reads: set[str] = set()
        writes: set[str] = set()
        param_names = {p.name for p in fn.params}
        # Only loop variables shadow module scope (block-scoped `const` in the
        # emitted code). Names plain-assigned in the function still read/write
        # module resources and must be effect-checked.
        local_names = _loop_vars_ast(fn.body)
        for stmt in fn.body:
            self._walk_data_access(stmt, reads, writes, param_names, local_names)
        self._enforce(fn.name, fn.effects, actual, reads, writes)
        self._provided_caps = set()

    def _walk_stmt(self, stmt: Any, uses: set[str], inherit: bool, app_scope: bool) -> None:  # noqa: PLR0912
        if isinstance(stmt, (Assignment, ShowStmt, ReturnStmt)):
            self._walk_expr(stmt.expr, uses, inherit, app_scope)
        elif isinstance(stmt, FunctionCall):
            self._walk_call(stmt, uses, inherit, app_scope)
            for arg in stmt.args:
                self._walk_expr(arg, uses, inherit, app_scope)
        elif isinstance(stmt, BinaryExpr):
            self._walk_expr(stmt.left, uses, inherit, app_scope)
            self._walk_expr(stmt.right, uses, inherit, app_scope)
        elif isinstance(stmt, GroupExpr):
            self._walk_expr(stmt.expr, uses, inherit, app_scope)
        elif isinstance(stmt, UnaryExpr):
            self._walk_expr(stmt.operand, uses, inherit, app_scope)
        elif isinstance(stmt, IfBlock):
            self._walk_expr(stmt.condition, uses, inherit, app_scope)
            for s in stmt.body:
                self._walk_stmt(s, uses, inherit, app_scope)
            for s in stmt.else_body:
                self._walk_stmt(s, uses, inherit, app_scope)
        elif isinstance(stmt, ForBlock):
            self._walk_expr(stmt.iterable, uses, inherit, app_scope)
            for s in stmt.body:
                self._walk_stmt(s, uses, inherit, app_scope)
        elif isinstance(stmt, WhileBlock):
            self._walk_expr(stmt.condition, uses, inherit, app_scope)
            for s in stmt.body:
                self._walk_stmt(s, uses, inherit, app_scope)
        elif isinstance(stmt, TryBlock):
            for s in stmt.body:
                self._walk_stmt(s, uses, inherit, app_scope)
            for s in stmt.on_error_body:
                self._walk_stmt(s, uses, inherit, app_scope)
            for s in stmt.finally_body:
                self._walk_stmt(s, uses, inherit, app_scope)
        elif isinstance(stmt, ListLiteral):
            for item in stmt.items:
                self._walk_expr(item, uses, inherit, app_scope)
        elif isinstance(stmt, MapLiteral):
            for value in stmt.items.values():
                self._walk_expr(value, uses, inherit, app_scope)
        elif isinstance(stmt, IndexExpr):
            self._walk_expr(stmt.object, uses, inherit, app_scope)
            self._walk_expr(stmt.index, uses, inherit, app_scope)
        elif isinstance(stmt, AwaitExpr):
            self._walk_expr(stmt.expr, uses, inherit, app_scope)

    def _walk_expr(self, expr: Any, uses: set[str], inherit: bool, app_scope: bool) -> None:  # noqa: PLR0912
        if isinstance(expr, FunctionCall):
            self._walk_call(expr, uses, inherit, app_scope)
            for arg in expr.args:
                self._walk_expr(arg, uses, inherit, app_scope)
        elif isinstance(expr, StructConstruct):
            for arg_value in expr.args.values():
                self._walk_expr(arg_value, uses, inherit, app_scope)
        elif isinstance(expr, FieldAccess):
            self._walk_expr(expr.object, uses, inherit, app_scope)
        elif isinstance(expr, BinaryExpr):
            self._walk_expr(expr.left, uses, inherit, app_scope)
            self._walk_expr(expr.right, uses, inherit, app_scope)
        elif isinstance(expr, GroupExpr):
            self._walk_expr(expr.expr, uses, inherit, app_scope)
        elif isinstance(expr, UnaryExpr):
            self._walk_expr(expr.operand, uses, inherit, app_scope)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self._walk_expr(item, uses, inherit, app_scope)
        elif isinstance(expr, MapLiteral):
            for value in expr.items.values():
                self._walk_expr(value, uses, inherit, app_scope)
        elif isinstance(expr, IndexExpr):
            self._walk_expr(expr.object, uses, inherit, app_scope)
            self._walk_expr(expr.index, uses, inherit, app_scope)
        elif isinstance(expr, AwaitExpr):
            self._walk_expr(expr.expr, uses, inherit, app_scope)

    def _walk_data_access(  # noqa: PLR0912
        self,
        stmt: Any,
        reads: set[str],
        writes: set[str],
        param_names: set[str],
        local_names: set[str],
    ) -> None:
        """Collect module-scope identifier reads/writes within a statement."""
        if isinstance(stmt, Assignment):
            if (
                stmt.name in self.module_scope
                and stmt.name not in param_names
                and stmt.name not in local_names
            ):
                writes.add(stmt.name)
            self._walk_expr_data_access(stmt.expr, reads, param_names, local_names)
        elif isinstance(stmt, (ShowStmt, ReturnStmt)):
            self._walk_expr_data_access(stmt.expr, reads, param_names, local_names)
        elif isinstance(stmt, IfBlock):
            self._walk_expr_data_access(stmt.condition, reads, param_names, local_names)
            for s in stmt.body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
            for s in stmt.else_body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
        elif isinstance(stmt, ForBlock):
            self._walk_expr_data_access(stmt.iterable, reads, param_names, local_names)
            for s in stmt.body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
        elif isinstance(stmt, WhileBlock):
            self._walk_expr_data_access(stmt.condition, reads, param_names, local_names)
            for s in stmt.body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
        elif isinstance(stmt, TryBlock):
            for s in stmt.body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
            for s in stmt.on_error_body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
            for s in stmt.finally_body:
                self._walk_data_access(s, reads, writes, param_names, local_names)
        else:
            self._walk_expr_data_access(stmt, reads, param_names, local_names)

    def _walk_expr_data_access(  # noqa: PLR0912
        self,
        expr: Any,
        reads: set[str],
        param_names: set[str],
        local_names: set[str],
    ) -> None:
        """Collect module-scope identifier reads within an expression."""
        if isinstance(expr, Identifier):
            if (
                expr.name in self.module_scope
                and expr.name not in param_names
                and expr.name not in local_names
            ):
                reads.add(expr.name)
        elif isinstance(expr, FunctionCall):
            for a in expr.args:
                self._walk_expr_data_access(a, reads, param_names, local_names)
        elif isinstance(expr, (BinaryExpr,)):
            self._walk_expr_data_access(expr.left, reads, param_names, local_names)
            self._walk_expr_data_access(expr.right, reads, param_names, local_names)
        elif isinstance(expr, UnaryExpr):
            self._walk_expr_data_access(expr.operand, reads, param_names, local_names)
        elif isinstance(expr, GroupExpr):
            self._walk_expr_data_access(expr.expr, reads, param_names, local_names)
        elif isinstance(expr, FieldAccess):
            self._walk_expr_data_access(expr.object, reads, param_names, local_names)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self._walk_expr_data_access(item, reads, param_names, local_names)
        elif isinstance(expr, MapLiteral):
            for value in expr.items.values():
                self._walk_expr_data_access(value, reads, param_names, local_names)
        elif isinstance(expr, IndexExpr):
            self._walk_expr_data_access(expr.object, reads, param_names, local_names)
            self._walk_expr_data_access(expr.index, reads, param_names, local_names)
        elif isinstance(expr, AwaitExpr):
            self._walk_expr_data_access(expr.expr, reads, param_names, local_names)
        elif isinstance(expr, StructConstruct):
            for arg_value in expr.args.values():
                self._walk_expr_data_access(arg_value, reads, param_names, local_names)

    def _walk_call(
        self, call: FunctionCall, uses: set[str], inherit: bool, app_scope: bool
    ) -> None:
        cap = BUILTIN_CAPABILITIES.get(call.name)
        if cap and (not app_scope or self.symbol_table.lookup(call.name) is None):
            uses.add(cap)
        omnisys_uses = omnisys_effects(call.name)
        if omnisys_uses:
            uses.update(omnisys_uses)
        if inherit:
            sym = self.symbol_table.lookup(call.name)
            if sym and sym.get('kind') == 'function':
                declared_effects = sym.get('declared_effects', {})
                declared_uses = declared_effects.get('uses', [])
                # Handle both old format (strings) and new format (tuples)
                uses.update({cap if isinstance(cap, str) else cap[0] for cap in declared_uses})
                # Capability delegation: a callee that borrows capabilities must
                # receive them from the caller for the duration of the call. The
                # caller must provide each borrowed cap via its own uses/reads/
                # writes clauses or by re-borrowing it.
                borrowed = declared_effects.get('borrows', [])
                if borrowed:
                    borrowed_caps = {cap if isinstance(cap, str) else cap[0] for cap in borrowed}
                    missing = borrowed_caps - self._provided_caps
                    if missing:
                        cap_missing = sorted(missing)[0]
                        raise DiagnosticError(
                            'E-EFFECT-012',
                            'effect',
                            'error',
                            f"Capability {cap_missing} borrowed by '{call.name}' not provided by caller.",  # noqa: E501
                            f"'{call.name}' declares 'borrows {cap_missing}', so every call site must "  # noqa: E501
                            f"provide it via 'uses', 'reads', 'writes', or its own 'borrows'.",
                            call.line,
                            call.column,
                            call.span_start,
                            call.span_end,
                            {'function': call.name, 'capability': cap_missing},
                            [
                                {
                                    'id': f'provide-{cap_missing}',
                                    'kind': 'add_declaration',
                                    'applicability': 'automatic',
                                    'description': f'Declare the borrowed capability {cap_missing} on the caller.',  # noqa: E501
                                    'edit': {
                                        'operation': 'insert',
                                        'span': {'start': 0, 'end': 0},
                                        'text': f'    borrows {cap_missing}\n',
                                    },
                                }
                            ],
                        )
                    # The borrow was satisfied by the caller; record it as used so
                    # the borrowed token is considered exercised by delegation.
                    uses.update(borrowed_caps)

    def _enforce(
        self,
        name: str,
        declared: dict[str, Any],
        actual: set[str],
        actual_reads: set[str] | None = None,
        actual_writes: set[str] | None = None,
    ) -> None:
        # Extract capability names from parameterized effects (tuples) or old format (strings)
        def extract_caps(effects_list: list[Any]) -> set[str]:
            return {cap if isinstance(cap, str) else cap[0] for cap in effects_list}

        declared_uses = extract_caps(declared.get('uses', []))
        declared_borrows = extract_caps(declared.get('borrows', []))
        declared_caps = (
            declared_uses
            | declared_borrows
            | extract_caps(declared.get('reads', []))
            | extract_caps(declared.get('writes', []))
        )
        pure = bool(declared.get('pure', False))

        if pure and declared_borrows:
            raise DiagnosticError(
                'E-EFFECT-010',
                'effect',
                'error',
                f"Function '{name}' declares 'borrows' but is marked 'pure'.",
                'Borrowed capabilities are effectful; a pure function cannot borrow capabilities.',
                1,
                1,
                0,
                0,
                {'function': name},
                [
                    {
                        'id': 'remove-pure-or-borrows',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': "Remove either the 'pure' marker or the 'borrows' clauses.",
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )

        if pure and actual:
            raise DiagnosticError(
                'E-EFFECT-001',
                'effect',
                'error',
                f"Function declared 'pure' but uses {sorted(actual)}",
                f'{name} is declared pure, but its implementation performs effectful work.',
                1,
                1,
                0,
                0,
                {'function': name},
                [
                    {
                        'id': 'remove-pure',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': 'Declare the capabilities actually used, or remove the pure markers from the effectful function.',  # noqa: E501
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )

        undeclared = actual - declared_caps
        if undeclared and not pure:
            cap = sorted(undeclared)[0]
            raise DiagnosticError(
                'E-EFFECT-003',
                'effect',
                'error',
                f'Capability {cap} used without declaration.',
                f'{name} performs {cap} I/O but declares no capability for it.',
                1,
                1,
                0,
                0,
                {'function': name, 'capability': cap},
                [
                    {
                        'id': f'declare-{cap}',
                        'kind': 'add_declaration',
                        'applicability': 'automatic',
                        'description': f'Add the missing {cap} capability declaration.',
                        'edit': {
                            'operation': 'insert',
                            'span': {'start': 0, 'end': 0},
                            'text': f'    uses {cap}\n',
                        },
                    }
                ],
            )

        dangling = declared_borrows - actual
        if dangling:
            cap = sorted(dangling)[0]
            raise DiagnosticError(
                'E-EFFECT-011',
                'effect',
                'error',
                f"Function '{name}' borrows {sorted(dangling)} but never uses it.",
                f'A borrowed capability must be exercised inside the function body; '
                f"declaring 'borrows {cap}' without using it is a dangling borrow.",
                1,
                1,
                0,
                0,
                {'function': name, 'capability': cap},
                [
                    {
                        'id': f'use-{cap}',
                        'kind': 'replace_span',
                        'applicability': 'suggested',
                        'description': f'Use {cap} inside the function body, or remove the borrows clause.',  # noqa: E501
                        'edit': {
                            'operation': 'replace',
                            'span': {'start': 0, 'end': 0},
                            'text': '',
                        },
                    }
                ],
            )

        actual_reads = actual_reads or set()
        actual_writes = actual_writes or set()
        declared_reads = extract_caps(declared.get('reads', []))
        declared_writes = extract_caps(declared.get('writes', []))
        undeclared_reads = actual_reads - declared_reads
        undeclared_writes = actual_writes - declared_writes
        if undeclared_reads or undeclared_writes:
            resource = sorted(undeclared_reads | undeclared_writes)[0]
            kind = 'writes' if resource in undeclared_writes else 'reads'
            raise DiagnosticError(
                'E-EFFECT-004',
                'effect',
                'error',
                f"Module data '{resource}' accessed via {kind} without declaration.",
                f"{name} {kind} '{resource}' but does not declare it.",
                1,
                1,
                0,
                0,
                {'function': name, 'resource': resource},
                [
                    {
                        'id': f'declare-{kind}-{resource}',
                        'kind': 'add_declaration',
                        'applicability': 'automatic',
                        'description': f'Add the missing {kind} {resource} declaration.',
                        'edit': {
                            'operation': 'insert',
                            'span': {'start': 0, 'end': 0},
                            'text': f'    {kind} {resource}\n',
                        },
                    }
                ],
            )

        declared_memory = set(declared.get('uses', [])) & MEMORY_EFFECTS
        if declared_memory:
            pass


def analyze(prog: Program) -> SymbolTable:
    """Analyze a program and return its symbol table."""
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(prog)
