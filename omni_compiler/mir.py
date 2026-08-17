"""OMNI MIR (Middle Intermediate Representation) Module
Converts a checked AST into a typed, effect-aware, serializable representation.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from omni_compiler.parser import (
    Assignment,
    BinaryExpr,
    BreakStmt,
    ContinueStmt,
    FieldAccess,
    ForBlock,
    FunctionCall,
    Identifier,
    IfBlock,
    ListLiteral,
    Literal,
    ReturnStmt,
    SceneBlock,
    ShowStmt,
    Slot,
    StructConstruct,
)


@dataclass
class MIRParameter:
    name: str
    type: str


@dataclass
class MIREffects:
    uses: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    pure: bool = False


@dataclass
class MIRFunction:
    name: str
    params: list[MIRParameter] = field(default_factory=list)
    return_type: str = "None"
    effects: MIREffects = field(default_factory=MIREffects)
    body: list[dict[str, Any]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    ensures: list[str] = field(default_factory=list)


@dataclass
class MIRModule:
    schema: str = "omni.mir"
    version: str = "1.0"
    functions: dict[str, MIRFunction] = field(default_factory=dict)
    entry_point: list[dict[str, Any]] = field(default_factory=list)
    ui_template: str | None = None
    scene: list[dict[str, Any]] = field(default_factory=list)
    types: dict[str, dict[str, str]] = field(default_factory=dict)
    imports: list[list[str]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "schema": self.schema,
            "version": self.version,
            "imports": self.imports,
            "functions": {
                name: {
                    "name": fn.name,
                    "params": [{"name": p.name, "type": p.type} for p in fn.params],
                    "return_type": fn.return_type,
                    "effects": {
                        "uses": fn.effects.uses,
                        "reads": fn.effects.reads,
                        "writes": fn.effects.writes,
                        "pure": fn.effects.pure,
                    },
                    "body": fn.body,
                    "requires": fn.requires,
                    "ensures": fn.ensures,
                }
                for name, fn in self.functions.items()
            },
            "entry_point": self.entry_point,
            "ui_template": self.ui_template,
            "scene": self.scene,
            "types": self.types,
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MIRModule":
        data = json.loads(json_str)
        module = cls(schema=data["schema"], version=data["version"])
        for name, fn_data in data.get("functions", {}).items():
            params = [MIRParameter(name=p["name"], type=p["type"]) for p in fn_data.get("params", [])]
            eff = fn_data.get("effects", {})
            effects = MIREffects(
                uses=list(eff.get("uses", [])),
                reads=list(eff.get("reads", [])),
                writes=list(eff.get("writes", [])),
                pure=bool(eff.get("pure", False)),
            )
            fn = MIRFunction(
                name=fn_data["name"],
                params=params,
                return_type=fn_data["return_type"],
                effects=effects,
                body=list(fn_data.get("body", [])),
                requires=list(fn_data.get("requires", [])),
                ensures=list(fn_data.get("ensures", [])),
            )
            module.functions[name] = fn
        module.entry_point = list(data.get("entry_point", []))
        module.ui_template = data.get("ui_template")
        module.scene = list(data.get("scene", []))
        module.types = dict(data.get("types", {}))
        module.imports = [list(p) for p in data.get("imports", [])]
        return module


def _expr_to_mir(e: Any) -> dict[str, Any]:
    if isinstance(e, Literal):
        if e.value_type == "Number":
            return {"op": "number", "value": e.value}
        if e.value_type == "Text":
            return {"op": "text", "value": e.value}
        if e.value_type == "Boolean":
            return {"op": "boolean", "value": bool(e.value)}
        if e.value_type == "None":
            return {"op": "none"}
    if isinstance(e, Identifier):
        return {"op": "ident", "name": e.name}
    if isinstance(e, FieldAccess):
        return {"op": "field", "object": _expr_to_mir(e.object), "field": e.field}
    if isinstance(e, StructConstruct):
        return {
            "op": "struct",
            "name": e.name,
            "args": {name: _expr_to_mir(value) for name, value in e.args.items()},
        }
    if isinstance(e, ListLiteral):
        return {"op": "list", "items": [_expr_to_mir(i) for i in e.items]}
    if isinstance(e, FunctionCall):
        return {"op": "call", "name": e.name, "args": [_expr_to_mir(a) for a in e.args]}
    if isinstance(e, BinaryExpr):
        return {"op": e.op, "left": _expr_to_mir(e.left), "right": _expr_to_mir(e.right)}
    raise TypeError(f"Unknown expression node: {e!r}")


def _stmt_to_mir(s: Any) -> dict[str, Any]:
    if isinstance(s, Assignment):
        return {"op": "assign", "name": s.name, "expr": _expr_to_mir(s.expr)}
    if isinstance(s, ReturnStmt):
        return {"op": "return", "expr": _expr_to_mir(s.expr)}
    if isinstance(s, ShowStmt):
        return {"op": "show", "expr": _expr_to_mir(s.expr)}
    if isinstance(s, BreakStmt):
        return {"op": "break"}
    if isinstance(s, ContinueStmt):
        return {"op": "continue"}
    if isinstance(s, IfBlock):
        return {
            "op": "if",
            "cond": _expr_to_mir(s.condition),
            "body": [_stmt_to_mir(x) for x in s.body],
            "else": [_stmt_to_mir(x) for x in s.else_body],
        }
    if isinstance(s, ForBlock):
        return {
            "op": "for",
            "var": s.variable,
            "iterable": _expr_to_mir(s.iterable),
            "body": [_stmt_to_mir(x) for x in s.body],
        }
    if isinstance(s, FunctionCall):
        return _expr_to_mir(s)
    raise TypeError(f"Unknown statement node: {s!r}")


def _expr_to_string(e: Any) -> str:
    if isinstance(e, Literal):
        if e.value_type == "Text":
            return e.value
        return str(e.value)
    if isinstance(e, Identifier):
        return e.name
    if isinstance(e, FunctionCall):
        return f"{e.name}({', '.join(_expr_to_string(a) for a in e.args)})"
    if isinstance(e, BinaryExpr):
        return f"{_expr_to_string(e.left)} {e.op} {_expr_to_string(e.right)}"
    return str(e)


def _scene_attr_to_mir(v: Any) -> dict[str, Any]:
    if isinstance(v, Slot):
        return {"op": "slot", "expr": _expr_to_mir(v.expr)}
    return _expr_to_mir(v)


def _scene_to_mir(scene: SceneBlock) -> list[dict[str, Any]]:
    objects = []
    for obj in scene.objects:
        objects.append({
            "shape": obj.shape,
            "attrs": {name: _scene_attr_to_mir(value) for name, value in obj.attrs.items()},
        })
    return objects


def to_mir(ast: Any, symbol_table: Any = None) -> MIRModule:
    """Convert a checked AST to OMNI MIR."""
    module = MIRModule()

    for fn in ast.functions:
        params = [MIRParameter(name=p.name, type=p.type) for p in fn.params]
        effects = MIREffects(
            uses=list(fn.effects.get("uses", [])),
            reads=list(fn.effects.get("reads", [])),
            writes=list(fn.effects.get("writes", [])),
            pure=bool(fn.effects.get("pure", False)),
        )
        body = [_stmt_to_mir(s) for s in fn.body]
        requires = [_expr_to_string(r) for r in fn.requires]
        ensures = [_expr_to_string(r) for r in fn.ensures]
        module.functions[fn.name] = MIRFunction(
            name=fn.name,
            params=params,
            return_type=fn.return_type,
            effects=effects,
            body=body,
            requires=requires,
            ensures=ensures,
        )

    entry = []
    if ast.app_block:
        entry.extend(_stmt_to_mir(s) for s in ast.app_block.body)
    for s in ast.statements:
        entry.append(_stmt_to_mir(s))
    module.entry_point = entry
    module.ui_template = ast.ui_template
    if ast.scene_block:
        module.scene = _scene_to_mir(ast.scene_block)
    for td in ast.types:
        module.types[td.name] = {"fields": dict(td.fields)}
    module.imports = [list(imp.path) for imp in ast.imports]

    return module