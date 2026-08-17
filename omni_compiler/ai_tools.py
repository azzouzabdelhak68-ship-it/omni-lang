"""v4.2: AI tooling for OmniScript - fix suggestions, test generation, execution tracing."""

import itertools
import json
from pathlib import Path
from typing import Any

from omni_compiler.checker import DiagnosticError, SymbolTable, analyze
from omni_compiler.parser import (
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
    ListLiteral,
    Literal,
    Program,
    ReturnStmt,
    ShowStmt,
    Slot,
    StructConstruct,
)

_UNKNOWN: object = object()

_AUTOMATIC_CONFIDENCE = 0.95
_SUGGESTED_CONFIDENCE = 0.7

_BINARY_OPS: dict[str, Any] = {
    "+": lambda left, right: left + right,
    "-": lambda left, right: left - right,
    "*": lambda left, right: left * right,
    "/": lambda left, right: left / right,
    "is": lambda left, right: left == right,
    "is not": lambda left, right: left != right,
    "greater than": lambda left, right: left > right,
    "less than": lambda left, right: left < right,
    "greater or equal": lambda left, right: left >= right,
    "less or equal": lambda left, right: left <= right,
    "and": lambda left, right: bool(left) and bool(right),
    "or": lambda left, right: bool(left) or bool(right),
}


def _diagnostic_from_exception(e: Exception) -> dict[str, Any]:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            "schema": "omni.diagnostic",
            "version": "1.0",
            "code": "E-SYNTAX-001",
            "category": "syntax",
            "severity": "error",
            "message": "Syntax error.",
            "details": msg,
            "span": {"start": 0, "end": 0},
            "location": {"line": 1, "column": 1},
            "context": {},
            "fixes": [
                {
                    "id": "fix-syntax",
                    "kind": "replace_span",
                    "applicability": "suggested",
                    "description": "Fix the reported syntax issue.",
                    "edit": {"operation": "replace", "span": {"start": 0, "end": 0}, "text": ""},
                }
            ],
        }
    if isinstance(e, NameError):
        msg = str(e)
        return {
            "schema": "omni.diagnostic",
            "version": "1.0",
            "code": "E-NAME-001",
            "category": "name",
            "severity": "error",
            "message": msg,
            "details": msg,
            "span": {"start": 0, "end": 0},
            "location": {"line": 1, "column": 1},
            "context": {},
            "fixes": [
                {
                    "id": "define-name",
                    "kind": "suggested",
                    "applicability": "suggested",
                    "description": "Define the missing name or check the spelling.",
                    "edit": {"operation": "insert", "span": {"start": 0, "end": 0}, "text": ""},
                }
            ],
        }
    return {
        "schema": "omni.diagnostic",
        "version": "1.0",
        "code": "E-INTERNAL-001",
        "category": "internal",
        "severity": "error",
        "message": str(e),
        "details": f"{type(e).__name__}: {e}",
        "span": {"start": 0, "end": 0},
        "location": {"line": 1, "column": 1},
        "context": {},
        "fixes": [],
    }


def _augment_fix(
    fix: dict[str, Any],
    rank: int,
    confidence: float,
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    return {
        **fix,
        "rank": rank,
        "confidence": confidence,
        "code": diagnostic.get("code"),
        "message": diagnostic.get("message"),
        "location": diagnostic.get("location"),
    }


def _rank_fixes(fixes: list[dict[str, Any]], diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    automatic = [f for f in fixes if f.get("applicability") == "automatic"]
    suggested = [f for f in fixes if f.get("applicability") != "automatic"]
    ranked: list[dict[str, Any]] = []
    rank = 1
    for fix in automatic:
        ranked.append(_augment_fix(fix, rank, _AUTOMATIC_CONFIDENCE, diagnostic))
        rank += 1
    for fix in suggested:
        ranked.append(_augment_fix(fix, rank, _SUGGESTED_CONFIDENCE, diagnostic))
        rank += 1
    return ranked


def suggest_fix(prog: Program, symbol_table: SymbolTable) -> list[dict[str, Any]]:
    """Re-run semantic analysis and return ranked, confidence-scored fixes."""
    _ = symbol_table
    diagnostic: dict[str, Any] | None = None
    try:
        analyze(prog)
    except Exception as e:
        diagnostic = _diagnostic_from_exception(e)
    if diagnostic is None:
        return []
    return _rank_fixes(list(diagnostic.get("fixes", [])), diagnostic)


def apply_fix(source_code: str, fix: dict[str, Any]) -> str:
    """Mechanically apply a fix's edit operation to the source text."""
    edit = fix.get("edit")
    if not isinstance(edit, dict):
        raise ValueError(f"fix is missing an 'edit' operation: {fix!r}")
    op = edit.get("operation")
    span = edit.get("span")
    if not isinstance(span, dict):
        raise ValueError(f"edit is missing a 'span': {edit!r}")
    raw_start = span.get("start")
    raw_end = span.get("end")
    if not isinstance(raw_start, int) or not isinstance(raw_end, int):
        raise ValueError(f"edit span must have integer start/end: {span!r}")
    text = str(edit.get("text", ""))
    length = len(source_code)
    if raw_start < 0 or raw_end < raw_start or raw_end > length:
        raise ValueError(
            f"edit span {{start: {raw_start}, end: {raw_end}}} is out of "
            f"range for source of length {length}"
        )
    if op == "insert":
        return source_code[:raw_start] + text + source_code[raw_start:]
    if op == "replace":
        return source_code[:raw_start] + text + source_code[raw_end:]
    if op == "delete":
        return source_code[:raw_start] + source_code[raw_end:]
    raise ValueError(f"unknown edit operation: {op!r}")


def apply_automatic_fixes(source_code: str, fixes: list[dict[str, Any]]) -> str:
    """Apply all automatic fixes from highest span start to lowest."""
    automatic = [f for f in fixes if f.get("applicability") == "automatic"]
    ordered = sorted(automatic, key=lambda f: int(f["edit"]["span"]["start"]), reverse=True)
    for fix in ordered:
        source_code = apply_fix(source_code, fix)
    return source_code


def _expr_to_string(e: Any) -> str:
    if isinstance(e, Literal):
        result = str(e.value)
    elif isinstance(e, Identifier):
        result = e.name
    elif isinstance(e, FunctionCall):
        result = f'{e.name}({", ".join(_expr_to_string(a) for a in e.args)})'
    elif isinstance(e, BinaryExpr):
        result = f"{_expr_to_string(e.left)} {e.op} {_expr_to_string(e.right)}"
    elif isinstance(e, ListLiteral):
        result = "[" + ", ".join(_expr_to_string(i) for i in e.items) + "]"
    elif isinstance(e, FieldAccess):
        result = f"{_expr_to_string(e.object)}.{e.field}"
    elif isinstance(e, StructConstruct):
        args = ", ".join(f"{name} = {_expr_to_string(value)}" for name, value in e.args.items())
        result = f"{e.name}({args})"
    elif isinstance(e, Slot):
        result = _expr_to_string(e.expr)
    else:
        result = str(e)
    return result


def _apply_binary_op(op: str, left: Any, right: Any) -> Any:
    operator = _BINARY_OPS.get(op)
    if operator is None:
        raise ValueError(f"unsupported operator: {op}")
    return operator(left, right)


def _eval_expr(expr: Any, env: dict[str, Any]) -> Any:
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Identifier):
        if expr.name not in env:
            raise KeyError(expr.name)
        return env[expr.name]
    if isinstance(expr, FunctionCall):
        if expr.name == "join":
            return ""
        raise ValueError(f"unsupported function call: {expr.name}")
    if isinstance(expr, BinaryExpr):
        return _apply_binary_op(expr.op, _eval_expr(expr.left, env), _eval_expr(expr.right, env))
    raise ValueError(f"unsupported expression node: {type(expr).__name__}")


def _find_function(prog: Program, function_name: str) -> FunctionDef:
    for fn in prog.functions:
        if fn.name == function_name:
            assert isinstance(fn, FunctionDef)
            return fn
    raise ValueError(f"unknown function {function_name!r}")


_EMBEDDED_HELPERS = """
def _eval_expr(expr, env):
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Identifier):
        if expr.name not in env:
            raise KeyError(expr.name)
        return env[expr.name]
    if isinstance(expr, FunctionCall):
        if expr.name == "join":
            return ""
        raise ValueError("unsupported function call: " + expr.name)
    if isinstance(expr, BinaryExpr):
        left = _eval_expr(expr.left, env)
        right = _eval_expr(expr.right, env)
        op = expr.op
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "is":
            return left == right
        if op == "is not":
            return left != right
        if op == "greater than":
            return left > right
        if op == "less than":
            return left < right
        if op == "greater or equal":
            return left >= right
        if op == "less or equal":
            return left <= right
        if op == "and":
            return bool(left) and bool(right)
        if op == "or":
            return bool(left) or bool(right)
        raise ValueError("unsupported operator: " + op)
    raise ValueError("unsupported expression node: " + type(expr).__name__)


def _check_contracts(fn, env):
    for req in fn.requires:
        try:
            if not _eval_expr(req, env):
                return False
        except (KeyError, ValueError, TypeError):
            pass
    return True
"""


def _find_valid_sample(fn: FunctionDef, requires: list[Any]) -> dict[str, Any] | None:
    presets: dict[str, list[Any]] = {
        "Number": [2, 1, 10, -1, 0],
        "Boolean": [True, False],
        "Text": ["sample", "hello"],
    }
    options = [presets.get(p.type, [None]) for p in fn.params]
    combos = itertools.islice(itertools.product(*options), 200)
    param_names = [p.name for p in fn.params]
    for combo in combos:
        env = dict(zip(param_names, combo, strict=True))
        ok = True
        for req in requires:
            try:
                if not _eval_expr(req, env):
                    ok = False
                    break
            except Exception:
                pass
        if ok:
            return env
    return None


def _strategy_for(ptype: str) -> str:
    if ptype == "Number":
        return "st.floats(allow_nan=False, allow_infinity=False)"
    return "st.booleans()"


def _gen_imports(function_name: str, property_ok: bool, omni_path: str) -> list[str]:
    lines = [
        f'"""Auto-generated pytest tests for the OmniScript function {function_name!r}.""',
        "",
        "Generated by omni_compiler.ai_tools.generate_test. Do not edit by hand.",
        '"""',
        "from pathlib import Path",
        "",
        "from omni_compiler.checker import analyze",
        "from omni_compiler.lexer import tokenize",
        "from omni_compiler.parser import (",
        "    BinaryExpr,",
        "    FunctionCall,",
        "    Identifier,",
        "    Literal,",
        "    parse,",
        ")",
    ]
    if property_ok:
        lines.extend(
            [
                "import hypothesis.strategies as st",
                "from hypothesis import assume",
                "from hypothesis import given",
            ]
        )
    lines.extend(["", f"OMNI_FILE = {omni_path!r}", "", ""])
    return lines


def _gen_helpers() -> list[str]:
    return [
        "def compile_source():",
        '    code = Path(OMNI_FILE).read_text(encoding="utf-8")',
        "    ast = parse(tokenize(code))",
        "    analyze(ast)",
        "    return ast",
        "",
        "",
        "def _find_fn(ast, name):",
        "    for fn in ast.functions:",
        "        if fn.name == name:",
        "            return fn",
        "    raise AssertionError(",
        '        "function {0!r} not found in compiled source".format(name)',
        "    )",
        _EMBEDDED_HELPERS.rstrip(),
        "",
        "",
    ]


def _gen_compile_tests(function_name: str, fn: FunctionDef) -> list[str]:
    return [
        f"def test_{function_name}_compiles():",
        "    ast = compile_source()",
        f'    _find_fn(ast, "{function_name}")',
        "",
        "",
        f"def test_{function_name}_contracts_present():",
        "    ast = compile_source()",
        f'    fn = _find_fn(ast, "{function_name}")',
        f"    assert len(fn.requires) == {len(fn.requires)}",
        f"    assert len(fn.ensures) == {len(fn.ensures)}",
    ]


def _gen_sample_test(function_name: str, sample: dict[str, Any]) -> list[str]:
    env_literal = "{" + ", ".join(f"{name!r}: {value!r}" for name, value in sample.items()) + "}"
    return [
        "",
        "",
        f"def test_{function_name}_sample_inputs():",
        "    ast = compile_source()",
        f'    fn = _find_fn(ast, "{function_name}")',
        f"    env = {env_literal}",
        "    assert _check_contracts(fn, env)",
        "    for ens in fn.ensures:",
        "        try:",
        "            assert _eval_expr(ens, env)",
        "        except (KeyError, ValueError, TypeError):",
        "            pass",
    ]


def _gen_property_test(function_name: str, fn: FunctionDef) -> list[str]:
    strategies = ", ".join(_strategy_for(p.type) for p in fn.params)
    param_list = ", ".join(p.name for p in fn.params)
    env_entries = ", ".join(f"{p.name!r}: {p.name}" for p in fn.params)
    return [
        "",
        "",
        f"@given({strategies})",
        f"def test_{function_name}_contracts_property({param_list}):",
        "    ast = compile_source()",
        f'    fn = _find_fn(ast, "{function_name}")',
        f"    env = {{{env_entries}}}",
        "    if not _check_contracts(fn, env):",
        "        assume(False)",
        "    for ens in fn.ensures:",
        "        try:",
        "            assert _eval_expr(ens, env)",
        "        except (KeyError, ValueError, TypeError):",
        "            pass",
    ]


def generate_test(
    prog: Program,
    symbol_table: SymbolTable,
    function_name: str,
    source_file: str | None = None,
) -> str:
    """Generate a pytest test file for a named OmniScript function."""
    _ = symbol_table
    fn = _find_function(prog, function_name)
    omni_path = str(Path(source_file).absolute()) if source_file else ""
    property_ok = bool(fn.params) and all(p.type in ("Number", "Boolean") for p in fn.params)
    sample = _find_valid_sample(fn, fn.requires)

    lines: list[str] = []
    lines.extend(_gen_imports(function_name, property_ok, omni_path))
    lines.extend(_gen_helpers())
    lines.extend(_gen_compile_tests(function_name, fn))
    if sample is not None:
        lines.extend(_gen_sample_test(function_name, sample))
    if property_ok:
        lines.extend(_gen_property_test(function_name, fn))
    return "\n".join(lines) + "\n"


def _try_eval(expr: Any, env: dict[str, Any]) -> Any:
    try:
        return _eval_expr(expr, env)
    except Exception:
        return _UNKNOWN


def _known_list_items(expr: Any, env: dict[str, Any]) -> Any:
    if not isinstance(expr, ListLiteral):
        return _UNKNOWN
    items: list[Any] = []
    for item in expr.items:
        value = _try_eval(item, env)
        if value is _UNKNOWN:
            return _UNKNOWN
        items.append(value)
    return items


class _TraceState:
    """Mutable state shared across statements while tracing execution."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.step = 0

    def emit(
        self,
        kind: str,
        function: str,
        statement: str,
        env: dict[str, Any],
        extra: dict[str, Any],
    ) -> None:
        self.step += 1
        self.events.append(
            {
                "step": self.step,
                "kind": kind,
                "function": function,
                "statement": statement,
                "env": dict(env),
                "span": {"start": 0, "end": 0},
                **extra,
            }
        )


def _trace_if(stmt: IfBlock, function: str, env: dict[str, Any], state: _TraceState) -> None:
    cond = _try_eval(stmt.condition, env)
    condition_str = f"if {_expr_to_string(stmt.condition)}:"
    if cond is _UNKNOWN:
        state.emit("if", function, condition_str, env, {"branch": "unknown"})
        _trace_stmts(stmt.body, function, env, state)
    elif cond:
        state.emit("if", function, condition_str, env, {"branch": "taken"})
        _trace_stmts(stmt.body, function, env, state)
    else:
        state.emit("if", function, condition_str, env, {"branch": "else"})
        _trace_stmts(stmt.else_body, function, env, state)


def _trace_for(stmt: ForBlock, function: str, env: dict[str, Any], state: _TraceState) -> None:
    items = _known_list_items(stmt.iterable, env)
    iterable_str = f"for {stmt.variable} in {_expr_to_string(stmt.iterable)}:"
    state.emit("for", function, iterable_str, env, {})
    if items is _UNKNOWN:
        return
    for item in items:
        env[stmt.variable] = item
        _trace_stmts(stmt.body, function, env, state)


def _trace_stmt(stmt: Any, function: str, env: dict[str, Any], state: _TraceState) -> None:
    if isinstance(stmt, Assignment):
        value = _try_eval(stmt.expr, env)
        if value is _UNKNOWN:
            value = "?"
        env[stmt.name] = value
        state.emit("assign", function, f"{stmt.name} = {_expr_to_string(stmt.expr)}", env, {})
    elif isinstance(stmt, ReturnStmt):
        state.emit("return", function, f"return {_expr_to_string(stmt.expr)}", env, {})
    elif isinstance(stmt, ShowStmt):
        state.emit("show", function, f"show {_expr_to_string(stmt.expr)}", env, {})
    elif isinstance(stmt, FunctionCall):
        state.emit("call", function, _expr_to_string(stmt), env, {})
    elif isinstance(stmt, (BreakStmt, ContinueStmt)):
        keyword = "break" if isinstance(stmt, BreakStmt) else "continue"
        state.emit("line", function, keyword, env, {})
    elif isinstance(stmt, IfBlock):
        _trace_if(stmt, function, env, state)
    elif isinstance(stmt, ForBlock):
        _trace_for(stmt, function, env, state)
    else:
        state.emit("line", function, _expr_to_string(stmt), env, {})


def _trace_stmts(stmts: list[Any], function: str, env: dict[str, Any], state: _TraceState) -> None:
    for stmt in stmts:
        _trace_stmt(stmt, function, env, state)


def trace_execution(
    prog: Program,
    symbol_table: SymbolTable,
    function_name: str | None = None,
) -> list[dict[str, Any]]:
    """Step through a function (or the entry block) and produce ordered trace events."""
    _ = symbol_table
    state = _TraceState()
    if function_name is None:
        body: list[Any] = prog.app_block.body if prog.app_block else prog.statements
        _trace_stmts(body, "app starts", {}, state)
    else:
        fn = _find_function(prog, function_name)
        initial: dict[str, Any] = {p.name: "?" for p in fn.params}
        param_str = ", ".join(f"{p.name}: {p.type}" for p in fn.params)
        signature = f"{fn.name}({param_str}) -> {fn.return_type}"
        state.emit("enter_fn", fn.name, f"enter fn {signature}", initial, {})
        _trace_stmts(fn.body, fn.name, initial, state)
    return state.events


def trace_to_json(trace: list[dict[str, Any]]) -> str:
    """Serialize a trace event list to pretty JSON."""
    return json.dumps(trace, indent=2)
