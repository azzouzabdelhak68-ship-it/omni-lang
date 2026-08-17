from typing import Any

from omni_compiler.parser import (
    AppBlock,
    Assignment,
    BinaryExpr,
    BreakStmt,
    ContinueStmt,
    FieldAccess,
    ForBlock,
    FunctionCall,
    FunctionDef,
    Identifier,
    IfBlock,
    ImportDecl,
    ListLiteral,
    Literal,
    Program,
    ReturnStmt,
    SceneBlock,
    SceneObject,
    ShowStmt,
    Slot,
    StructConstruct,
    TypeDecl,
)

from omni_compiler.omnisys_registry import (
    is_omnisys_call,
    module_name_of,
    module_names,
    omnisys_effects,
    resolve_import,
)

BUILTIN_CAPABILITIES = {
    "fetch": "network",
    "http_get": "network",
    "http_post": "network",
    "http_request": "network",
    "open_file": "filesystem",
    "read_file": "filesystem",
    "write_file": "filesystem",
    "db_query": "database",
    "read_secret": "secrets",
}

BUILTIN_FUNCTIONS = {
    "join": {
        "kind": "function",
        "type": "fn(List, Text) -> Text",
        "declared_effects": {"uses": [], "reads": [], "writes": []},
        "exported": True,
        "dependencies": [],
    },
}

SCENE_SHAPES = {"box", "sphere", "cylinder", "plane", "light", "camera"}
SCENE_ATTRIBUTES = {"size", "color", "pos", "rotation", "scale", "type", "intensity", "texture", "click"}
SCENE_NUMERIC_ATTRS = {"size", "rotation", "scale", "intensity"}
SCENE_TEXT_ATTRS = {"color", "pos", "texture", "click"}

class DiagnosticError(Exception):
    def __init__(self, code, category, severity, message, details,
                 line=1, column=1, span_start=0, span_end=0, context=None, fixes=None):
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
        return {
            "schema": "omni.diagnostic",
            "version": "1.0",
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "span": {"start": self.span_start, "end": self.span_end},
            "location": {"line": self.line, "column": self.column},
            "context": self.context,
            "fixes": self.fixes,
        }


class SymbolTable:
    def __init__(self):
        self.symbols: dict[str, dict[str, Any]] = {}
        self.scopes: list[set[str]] = [set()]

    def push_scope(self):
        self.scopes.append(set())

    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def define(self, name: str, symbol_info: dict[str, Any]):
        self.symbols[name] = symbol_info
        self.scopes[-1].add(name)

    def lookup(self, name: str) -> dict[str, Any] | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return self.symbols[name]
        if name in self.symbols:
            return self.symbols[name]
        return None

    def inspect_symbol(self, name: str) -> dict[str, Any] | None:
        sym = self.lookup(name)
        if not sym:
            return None
        return {
            "schema": "omni.symbol",
            "version": "1.0",
            "name": name,
            "kind": sym.get("kind", "variable"),
            "type": sym.get("type", "Number"),
            "declared_effects": sym.get("declared_effects", {"uses": [], "reads": [], "writes": []}),
            "span": {"start": sym.get("start", 0), "end": sym.get("end", 0)},
            "location": {"line": sym.get("line", 1), "column": sym.get("column", 1)},
            "dependencies": sym.get("dependencies", []),
            "exported": sym.get("exported", True)
        }


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.loop_depth = 0
        self.custom_types: dict[str, dict[str, str]] = {}
        self.imported_modules: set[str] = set()

    def analyze(self, prog: Program) -> SymbolTable:
        for name, info in BUILTIN_FUNCTIONS.items():
            self.symbol_table.define(name, dict(info))
        for imp in prog.imports:
            self.validate_import(imp)
        for td in prog.types:
            self.analyze_type_decl(td)
        for fn in prog.functions:
            param_types = [p.type for p in fn.params]
            fn_type = f"fn({', '.join(param_types)}) -> {fn.return_type}"
            self.symbol_table.define(fn.name, {
                "kind": "function",
                "type": fn_type,
                "declared_effects": fn.effects,
                "exported": True,
                "dependencies": []
            })

        if prog.app_block:
            self.analyze_app_block(prog.app_block)
            self.enforce_app_block_effects(prog.app_block)

        for fn in prog.functions:
            self.analyze_function(fn)
            self.enforce_function_effects(fn)

        for stmt in prog.statements:
            self.analyze_statement(stmt)

        if prog.scene_block:
            self.analyze_scene_block(prog.scene_block)

        return self.symbol_table

    def validate_import(self, imp: ImportDecl):
        if not imp.path:
            return
        if imp.path[0] != "OMNISYS":
            raise DiagnosticError(
                "E-IMPORT-001", "import", "error",
                f"Unknown import root '{imp.path[0]}'.",
                "Only the OMNISYS platform root may be imported: 'import OMNISYS' or 'import OMNISYS.<module>'.",
                1, 1, 0, 0,
                {"root": imp.path[0]},
                [{
                    "id": "use-omnisys",
                    "kind": "replace_span",
                    "applicability": "automatic",
                    "description": "Replace the import root with 'OMNISYS'.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": "import OMNISYS"}
                }]
            )
        resolved = resolve_import(tuple(imp.path))
        if resolved is None:
            raise DiagnosticError(
                "E-IMPORT-002", "import", "error",
                f"Unknown OMNISYS module '{'.'.join(imp.path)}'.",
                f"The OMNISYS module tree is: {', '.join(sorted(module_names()))}. 'import OMNISYS' alone imports the implicit core root.",
                1, 1, 0, 0,
                {"module": ".".join(imp.path)},
                [{
                    "id": "use-known-module",
                    "kind": "replace_span",
                    "applicability": "automatic",
                    "description": "Use a module from the OMNISYS tree.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": "import OMNISYS.core"}
                }]
            )
        self.imported_modules.add(module_name_of(resolved.js_file))

    def analyze_type_decl(self, td: TypeDecl):
        self.custom_types[td.name] = td.fields
        self.symbol_table.define(td.name, {
            "kind": "type",
            "type": td.name,
            "declared_effects": {"uses": [], "reads": [], "writes": []},
            "exported": True,
            "dependencies": [],
        })
        for ftype in td.fields.values():
            if ftype not in {"Number", "Text", "Boolean", "List", "None"} and ftype not in self.custom_types:
                raise DiagnosticError(
                    "E-TYPE-001", "type", "error",
                    f"Unknown type '{ftype}' in fields of '{td.name}'.",
                    f"The field type '{ftype}' is neither a built-in type nor a declared custom type.",
                    1, 1, 0, 0,
                    {"type": td.name, "field_type": ftype},
                    [{
                        "id": "declare-type",
                        "kind": "add_declaration",
                        "applicability": "suggested",
                        "description": f"Declare a custom type named '{ftype}' or use a built-in type.",
                        "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": f"type {ftype} = {{ }}\n"}
                    }]
                )

    def analyze_scene_block(self, scene: SceneBlock):
        for obj in scene.objects:
            self.analyze_scene_object(obj)

    def analyze_scene_object(self, obj: SceneObject):
        if obj.shape not in SCENE_SHAPES:
            raise DiagnosticError(
                "E-SCENE-001", "scene", "error",
                f"Unknown scene shape '{obj.shape}'.",
                f"'{obj.shape}' is not a built-in shape. Use one of: {', '.join(sorted(SCENE_SHAPES))}.",
                1, 1, 0, 0,
                {"shape": obj.shape},
                [{
                    "id": "use-known-shape",
                    "kind": "replace_span",
                    "applicability": "automatic",
                    "description": f"Replace '{obj.shape}' with a built-in shape such as 'sphere'.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": "sphere"}
                }]
            )
        for name, value in obj.attrs.items():
            if name not in SCENE_ATTRIBUTES:
                raise DiagnosticError(
                    "E-SCENE-002", "scene", "error",
                    f"Unknown attribute '{name}' on scene shape '{obj.shape}'.",
                    f"Supported attributes are: {', '.join(sorted(SCENE_ATTRIBUTES))}.",
                    1, 1, 0, 0,
                    {"shape": obj.shape, "attribute": name},
                    [{
                        "id": "use-known-attribute",
                        "kind": "replace_span",
                        "applicability": "automatic",
                        "description": f"Replace '{name}' with a supported attribute such as 'color'.",
                        "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": "color"}
                    }]
                )
            self._analyze_scene_attr_value(obj, name, value)

    def _analyze_scene_attr_value(self, obj: SceneObject, name: str, value: Any):
        if isinstance(value, Slot):
            self.analyze_expr(value.expr)
            return
        if name in SCENE_TEXT_ATTRS and value.value_type == "Number":
            raise DiagnosticError(
                "E-SCENE-003", "scene", "error",
                f"Attribute '{name}' expects a Text value.",
                f"Scene attribute '{name}' on '{obj.shape}' must be text, got a Number literal.",
                1, 1, 0, 0,
                {"shape": obj.shape, "attribute": name},
                [{
                    "id": "quote-value",
                    "kind": "replace_span",
                    "applicability": "automatic",
                    "description": f"Quote the '{name}' value to make it Text.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": f'"{value.value}"'}
                }]
            )

    def analyze_app_block(self, app_block: AppBlock):
        self.symbol_table.push_scope()
        for stmt in app_block.body:
            self.analyze_statement(stmt)
        self.symbol_table.pop_scope()

    def analyze_function(self, fn: FunctionDef):
        self.symbol_table.push_scope()
        for p in fn.params:
            self.symbol_table.define(p.name, {
                "kind": "parameter",
                "type": p.type,
                "exported": False,
                "dependencies": []
            })
        self.symbol_table.define("result", {
            "kind": "variable",
            "type": fn.return_type,
            "exported": False,
            "dependencies": []
        })

        for req in fn.requires:
            self.analyze_expr(req)
        for ens in fn.ensures:
            self.analyze_expr(ens)
        for stmt in fn.body:
            self.analyze_statement(stmt)
        self.symbol_table.pop_scope()

    def analyze_statement(self, stmt: Any):
        if isinstance(stmt, Assignment):
            self.analyze_expr(stmt.expr)
            self.symbol_table.define(stmt.name, {
                "kind": "variable",
                "type": self._resolve_type_of(stmt.expr),
                "exported": False,
                "dependencies": []
            })
        elif isinstance(stmt, (ShowStmt, ReturnStmt)):
            self.analyze_expr(stmt.expr)
        elif isinstance(stmt, BreakStmt):
            if self.loop_depth == 0:
                raise DiagnosticError(
                    "E-LOOP-001", "loop", "error",
                    "'break' used outside a loop.",
                    "'break' is only valid inside a 'for' block.",
                    1, 1, 0, 0,
                    {},
                    [{
                        "id": "move-break",
                        "kind": "replace_span",
                        "applicability": "suggested",
                        "description": "Move the 'break' inside a 'for' block.",
                        "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
                    }]
                )
        elif isinstance(stmt, ContinueStmt):
            if self.loop_depth == 0:
                raise DiagnosticError(
                    "E-LOOP-002", "loop", "error",
                    "'continue' used outside a loop.",
                    "'continue' is only valid inside a 'for' block.",
                    1, 1, 0, 0,
                    {},
                    [{
                        "id": "move-continue",
                        "kind": "replace_span",
                        "applicability": "suggested",
                        "description": "Move the 'continue' inside a 'for' block.",
                        "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
                    }]
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
            self.symbol_table.define(stmt.variable, {
                "kind": "variable",
                "type": "Number",
                "exported": False,
                "dependencies": []
            })
            self.loop_depth += 1
            for s in stmt.body:
                self.analyze_statement(s)
            self.loop_depth -= 1
            self.symbol_table.pop_scope()
        elif isinstance(stmt, Identifier):
            self.check_identifier(stmt.name)
        elif isinstance(stmt, FunctionCall):
            self.check_identifier(stmt.name)
            for arg in stmt.args:
                self.analyze_expr(arg)
        elif isinstance(stmt, BinaryExpr):
            self.analyze_expr(stmt.left)
            self.analyze_expr(stmt.right)
        elif isinstance(stmt, FieldAccess):
            self.analyze_expr(stmt)
        elif isinstance(stmt, StructConstruct):
            self.analyze_expr(stmt)

    def analyze_expr(self, expr: Any):
        if isinstance(expr, Identifier):
            self.check_identifier(expr.name)
        elif isinstance(expr, FieldAccess):
            self._analyze_field_access(expr)
        elif isinstance(expr, StructConstruct):
            self._analyze_struct_construct(expr)
        elif isinstance(expr, FunctionCall):
            self.check_identifier(expr.name)
            for arg in expr.args:
                self.analyze_expr(arg)
        elif isinstance(expr, BinaryExpr):
            self.analyze_expr(expr.left)
            self.analyze_expr(expr.right)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self.analyze_expr(item)

    def check_identifier(self, name: str):
        if name in BUILTIN_CAPABILITIES or name in BUILTIN_FUNCTIONS or name.startswith("sim."):
            return
        if is_omnisys_call(name):
            parts = name.split(".")
            module = parts[1]
            if module not in self.imported_modules:
                raise DiagnosticError(
                    "E-IMPORT-003", "import", "error",
                    f"OMNISYS module '{module}' used without being imported.",
                    f"Add 'import OMNISYS.{module}' before using 'omnisys.{module}.*'.",
                    1, 1, 0, 0,
                    {"module": module, "call": name},
                    [{
                        "id": "import-module",
                        "kind": "add_declaration",
                        "applicability": "automatic",
                        "description": f"Import OMNISYS.{module}.",
                        "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": f"import OMNISYS.{module}\n"}
                    }]
                )
            return
        if not self.symbol_table.lookup(name):
            raise NameError(f"Undefined variable or function '{name}'")

    def _resolve_type_of(self, expr: Any) -> str:
        if isinstance(expr, StructConstruct):
            return expr.name
        if isinstance(expr, FieldAccess):
            base = self._resolve_type_of(expr.object)
            fields = self.custom_types.get(base)
            if fields is None:
                return "unknown"
            return fields.get(expr.field, "unknown")
        if isinstance(expr, Identifier):
            sym = self.symbol_table.lookup(expr.name)
            if sym and sym.get("kind") == "type":
                return expr.name
            if sym:
                return str(sym.get("type", "Number"))
            return "unknown"
        if isinstance(expr, Literal):
            return expr.value_type
        return "unknown"

    def _analyze_field_access(self, expr: FieldAccess):
        self.analyze_expr(expr.object)
        obj_type = self._resolve_type_of(expr.object)
        fields = self.custom_types.get(obj_type)
        if fields is None:
            raise DiagnosticError(
                "E-TYPE-002", "type", "error",
                f"Cannot access field '{expr.field}' on a non-struct value.",
                f"'{obj_type}' is not a declared custom type, so field access is not allowed.",
                1, 1, 0, 0,
                {"object_type": obj_type, "field": expr.field},
                [{
                    "id": "use-struct",
                    "kind": "replace_span",
                    "applicability": "suggested",
                    "description": "Access fields only on values of a declared custom type.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
                }]
            )
        if expr.field not in fields:
            raise DiagnosticError(
                "E-TYPE-003", "type", "error",
                f"Unknown field '{expr.field}' on type '{obj_type}'.",
                f"'{obj_type}' has no field named '{expr.field}'. Available: {', '.join(fields)}.",
                1, 1, 0, 0,
                {"object_type": obj_type, "field": expr.field},
                [{
                    "id": "use-known-field",
                    "kind": "replace_span",
                    "applicability": "automatic",
                    "description": f"Use one of the declared fields: {', '.join(fields)}.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": next(iter(fields))}
                }]
            )

    def _analyze_struct_construct(self, expr: StructConstruct):
        fields = self.custom_types.get(expr.name)
        if fields is None:
            raise NameError(f"Undefined variable or function '{expr.name}'")
        for arg_name, arg_value in expr.args.items():
            if arg_name not in fields:
                raise DiagnosticError(
                    "E-TYPE-004", "type", "error",
                    f"Unknown field '{arg_name}' in '{expr.name}' construction.",
                    f"'{expr.name}' has no field named '{arg_name}'. Available: {', '.join(fields)}.",
                    1, 1, 0, 0,
                    {"type": expr.name, "field": arg_name},
                    [{
                        "id": "use-known-field",
                        "kind": "replace_span",
                        "applicability": "automatic",
                        "description": f"Use one of the declared fields: {', '.join(fields)}.",
                        "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": next(iter(fields))}
                    }]
                )
            self.analyze_expr(arg_value)
        missing = set(fields) - set(expr.args)
        if missing:
            raise DiagnosticError(
                "E-TYPE-005", "type", "error",
                f"Missing field(s) in '{expr.name}' construction: {', '.join(sorted(missing))}.",
                f"Constructing '{expr.name}' requires all fields: {', '.join(fields)}.",
                1, 1, 0, 0,
                {"type": expr.name, "missing": sorted(missing)},
                [{
                    "id": "add-fields",
                    "kind": "add_declaration",
                    "applicability": "automatic",
                    "description": f"Add the missing field(s): {', '.join(sorted(missing))}.",
                    "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": ""}
                }]
            )

    # ---- Effect enforcement ----

    def enforce_app_block_effects(self, app_block: AppBlock):
        actual = set()
        for stmt in app_block.body:
            self._walk_stmt(stmt, actual, inherit=False, app_scope=True)
        self._enforce("app starts", {"uses": [], "reads": [], "writes": [], "pure": False}, actual)

    def enforce_function_effects(self, fn: FunctionDef):
        actual = set()
        cap = BUILTIN_CAPABILITIES.get(fn.name)
        if cap:
            actual.add(cap)
        for stmt in fn.body:
            self._walk_stmt(stmt, actual, inherit=True, app_scope=False)
        self._enforce(fn.name, fn.effects, actual)

    def _walk_stmt(self, stmt: Any, uses: set[str], inherit: bool, app_scope: bool):
        if isinstance(stmt, (Assignment, ShowStmt, ReturnStmt)):
            self._walk_expr(stmt.expr, uses, inherit, app_scope)
        elif isinstance(stmt, FunctionCall):
            self._walk_call(stmt, uses, inherit, app_scope)
            for arg in stmt.args:
                self._walk_expr(arg, uses, inherit, app_scope)
        elif isinstance(stmt, BinaryExpr):
            self._walk_expr(stmt.left, uses, inherit, app_scope)
            self._walk_expr(stmt.right, uses, inherit, app_scope)
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
        elif isinstance(stmt, ListLiteral):
            for item in stmt.items:
                self._walk_expr(item, uses, inherit, app_scope)

    def _walk_expr(self, expr: Any, uses: set[str], inherit: bool, app_scope: bool):
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
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self._walk_expr(item, uses, inherit, app_scope)

    def _walk_call(self, call: FunctionCall, uses: set[str], inherit: bool, app_scope: bool):
        cap = BUILTIN_CAPABILITIES.get(call.name)
        if cap:
            if not app_scope or self.symbol_table.lookup(call.name) is None:
                uses.add(cap)
        omnisys_uses = omnisys_effects(call.name)
        if omnisys_uses:
            uses.update(omnisys_uses)
        if inherit:
            sym = self.symbol_table.lookup(call.name)
            if sym and sym.get("kind") == "function":
                uses.update(sym.get("declared_effects", {}).get("uses", []))

    def _enforce(self, name: str, declared: dict[str, Any], actual: set[str]):
        declared_uses = set(declared.get("uses", []))
        pure = bool(declared.get("pure", False))

        if pure and actual:
            raise DiagnosticError(
                "E-EFFECT-001", "effect", "error",
                f"Function declared 'pure' but uses {sorted(actual)}",
                f"{name} is declared pure, but its implementation performs effectful work.",
                1, 1, 0, 0,
                {"function": name},
                [{
                    "id": "remove-pure",
                    "kind": "replace_span",
                    "applicability": "suggested",
                    "description": "Declare the capabilities actually used, or remove the pure markers from the effectful function.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""}
                }]
            )

        undeclared = actual - declared_uses
        if undeclared and not pure:
            cap = sorted(undeclared)[0]
            raise DiagnosticError(
                "E-EFFECT-003", "effect", "error",
                f"Capability {cap} used without declaration.",
                f"{name} performs {cap} I/O but declares no capability for it.",
                1, 1, 0, 0,
                {"function": name, "capability": cap},
                [{
                    "id": f"declare-{cap}",
                    "kind": "add_declaration",
                    "applicability": "automatic",
                    "description": f"Add the missing {cap} capability declaration.",
                    "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": f"    uses {cap}\n"}
                }]
            )


def analyze(prog: Program) -> SymbolTable:
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(prog)