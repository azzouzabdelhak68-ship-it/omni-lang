# OmniScript Compiler Bundle
> Generated from monorepo source. Total files: 15

## File: `omni_compiler\__init__.py`
```python
"""OmniScript Compiler Package."""

```

## File: `omni_compiler\ai_tools.py`
```python
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
    GroupExpr,
    Identifier,
    IfBlock,
    ListLiteral,
    Literal,
    Program,
    ReturnStmt,
    ShowStmt,
    Slot,
    StructConstruct,
    UnaryExpr,
)

_UNKNOWN: object = object()

_AUTOMATIC_CONFIDENCE = 0.95
_SUGGESTED_CONFIDENCE = 0.7

_BINARY_OPS: dict[str, Any] = {
    '+': lambda left, right: left + right,
    '-': lambda left, right: left - right,
    '*': lambda left, right: left * right,
    '/': lambda left, right: left / right,
    'is': lambda left, right: left == right,
    'is not': lambda left, right: left != right,
    'greater than': lambda left, right: left > right,
    'less than': lambda left, right: left < right,
    'greater or equal': lambda left, right: left >= right,
    'less or equal': lambda left, right: left <= right,
    'and': lambda left, right: bool(left) and bool(right),
    'or': lambda left, right: bool(left) or bool(right),
}


def _diagnostic_from_exception(e: Exception) -> dict[str, Any]:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-SYNTAX-001',
            'category': 'syntax',
            'severity': 'error',
            'message': 'Syntax error.',
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'fix-syntax',
                    'kind': 'replace_span',
                    'applicability': 'suggested',
                    'description': 'Fix the reported syntax issue.',
                    'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    if isinstance(e, NameError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-NAME-001',
            'category': 'name',
            'severity': 'error',
            'message': msg,
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'define-name',
                    'kind': 'suggested',
                    'applicability': 'suggested',
                    'description': 'Define the missing name or check the spelling.',
                    'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    return {
        'schema': 'omni.diagnostic',
        'version': '1.0',
        'code': 'E-INTERNAL-001',
        'category': 'internal',
        'severity': 'error',
        'message': str(e),
        'details': f'{type(e).__name__}: {e}',
        'span': {'start': 0, 'end': 0},
        'location': {'line': 1, 'column': 1},
        'context': {},
        'fixes': [],
    }


def _augment_fix(
    fix: dict[str, Any],
    rank: int,
    confidence: float,
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    return {
        **fix,
        'rank': rank,
        'confidence': confidence,
        'code': diagnostic.get('code'),
        'message': diagnostic.get('message'),
        'location': diagnostic.get('location'),
    }


def _rank_fixes(fixes: list[dict[str, Any]], diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    automatic = [f for f in fixes if f.get('applicability') == 'automatic']
    suggested = [f for f in fixes if f.get('applicability') != 'automatic']
    ranked: list[dict[str, Any]] = []
    rank = 1
    for fix in automatic:
        ranked.append(_augment_fix(fix, rank, _AUTOMATIC_CONFIDENCE, diagnostic))
        rank += 1
    for fix in suggested:
        ranked.append(_augment_fix(fix, rank, _SUGGESTED_CONFIDENCE, diagnostic))
        rank += 1
    return ranked


def suggest_fix(prog: Program, symbol_table: SymbolTable | None = None) -> list[dict[str, Any]]:
    """Re-run semantic analysis and return ranked, confidence-scored fixes."""
    _ = symbol_table
    diagnostic: dict[str, Any] | None = None
    try:
        analyze(prog)
    except Exception as e:
        diagnostic = _diagnostic_from_exception(e)
    if diagnostic is None:
        return []
    return _rank_fixes(list(diagnostic.get('fixes', [])), diagnostic)


def apply_fix(source_code: str, fix: dict[str, Any]) -> str:
    """Mechanically apply a fix's edit operation to the source text."""
    edit = fix.get('edit')
    if not isinstance(edit, dict):
        raise ValueError(f"fix is missing an 'edit' operation: {fix!r}")
    op = edit.get('operation')
    span = edit.get('span')
    if not isinstance(span, dict):
        raise ValueError(f"edit is missing a 'span': {edit!r}")
    raw_start = span.get('start')
    raw_end = span.get('end')
    if not isinstance(raw_start, int) or not isinstance(raw_end, int):
        raise ValueError(f'edit span must have integer start/end: {span!r}')
    text = str(edit.get('text', ''))
    length = len(source_code)
    if raw_start < 0 or raw_end < raw_start or raw_end > length:
        raise ValueError(
            f'edit span {{start: {raw_start}, end: {raw_end}}} is out of '
            f'range for source of length {length}'
        )
    if op == 'insert':
        return source_code[:raw_start] + text + source_code[raw_start:]
    if op == 'replace':
        return source_code[:raw_start] + text + source_code[raw_end:]
    if op == 'delete':
        return source_code[:raw_start] + source_code[raw_end:]
    raise ValueError(f'unknown edit operation: {op!r}')


def apply_automatic_fixes(source_code: str, fixes: list[dict[str, Any]]) -> str:
    """Apply all automatic fixes from highest span start to lowest."""
    automatic = [f for f in fixes if f.get('applicability') == 'automatic']
    ordered = sorted(automatic, key=lambda f: int(f['edit']['span']['start']), reverse=True)
    for fix in ordered:
        source_code = apply_fix(source_code, fix)
    return source_code


def _expr_to_string(e: Any) -> str:  # noqa: PLR0912
    if isinstance(e, Literal):
        if e.value_type == 'Text':
            result: str = '"' + e.value.replace('"', '\\"') + '"'
        else:
            result = str(e.value)
    elif isinstance(e, Identifier):
        result = e.name
    elif isinstance(e, FunctionCall):
        result = f'{e.name}({", ".join(_expr_to_string(a) for a in e.args)})'
    elif isinstance(e, BinaryExpr):
        result = f'{_expr_to_string(e.left)} {e.op} {_expr_to_string(e.right)}'
    elif isinstance(e, GroupExpr):
        result = f'({_expr_to_string(e.expr)})'
    elif isinstance(e, UnaryExpr):
        prefix = 'not ' if e.op == 'not' else '-'
        result = prefix + _expr_to_string(e.operand)
    elif isinstance(e, ListLiteral):
        result = '[' + ', '.join(_expr_to_string(i) for i in e.items) + ']'
    elif isinstance(e, FieldAccess):
        result = f'{_expr_to_string(e.object)}.{e.field}'
    elif isinstance(e, StructConstruct):
        args = ', '.join(f'{name} = {_expr_to_string(value)}' for name, value in e.args.items())
        result = f'{e.name}({args})'
    elif isinstance(e, Slot):
        result = _expr_to_string(e.expr)
    else:
        result = str(e)
    return result


def _apply_binary_op(op: str, left: Any, right: Any) -> Any:
    operator = _BINARY_OPS.get(op)
    if operator is None:
        raise ValueError(f'unsupported operator: {op}')
    return operator(left, right)


def _eval_expr(expr: Any, env: dict[str, Any]) -> Any:  # noqa: PLR0911
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Identifier):
        if expr.name not in env:
            raise KeyError(expr.name)
        return env[expr.name]
    if isinstance(expr, FunctionCall):
        if expr.name == 'join':
            return ''
        raise ValueError(f'unsupported function call: {expr.name}')
    if isinstance(expr, BinaryExpr):
        return _apply_binary_op(expr.op, _eval_expr(expr.left, env), _eval_expr(expr.right, env))
    if isinstance(expr, GroupExpr):
        return _eval_expr(expr.expr, env)
    if isinstance(expr, UnaryExpr):
        value = _eval_expr(expr.operand, env)
        if expr.op == 'not':
            return not bool(value)
        if expr.op == 'neg':
            return -value
        raise ValueError(f'unsupported unary operator: {expr.op}')
    raise ValueError(f'unsupported expression node: {type(expr).__name__}')


def _find_function(prog: Program, function_name: str) -> FunctionDef:
    for fn in prog.functions:
        if fn.name == function_name:
            assert isinstance(fn, FunctionDef)
            return fn
    raise ValueError(f'unknown function {function_name!r}')


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
    if isinstance(expr, GroupExpr):
        return _eval_expr(expr.expr, env)
    if isinstance(expr, UnaryExpr):
        value = _eval_expr(expr.operand, env)
        if expr.op == "not":
            return not bool(value)
        if expr.op == "neg":
            return -value
        raise ValueError("unsupported unary operator: " + expr.op)
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
        'Number': [2, 1, 10, -1, 0],
        'Boolean': [True, False],
        'Text': ['sample', 'hello'],
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
    if ptype == 'Number':
        return 'st.floats(allow_nan=False, allow_infinity=False)'
    return 'st.booleans()'


def _gen_imports(function_name: str, property_ok: bool, omni_path: str) -> list[str]:
    lines = [
        f'"""Auto-generated pytest tests for the OmniScript function {function_name!r}.""',
        '',
        'Generated by omni_compiler.ai_tools.generate_test. Do not edit by hand.',
        '"""',
        'from pathlib import Path',
        '',
        'from omni_compiler.checker import analyze',
        'from omni_compiler.lexer import tokenize',
        'from omni_compiler.parser import (',
        '    BinaryExpr,',
        '    FunctionCall,',
        '    GroupExpr,',
        '    Identifier,',
        '    Literal,',
        '    UnaryExpr,',
        '    parse,',
        ')',
    ]
    if property_ok:
        lines.extend(
            [
                'import hypothesis.strategies as st',
                'from hypothesis import assume',
                'from hypothesis import given',
            ]
        )
    lines.extend(['', f'OMNI_FILE = {omni_path!r}', '', ''])
    return lines


def _gen_helpers() -> list[str]:
    return [
        'def compile_source():',
        '    code = Path(OMNI_FILE).read_text(encoding="utf-8")',
        '    ast = parse(tokenize(code))',
        '    analyze(ast)',
        '    return ast',
        '',
        '',
        'def _find_fn(ast, name):',
        '    for fn in ast.functions:',
        '        if fn.name == name:',
        '            return fn',
        '    raise AssertionError(',
        '        "function {0!r} not found in compiled source".format(name)',
        '    )',
        _EMBEDDED_HELPERS.rstrip(),
        '',
        '',
    ]


def _gen_compile_tests(function_name: str, fn: FunctionDef) -> list[str]:
    return [
        f'def test_{function_name}_compiles():',
        '    ast = compile_source()',
        f'    _find_fn(ast, "{function_name}")',
        '',
        '',
        f'def test_{function_name}_contracts_present():',
        '    ast = compile_source()',
        f'    fn = _find_fn(ast, "{function_name}")',
        f'    assert len(fn.requires) == {len(fn.requires)}',
        f'    assert len(fn.ensures) == {len(fn.ensures)}',
    ]


def _gen_sample_test(function_name: str, sample: dict[str, Any]) -> list[str]:
    env_literal = '{' + ', '.join(f'{name!r}: {value!r}' for name, value in sample.items()) + '}'
    return [
        '',
        '',
        f'def test_{function_name}_sample_inputs():',
        '    ast = compile_source()',
        f'    fn = _find_fn(ast, "{function_name}")',
        f'    env = {env_literal}',
        '    assert _check_contracts(fn, env)',
        '    for ens in fn.ensures:',
        '        try:',
        '            assert _eval_expr(ens, env)',
        '        except (KeyError, ValueError, TypeError):',
        '            pass',
    ]


def _gen_property_test(function_name: str, fn: FunctionDef) -> list[str]:
    strategies = ', '.join(_strategy_for(p.type) for p in fn.params)
    param_list = ', '.join(p.name for p in fn.params)
    env_entries = ', '.join(f'{p.name!r}: {p.name}' for p in fn.params)
    return [
        '',
        '',
        f'@given({strategies})',
        f'def test_{function_name}_contracts_property({param_list}):',
        '    ast = compile_source()',
        f'    fn = _find_fn(ast, "{function_name}")',
        f'    env = {{{env_entries}}}',
        '    if not _check_contracts(fn, env):',
        '        assume(False)',
        '    for ens in fn.ensures:',
        '        try:',
        '            assert _eval_expr(ens, env)',
        '        except (KeyError, ValueError, TypeError):',
        '            pass',
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
    omni_path = str(Path(source_file).absolute()) if source_file else ''
    property_ok = bool(fn.params) and all(p.type in ('Number', 'Boolean') for p in fn.params)
    sample = _find_valid_sample(fn, fn.requires)

    lines: list[str] = []
    lines.extend(_gen_imports(function_name, property_ok, omni_path))
    lines.extend(_gen_helpers())
    lines.extend(_gen_compile_tests(function_name, fn))
    if sample is not None:
        lines.extend(_gen_sample_test(function_name, sample))
    if property_ok:
        lines.extend(_gen_property_test(function_name, fn))
    return '\n'.join(lines) + '\n'


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
                'step': self.step,
                'kind': kind,
                'function': function,
                'statement': statement,
                'env': dict(env),
                'span': {'start': 0, 'end': 0},
                **extra,
            }
        )


def _trace_if(stmt: IfBlock, function: str, env: dict[str, Any], state: _TraceState) -> None:
    cond = _try_eval(stmt.condition, env)
    condition_str = f'if {_expr_to_string(stmt.condition)}:'
    if cond is _UNKNOWN:
        state.emit('if', function, condition_str, env, {'branch': 'unknown'})
        _trace_stmts(stmt.body, function, env, state)
    elif cond:
        state.emit('if', function, condition_str, env, {'branch': 'taken'})
        _trace_stmts(stmt.body, function, env, state)
    else:
        state.emit('if', function, condition_str, env, {'branch': 'else'})
        _trace_stmts(stmt.else_body, function, env, state)


def _trace_for(stmt: ForBlock, function: str, env: dict[str, Any], state: _TraceState) -> None:
    items = _known_list_items(stmt.iterable, env)
    iterable_str = f'for {stmt.variable} in {_expr_to_string(stmt.iterable)}:'
    state.emit('for', function, iterable_str, env, {})
    if items is _UNKNOWN:
        return
    for item in items:
        env[stmt.variable] = item
        _trace_stmts(stmt.body, function, env, state)


def _trace_stmt(stmt: Any, function: str, env: dict[str, Any], state: _TraceState) -> None:
    if isinstance(stmt, Assignment):
        value = _try_eval(stmt.expr, env)
        if value is _UNKNOWN:
            value = '?'
        env[stmt.name] = value
        state.emit('assign', function, f'{stmt.name} = {_expr_to_string(stmt.expr)}', env, {})
    elif isinstance(stmt, ReturnStmt):
        state.emit('return', function, f'return {_expr_to_string(stmt.expr)}', env, {})
    elif isinstance(stmt, ShowStmt):
        state.emit('show', function, f'show {_expr_to_string(stmt.expr)}', env, {})
    elif isinstance(stmt, FunctionCall):
        state.emit('call', function, _expr_to_string(stmt), env, {})
    elif isinstance(stmt, (BreakStmt, ContinueStmt)):
        keyword = 'break' if isinstance(stmt, BreakStmt) else 'continue'
        state.emit('line', function, keyword, env, {})
    elif isinstance(stmt, IfBlock):
        _trace_if(stmt, function, env, state)
    elif isinstance(stmt, ForBlock):
        _trace_for(stmt, function, env, state)
    else:
        state.emit('line', function, _expr_to_string(stmt), env, {})


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
        _trace_stmts(body, 'app starts', {}, state)
    else:
        fn = _find_function(prog, function_name)
        initial: dict[str, Any] = {p.name: '?' for p in fn.params}
        param_str = ', '.join(f'{p.name}: {p.type}' for p in fn.params)
        signature = f'{fn.name}({param_str}) -> {fn.return_type}'
        state.emit('enter_fn', fn.name, f'enter fn {signature}', initial, {})
        _trace_stmts(fn.body, fn.name, initial, state)
    return state.events


def trace_to_json(trace: list[dict[str, Any]]) -> str:
    """Serialize a trace event list to pretty JSON."""
    return json.dumps(trace, indent=2)

```

## File: `omni_compiler\c_emitter.py`
```python
# ruff: noqa: Q000, PLR0911, PLR0912, PLR0915, PLR2004
"""C99 Emitter Module with Flecs Adapter and SQLite Support.

Generates typed C99 code from OMNI MIR for native desktop and simulation
targets. The generated code is guarded by ``OMNI_HAVE_FLECS``: when defined
the Flecs C API is used for entities/components/systems; otherwise a plain
deterministic fallback loop runs registered systems, so the emitted file
still compiles without the Flecs library.

SQLite support is enabled via ``OMNI_HAVE_SQLITE`` which links against
the system SQLite3 library.

Floating-point conformance: uses math.h for IEEE 754 compliant operations
including proper handling of division by zero, NaN, infinity, and rounding.
"""

from typing import Any

MIN_QUOTE_LEN = 2

_C_TYPE_MAP = {
    'Number': 'double',
    'Text': 'const char*',
    'Boolean': 'bool',
    'List': 'OmniList',
    'None': 'void',
}


def _c_type(omni_type: str) -> str:
    """Map an OmniScript type to a C type."""
    return _C_TYPE_MAP.get(omni_type, omni_type)


def _c_text(raw: str) -> str:
    """Format a string literal for C."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    return f'"{body}"'


def _expr_type(
    e: dict[str, Any],
    types: dict[str, str],
    custom_types: dict[str, Any],
) -> str:
    """Best-effort static type inference for a MIR expression dict."""
    op = e.get('op')
    if op == 'number':
        return 'Number'
    if op == 'text':
        return 'Text'
    if op == 'boolean':
        return 'Boolean'
    if op == 'none':
        return 'None'
    if op == 'list':
        return 'List'
    if op == 'struct':
        return str(e['name'])
    if op == 'ident':
        return types.get(str(e['name']), 'Number')
    if op == 'group':
        return _expr_type(e.get('expr', {}), types, custom_types)
    if op == 'not':
        return 'Boolean'
    if op == 'neg':
        return 'Number'
    if op == 'field':
        base = _expr_type(e.get('object', {}), types, custom_types)
        fields = custom_types.get(base)
        if fields:
            return str(fields.get(str(e.get('field')), 'Number'))
        return 'Number'
    if op == 'call':
        if e.get('name') == 'join':
            return 'Text'
        return 'Number'
    if op in ('is', 'is not', 'and', 'or'):
        return 'Boolean'
    if op in ('greater than', 'less than', 'greater or equal', 'less or equal'):
        return 'Boolean'
    return 'Number'


def _slot_type(expr_text: str, types: dict[str, str]) -> str:
    """Infer the type of a ``{slot}`` expression embedded in a text literal."""
    slot = expr_text.strip()
    if slot and slot.replace('_', '').isalnum() and not slot[0].isdigit():
        return types.get(slot, 'Number')
    return 'Number'


def _c_text_expr(raw: str, types: dict[str, str], _custom_types: dict[str, Any]) -> str:
    """Render a text literal with ``{slot}`` interpolation as omni_format()."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    fmt_parts: list[str] = []
    args: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i + 1] in '{}.}':
            buf.append(body[i + 1])
            i += 2
        elif body[i] == '{':
            j = body.find('}', i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1 : j]
            if buf:
                fmt_parts.append(''.join(buf).replace('%', '%%'))
                buf = []
            stype = _slot_type(slot, types)
            if stype == 'Text':
                fmt_parts.append('%s')
                args.append(f'((const char*)({slot}))')
            elif stype == 'Boolean':
                fmt_parts.append('%s')
                args.append(f"(({slot}) ? 'true' : 'false')".replace("'", '"'))
            else:
                fmt_parts.append('%f')
                args.append(f'(double)({slot})')
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append(''.join(buf).replace('%', '%%'))
    if not fmt_parts:
        return '""'
    if not args:
        return _c_text(raw)
    fmt = ''.join(fmt_parts)
    return f'omni_format("{fmt}", {", ".join(args)})'


def _c_expr_unary_and_literals(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str | None:
    types = types or {}
    op = e.get('op')
    if op == 'number':
        val = str(e['value'])
        return f'{val}.0' if '.' not in val and 'e' not in val.lower() else val
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return 'NULL'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        if '{' in str(e['value']):
            return _c_text_expr(str(e['value']), types, custom_types)
        return _c_text(str(e['value']))
    if op == 'list':
        items = ', '.join(_c_expr(i, custom_types, types) for i in e['items'])
        return f'omni_make_list((void*[]){{{items}}}, {len(e["items"])})'
    if op == 'map':
        return '// map literal (unsupported in C): omni_map'
    if op == 'index':
        obj = _c_expr(e.get('object', {}), custom_types, types)
        idx = _c_expr(e.get('index', {}), custom_types, types)
        return f'((void**)({obj}).items)[(int)({idx})]'
    if op == 'await':
        return _c_expr(e.get('expr', {}), custom_types, types)
    if op == 'field':
        return f'{_c_expr(e["object"], custom_types, types)}.{e["field"]}'
    if op == 'struct':
        struct_type = e['name']
        fields = ', '.join(
            f'.{k} = {_c_expr(v, custom_types, types)}' for k, v in e['args'].items()
        )
        return f'({struct_type}){{ {fields} }}'
    if op == 'call':
        args = ', '.join(_c_expr(a, custom_types, types) for a in e['args'])
        return f'omni_join({args})' if e['name'] == 'join' else f'{e["name"]}({args})'
    if op == 'group':
        return f'({_c_expr(e["expr"], custom_types, types)})'
    if op == 'not':
        return f'(!{_c_expr(e["operand"], custom_types, types)})'
    if op == 'neg':
        return f'(-{_c_expr(e["operand"], custom_types, types)})'
    return None


def _c_expr(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str:
    unary_res = _c_expr_unary_and_literals(e, custom_types, types)
    if unary_res is not None:
        return unary_res

    op = e.get('op', '')
    left = _c_expr(e['left'], custom_types, types)
    right = _c_expr(e['right'], custom_types, types)

    if op == '/':
        return f'omni_fp_divide({left}, {right})'
    if op == '%':
        return f'omni_fp_modulo({left}, {right})'

    op_map = {
        'is': '==',
        'is not': '!=',
        'and': '&&',
        'or': '||',
        'greater than': '>',
        'less than': '<',
        'greater or equal': '>=',
        'less or equal': '<=',
    }
    cop = op_map.get(op, op)
    return f'({left} {cop} {right})'


def _c_stmt(
    s: dict[str, Any],
    declared_vars: set[str],
    custom_types: dict[str, Any],
    indent: int = 2,
    types: dict[str, str] | None = None,
) -> str:
    if types is None:
        types = {}
    pad = ' ' * indent
    op = s.get('op')
    if op == 'assign':
        var_name = s['name']
        vtype = _expr_type(s['expr'], types, custom_types)
        types[var_name] = vtype
        if var_name not in declared_vars:
            declared_vars.add(var_name)
            return f'{pad}{_c_type(vtype)} {var_name} = {_c_expr(s["expr"], custom_types, types)};'
        return f'{pad}{var_name} = {_c_expr(s["expr"], custom_types, types)};'
    if op == 'return':
        return f'{pad}return {_c_expr(s["expr"], custom_types, types)};'
    if op == 'show':
        return _c_show(s['expr'], custom_types, types, pad)
    if op in ('break', 'continue'):
        return f'{pad}{op};'
    if op == 'if':
        lines = [f'{pad}if ({_c_expr(s["cond"], custom_types, types)}) {{']
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        if s.get('else'):
            lines.append(f'{pad}else {{')
            for st in s['else']:
                lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
            lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'for':
        var = s['var']
        iterable = _c_expr(s['iterable'], custom_types, types)
        elem_type = _list_elem_type(s['iterable'], types, custom_types)
        c_elem = _c_type(elem_type)
        declared_vars.add(var)
        types[var] = elem_type
        lines = [
            f'{pad}for (int _i_{var} = 0; _i_{var} < {iterable}.count; _i_{var}++) {{',
            f'{pad}  {c_elem} {var} = (({c_elem}*){iterable}.items)[_i_{var}];',
        ]
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'{pad}while ({_c_expr(s["cond"], custom_types, types)}) {{']
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'try':
        lines = [
            f'{pad}// try/catch lowered to a return-on-error guard',
            f'{pad}{{',
        ]
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        for st in s.get('on_error', []):
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        if s.get('finally'):
            for st in s['finally']:
                lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        return '\n'.join(lines)
    if op == 'global':
        return f'{pad}// global {s.get("name", "")}'
    if op == 'call':
        return f'{pad}{_c_expr(s, custom_types, types)};'
    return f'{pad}// unknown statement: {s!r}'


def _list_elem_type(
    iterable: dict[str, Any],
    types: dict[str, str],
    custom_types: dict[str, Any],
) -> str:
    """Determine the element type of a list expression (best effort)."""
    if iterable.get('op') == 'list':
        items = iterable.get('items', [])
        if items:
            return _expr_type(items[0], types, custom_types)
        return 'Number'
    if iterable.get('op') == 'ident':
        return types.get(str(iterable['name']), 'Number')
    return 'Number'


def _c_show(
    expr: dict[str, Any], custom_types: dict[str, Any], types: dict[str, str], pad: str
) -> str:
    """Emit a printf statement matching the expression type."""
    vtype = _expr_type(expr, types, custom_types)
    cexpr = _c_expr(expr, custom_types, types)
    if vtype == 'Text':
        return f'{pad}printf("%s\\n", ({cexpr}));'
    if vtype == 'Boolean':
        return f'{pad}printf("%s\\n", ({cexpr}) ? "true" : "false");'
    if vtype in custom_types:
        return f'{pad}// show struct: {cexpr}'
    return f'{pad}printf("%f\\n", (double)({cexpr}));'


def _emit_c_type_decls(custom_types: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        lines.append(f'typedef struct {tname} {{')
        for fname, ftype in fields.items():
            lines.append(f'  {_c_type(ftype)} {fname};')
        lines.append(f'}} {tname};')
        lines.append('')
    return lines


def _component_name(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> str | None:
    """Resolve a sim component item (struct construct or variable) to a type name."""
    if item.get('op') == 'struct':
        return str(item['name'])
    if item.get('op') == 'ident':
        name = str(item['name'])
        if name in constructs:
            return str(constructs[name]['name'])
        return types.get(name)
    return None


def _component_field_values(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    custom_types: dict[str, Any],
) -> list[str]:
    """Extract ordered field values for a component item."""
    construct = item if item.get('op') == 'struct' else constructs.get(str(item.get('name', '')))
    if not construct:
        return []
    return [
        _c_expr(construct['args'][f], custom_types)
        for f in _struct_field_order(construct, custom_types)
    ]


def _component_types_used(
    mir: Any, constructs: dict[str, dict[str, Any]], types: dict[str, str]
) -> list[str]:
    """Return the custom types referenced by sim.* calls in the entry point."""
    used: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get('op') != 'call' or not str(stmt.get('name', '')).startswith('sim.'):
            continue
        for arg in stmt.get('args', []):
            if arg.get('op') != 'list':
                continue
            for item in arg.get('items', []):
                cname = _component_name(item, constructs, types)
                if cname and cname not in used:
                    used.append(cname)
    return used


def _struct_field_order(struct_expr: dict[str, Any], custom_types: dict[str, Any]) -> list[str]:
    """Order the fields of a struct construct by declaration order."""
    name = struct_expr['name']
    fields = custom_types.get(name, {})
    ordered = [f for f in fields if f in struct_expr.get('args', {})]
    for f in struct_expr.get('args', {}):
        if f not in ordered:
            ordered.append(f)
    return ordered


def _emit_sim_lowering(
    mir: Any,
    custom_types: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> tuple[list[str], str | None]:
    """Emit the entry point main body, lowering ``sim.*`` calls to Flecs C.

    Returns ``(body_lines, run_ticks)`` where ``run_ticks`` is the ``sim.run``
    argument (a C expression) or ``None`` when the program never calls
    ``sim.run``. Non-``sim.*`` statements are emitted inline so variable
    declaration order matches source order.
    """
    lines: list[str] = []
    components = _component_types_used(mir, constructs, types)
    fallback_systems: list[str] = []
    entity_specs: list[tuple[str, list[tuple[str, list[str]]]]] = []
    run_ticks: str | None = None
    declared_main: set[str] = set()

    def lower_sim_call(name: str, args: list[dict[str, Any]]) -> None:
        """Lower a top-level ``sim.*`` call statement in place."""
        nonlocal run_ticks
        if name == 'sim.entity' and len(args) >= 2:
            entity_name = _c_text(str(args[0].get('value', 'entity')))
            comps = [a for a in args[1].get('items', []) if _component_name(a, constructs, types)]
            specs = []
            for comp in comps:
                cname = _component_name(comp, constructs, types)
                if not cname:
                    continue
                values = _component_field_values(comp, constructs, custom_types)
                specs.append((cname, values))
            entity_specs.append((entity_name, specs))

        elif name == 'sim.system' and len(args) >= 3:
            sys_name = _c_text(str(args[0].get('value', 'system')))
            fn_name = str(args[1].get('name', '')) if args[1].get('op') == 'ident' else ''
            if fn_name:
                fallback_systems.append(fn_name)
            lines.append('')
            lines.append('  // sim.system: register system to run every tick')
            lines.append('#ifdef OMNI_HAVE_FLECS')
            lines.append(f'  ECS_SYSTEM(world, {fn_name}, EcsOnUpdate, 0);')
            lines.append('#else')
            lines.append(f'  (void){sys_name};')
            lines.append('#endif')
            lines.append('')

        elif name == 'sim.run':
            run_ticks = _c_expr(args[0], custom_types, types) if args else '1'
            lines.append('')
            lines.append(f'  // sim.run({run_ticks}): run the world {run_ticks} ticks')

        elif name == 'sim.query':
            comp = _c_text(str(args[0].get('value', ''))) if args else '""'
            lines.append('')
            lines.append(f'  // sim.query {comp}: entities carrying a component (empty stub)')
            lines.append('')

        else:
            lines.append('')
            lines.append(f'  // sim.{name}: no C lowering yet')
            lines.append('')

    def lower_sim_assign(var: str, expr: dict[str, Any]) -> None:
        """Lower an assignment whose value is a ``sim.*`` call."""
        nonlocal run_ticks
        sim_name = str(expr.get('name', ''))
        args = expr.get('args', [])
        if sim_name == 'sim.query':
            comp = _c_text(str(args[0].get('value', ''))) if args else '""'
            lines.append('')
            lines.append(f'  // sim.query {comp}: entities carrying a component (empty stub)')
            lines.append(f'  OmniList {var} = omni_make_list((void*[]){{}}, 0);')
            lines.append(f'  (void){var};')
            lines.append('')
        elif sim_name == 'sim.run':
            run_ticks = _c_expr(args[0], custom_types, types) if args else '1'
            lines.append('')
            lines.append(f'  // sim.run({run_ticks}): run the world {run_ticks} ticks')
            lines.append(f'  double {var} = 0;')
            lines.append(f'  (void){var};')
            lines.append('')
        else:
            lines.append('')
            lines.append(f'  // {sim_name} result assigned to {var} (no C lowering yet)')
            lines.append(f'  double {var} = 0;')
            lines.append(f'  (void){var};')
            lines.append('')

    for stmt in mir.entry_point:
        op = stmt.get('op')
        if op == 'call' and str(stmt.get('name', '')).startswith('sim.'):
            lower_sim_call(str(stmt['name']), stmt.get('args', []))
            continue
        if (
            op == 'assign'
            and stmt['expr'].get('op') == 'call'
            and str(stmt['expr'].get('name', '')).startswith('sim.')
        ):
            lower_sim_assign(str(stmt['name']), stmt['expr'])
            continue
        lines.append(_c_stmt(stmt, declared_main, custom_types, 2, types))

    for entity_name, specs in entity_specs:
        lines.append('')
        lines.append('  // sim.entity: components -> Flecs')
        lines.append('#ifdef OMNI_HAVE_FLECS')
        var = f'e_entity_{len(entity_specs)}'
        lines.append(f'  ecs_entity_t {var} = ecs_new(world);')
        lines.append(f'  ecs_set_name(world, {var}, {entity_name});')
        for cname, _values in specs:
            lines.append(f'  ecs_set(world, {var}, {cname}, {{{", ".join(_values)}}});')
        lines.append(f'  (void){var};')
        lines.append('#else')
        for cname, _ in specs:
            lines.append(f'  (void){cname};')
        lines.append('#endif')
        lines.append('')

    if components:
        lines.append('  // Flecs component registration')
        lines.append('#ifdef OMNI_HAVE_FLECS')
        for cname in components:
            lines.append(f'  ECS_COMPONENT_DECLARE({cname});')
        for cname in components:
            lines.append(f'  ECS_COMPONENT_DEFINE(world, {cname});')
        lines.append('#endif')
        lines.append('')

    if fallback_systems:
        lines.append('  // deterministic fallback: run registered systems each tick')
        lines.append('#ifndef OMNI_HAVE_FLECS')
        if run_ticks is not None:
            lines.append(f'  for (int _omni_tick = 0; _omni_tick < {run_ticks}; _omni_tick++) {{')
            for fn_name in fallback_systems:
                lines.append(f'    {fn_name}();')
            lines.append('  }')
        else:
            for fn_name in fallback_systems:
                lines.append(f'  {fn_name}();')
        lines.append('#endif')
        lines.append('')

    return lines, run_ticks


def emit_c(mir: Any) -> str:
    """Emit C99 code with Flecs adapter and SQLite support from OMNI MIR."""
    lines: list[str] = [
        '// Generated by OmniScript C Emitter (v3.3)',
        '#include <stdio.h>',
        '#include <stdlib.h>',
        '#include <string.h>',
        '#include <stdbool.h>',
        '#include <stdarg.h>',
        '#include <math.h>',
        '#include "flecs.h"',
        '',
        '#ifdef OMNI_HAVE_SQLITE',
        '#include <sqlite3.h>',
        '#endif',
        '',
        '// IEEE 754 Floating-Point Conformance Helpers',
        'static inline bool omni_fp_is_nan(double x) { return isnan(x); }',
        'static inline bool omni_fp_is_finite(double x) { return isfinite(x); }',
        'static inline bool omni_fp_is_infinite(double x) { return isinf(x); }',
        'static inline double omni_fp_divide(double a, double b) {',
        '  if (b == 0.0) {',
        '    if (a == 0.0) return NAN;',
        '    return copysign(INFINITY, a);',
        '  }',
        '  return a / b;',
        '}',
        'static inline double omni_fp_modulo(double a, double b) {',
        '  if (b == 0.0 || isnan(a) || isnan(b)) return NAN;',
        '  if (isinf(a)) return NAN;',
        '  return fmod(a, b);',
        '}',
        'static inline double omni_fp_neg_zero(void) { return -0.0; }',
        'static inline double omni_fp_copy_sign(double x, double y) { return copysign(x, y); }',
        '',
        'typedef struct {',
        '  void** items;',
        '  int count;',
        '} OmniList;',
        '',
        'static OmniList omni_make_list(void* items[], int count) {',
        '  OmniList l;',
        '  l.items = items;',
        '  l.count = count;',
        '  return l;',
        '}',
        '',
        'static char omni_format_buf[4096];',
        'static char* omni_format(const char* fmt, ...) {',
        '  va_list args;',
        '  va_start(args, fmt);',
        '  vsnprintf(omni_format_buf, sizeof(omni_format_buf), fmt, args);',
        '  va_end(args);',
        '  return omni_format_buf;',
        '}',
        '',
        'static char omni_join_buf[4096];',
        'static const char* omni_join(OmniList list, const char* sep) {',
        "  omni_join_buf[0] = '\\0';",
        '  size_t off = 0;',
        '  const char** items = (const char**)list.items;',
        '  for (int i = 0; i < list.count; i++) {',
        '    if (i > 0) {',
        '      size_t sl = strlen(sep);',
        '      if (off + sl < sizeof(omni_join_buf)) {',
        '        memcpy(omni_join_buf + off, sep, sl); off += sl;',
        '      }',
        '    }',
        '    const char* s = items[i] ? items[i] : "";',
        '    size_t sl = strlen(s);',
        '    if (off + sl < sizeof(omni_join_buf)) {',
        '      memcpy(omni_join_buf + off, s, sl); off += sl;',
        '    }',
        '  }',
        "  omni_join_buf[off] = '\\0';",
        '  return omni_join_buf;',
        '}',
        '',
        '// OMNISYS.async stubs (no-op for C target)',
        'typedef struct {',
        '  void* handle;',
        '  void (*cancel)(void*);',
        '} OmniTask;',
        'static void omni_async_cancel_stub(void* handle) { (void)handle; }',
        'static OmniTask omnisys_async_task(void* fn) { return (OmniTask){ .handle = fn, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_delay(double ms) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_interval(double ms, void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_timeout(double ms, void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_tick(void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static void omnisys_async_cancel(OmniTask task) { if (task.cancel) task.cancel(task.handle); }',  # noqa: E501
        'static void* omnisys_async_await(OmniTask task) { return task.handle; }',
        '',
        '// OMNISYS.pkg — Semantic Versioning & Lockfile Support',
        '// Version struct',
        'typedef struct {',
        '  int major;',
        '  int minor;',
        '  int patch;',
        '  const char* prerelease;',
        '  const char* build;',
        '} OmniVersion;',
        '',
        '// Parse semantic version string into OmniVersion',
        '// Returns 0 on success, -1 on failure',
        'static int omni_pkg_parse_version(const char* version, OmniVersion* out) {',
        '  if (!version || !out) return -1;',
        '  int major = 0, minor = 0, patch = 0;',
        '  const char* p = version;',
        '  char* end;',
        '  major = (int)strtol(p, &end, 10);',
        "  if (end == p || *end != '.') return -1;",
        '  p = end + 1;',
        '  minor = (int)strtol(p, &end, 10);',
        "  if (end == p || *end != '.') return -1;",
        '  p = end + 1;',
        '  patch = (int)strtol(p, &end, 10);',
        '  if (end == p) {',
        '    out->major = major;',
        '    out->minor = minor;',
        '    out->patch = patch;',
        '    out->prerelease = "";',
        '    out->build = "";',
        '    return 0;',
        '  }',
        '  const char* prerelease = "";',
        '  const char* build = "";',
        "  if (*end == '-') {",
        '    p = end + 1;',
        '    prerelease = p;',
        "    while (*p && *p != '+') p++;",
        "    if (*p == '+') {",
        '      p++;',
        '      build = p;',
        '    }',
        "  } else if (*end == '+') {",
        '    p = end + 1;',
        '    build = p;',
        '  }',
        '  out->major = major;',
        '  out->minor = minor;',
        '  out->patch = patch;',
        '  out->prerelease = prerelease;',
        '  out->build = build;',
        '  return 0;',
        '}',
        '',
        '// Compare two versions: -1 if a<b, 0 if a==b, 1 if a>b',
        'static int omni_pkg_cmp_version(const OmniVersion* a, const OmniVersion* b) {',
        '  if (a->major != b->major) return (a->major < b->major) ? -1 : 1;',
        '  if (a->minor != b->minor) return (a->minor < b->minor) ? -1 : 1;',
        '  if (a->patch != b->patch) return (a->patch < b->patch) ? -1 : 1;',
        '  // prerelease < release',
        '  bool a_pre = a->prerelease && a->prerelease[0];',
        '  bool b_pre = b->prerelease && b->prerelease[0];',
        '  if (a_pre != b_pre) return a_pre ? -1 : 1;',
        '  if (a_pre && b_pre) {',
        '    return strcmp(a->prerelease, b->prerelease);',
        '  }',
        '  return 0;',
        '}',
        '',
        '// Check if version satisfies constraint',
        '// Supports: ^ (caret), ~ (tilde), >=, <=, >, <, =, ==, || (union)',
        'static bool omni_pkg_satisfies(const char* version, const char* constraint) {',
        '  if (!version || !constraint) return false;',
        '  OmniVersion v;',
        '  if (omni_pkg_parse_version(version, &v) != 0) return false;',
        '  ',
        '  // Split by || for union constraints',
        '  char constraint_copy[512];',
        '  strncpy(constraint_copy, constraint, sizeof(constraint_copy) - 1);',
        "  constraint_copy[sizeof(constraint_copy) - 1] = '\\0';",
        '  ',
        '  char* part = strtok(constraint_copy, "|");',
        '  while (part) {',
        '    // Trim whitespace',
        "    while (*part == ' ' || *part == '\\t') part++;",
        '    char* end = part + strlen(part) - 1;',
        "    while (end > part && (*end == ' ' || *end == '\\t')) *end-- = '\\0';",
        '    ',
        "    if (part[0] == '^') {",
        '      // Caret: ^1.2.3 := >=1.2.3 <2.0.0 (or <0.3.0 for 0.x)',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part + 1, &target) == 0) {',
        '        OmniVersion upper = target;',
        '        if (target.major == 0) {',
        '          if (target.minor == 0) upper.patch++;',
        '          else upper.minor++;',
        '        } else {',
        '          upper.major++;',
        '        }',
        '        upper.minor = (target.major == 0 && target.minor == 0) ? 0 : upper.minor;',
        '        upper.patch = (target.major == 0 && target.minor == 0) ? upper.patch : 0;',
        '        if (omni_pkg_cmp_version(&v, &target) >= 0 && omni_pkg_cmp_version(&v, &upper) < 0) {',  # noqa: E501
        '          return true;',
        '        }',
        '      }',
        "    } else if (part[0] == '~') {",
        '      // Tilde: ~1.2.3 := >=1.2.3 <1.3.0',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part + 1, &target) == 0) {',
        '        OmniVersion upper = target;',
        '        upper.minor++;',
        '        upper.patch = 0;',
        '        if (omni_pkg_cmp_version(&v, &target) >= 0 && omni_pkg_cmp_version(&v, &upper) < 0) {',  # noqa: E501
        '          return true;',
        '        }',
        '      }',
        '    } else if (strncmp(part, ">=", 2) == 0 || strncmp(part, "<=", 2) == 0 ||',
        '               strncmp(part, ">", 1) == 0 || strncmp(part, "<", 1) == 0 ||',
        '               strncmp(part, "==", 2) == 0 || part[0] == \'=\') {',
        '      // Simple comparison',
        '      const char* op = part;',
        '      const char* ver_str = part;',
        '      if (strncmp(part, ">=", 2) == 0 || strncmp(part, "<=", 2) == 0 || strncmp(part, "==", 2) == 0) {',  # noqa: E501
        '        ver_str = part + 2;',
        "      } else if (part[0] == '>' || part[0] == '<' || part[0] == '=') {",
        '        ver_str = part + 1;',
        '      }',
        "      while (*ver_str == ' ' || *ver_str == '\\t') ver_str++;",
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(ver_str, &target) == 0) {',
        '        int cmp = omni_pkg_cmp_version(&v, &target);',
        "        if ((op[0] == '>' && op[1] == '=' && cmp >= 0) ||",
        "            (op[0] == '<' && op[1] == '=' && cmp <= 0) ||",
        "            (op[0] == '>' && op[1] != '=' && cmp > 0) ||",
        "            (op[0] == '<' && op[1] != '=' && cmp < 0) ||",
        "            ((op[0] == '=' || (op[0] == '=' && op[1] == '=')) && cmp == 0)) {",
        '          return true;',
        '        }',
        '      }',
        '    } else {',
        '      // Bare version = exact match',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part, &target) == 0) {',
        '        if (omni_pkg_cmp_version(&v, &target) == 0) return true;',
        '      }',
        '    }',
        '    part = strtok(NULL, "|");',
        '  }',
        '  return false;',
        '}',
        '',
        '// SHA256 checksum (simplified - uses a basic hash for demo)',
        '// In production, link with OpenSSL or use platform crypto API',
        'static void omni_pkg_compute_checksum(const char* content, char* out, size_t out_size) {',
        '  // Simple FNV-1a hash as placeholder for SHA256',
        '  uint32_t hash = 2166136261u;',
        '  for (size_t i = 0; content[i]; i++) {',
        '    hash ^= (uint8_t)content[i];',
        '    hash *= 16777619u;',
        '  }',
        '  snprintf(out, out_size, "sha256:%08x", hash);',
        '}',
        '',
        '// Lockfile entry',
        'typedef struct {',
        '  const char* name;',
        '  const char* version;',
        '  const char* checksum;',
        '  const char** dep_names;',
        '  const char** dep_versions;',
        '  int dep_count;',
        '} OmniLockfileEntry;',
        '',
        '// Lockfile',
        'typedef struct {',
        '  OmniLockfileEntry* entries;',
        '  int count;',
        '  int capacity;',
        '} OmniLockfile;',
        '',
        'static void omni_lockfile_init(OmniLockfile* lf) {',
        '  lf->entries = NULL;',
        '  lf->count = 0;',
        '  lf->capacity = 0;',
        '}',
        '',
        'static void omni_lockfile_add(OmniLockfile* lf, const char* name, const char* version,',
        '                               const char* checksum, const char** dep_names,',
        '                               const char** dep_versions, int dep_count) {',
        '  if (lf->count >= lf->capacity) {',
        '    lf->capacity = lf->capacity ? lf->capacity * 2 : 4;',
        '    lf->entries = realloc(lf->entries, lf->capacity * sizeof(OmniLockfileEntry));',
        '  }',
        '  OmniLockfileEntry* e = &lf->entries[lf->count++];',
        '  e->name = name;',
        '  e->version = version;',
        '  e->checksum = checksum;',
        '  e->dep_names = dep_names;',
        '  e->dep_versions = dep_versions;',
        '  e->dep_count = dep_count;',
        '}',
        '',
        'static OmniLockfileEntry* omni_lockfile_get(OmniLockfile* lf, const char* name) {',
        '  for (int i = 0; i < lf->count; i++) {',
        '    if (strcmp(lf->entries[i].name, name) == 0) return &lf->entries[i];',
        '  }',
        '  return NULL;',
        '}',
        '',
        'static void omni_lockfile_free(OmniLockfile* lf) {',
        '  free(lf->entries);',
        '  lf->entries = NULL;',
        '  lf->count = 0;',
        '  lf->capacity = 0;',
        '}',
        '',
        '// Package spec for resolution',
        'typedef struct {',
        '  const char* name;',
        '  const char* version_constraint;',
        '  const char** dep_names;',
        '  const char** dep_constraints;',
        '  int dep_count;',
        '  const char* checksum;',
        '} OmniPackageSpec;',
        '',
        '// Resolution result',
        'typedef struct {',
        '  OmniLockfileEntry* packages;',
        '  int count;',
        '  OmniLockfile lockfile;',
        '  const char** warnings;',
        '  int warning_count;',
        '} OmniResolution;',
        '',
        '// Deterministic version resolution (simplified)',
        'static OmniResolution omni_pkg_resolve_versions(OmniPackageSpec* specs, int spec_count,',
        '                                                 const char** registry_names,',
        '                                                 const char*** registry_versions,',
        '                                                 const char**** registry_deps,',
        '                                                 int registry_count,',
        '                                                 OmniLockfile* lockfile) {',
        '  OmniResolution result = {0};',
        '  // This is a simplified stub - full implementation would require',
        '  // a proper registry data structure and topological sort',
        '  result.packages = NULL;',
        '  result.count = 0;',
        '  omni_lockfile_init(&result.lockfile);',
        '  result.warnings = NULL;',
        '  result.warning_count = 0;',
        '  return result;',
        '}',
        '',
        '// OMNISYS.pkg function stubs for C target',
        'OmniVersion omnisys_pkg_parse_version(const char* version) {',
        '  OmniVersion v = {0};',
        '  omni_pkg_parse_version(version, &v);',
        '  return v;',
        '}',
        '',
        'bool omnisys_pkg_satisfies(const char* version, const char* constraint) {',
        '  return omni_pkg_satisfies(version, constraint);',
        '}',
        '',
        'void omnisys_pkg_compute_checksum(const char* content, char* out, size_t out_size) {',
        '  omni_pkg_compute_checksum(content, out, out_size);',
        '}',
        '',
        'OmniLockfile* omnisys_pkg_lockfile_new(void) {',
        '  OmniLockfile* lf = malloc(sizeof(OmniLockfile));',
        '  omni_lockfile_init(lf);',
        '  return lf;',
        '}',
        '',
        'void omnisys_pkg_lockfile_free(OmniLockfile* lf) {',
        '  omni_lockfile_free(lf);',
        '  free(lf);',
        '}',
        '',
        'const char* omnisys_pkg_lockfile_to_json(OmniLockfile* lf) {',
        '  // Simplified JSON serialization',
        '  static char buf[8192];',
        '  size_t off = 0;',
        '  off += snprintf(buf + off, sizeof(buf) - off, "{\\"version\\":1,\\"packages\\":[");',
        '  for (int i = 0; i < lf->count; i++) {',
        '    if (i > 0) off += snprintf(buf + off, sizeof(buf) - off, ",");',
        '    off += snprintf(buf + off, sizeof(buf) - off,',
        '      "{\\"name\\":\\"%s\\",\\"version\\":\\"%s\\",\\"checksum\\":\\"%s\\"}',
        '      lf->entries[i].name, lf->entries[i].version, lf->entries[i].checksum);',
        '  }',
        '  off += snprintf(buf + off, sizeof(buf) - off, "]}");',
        '  return buf;',
        '}',
        '',
        'OmniLockfile* omnisys_pkg_lockfile_from_json(const char* json) {',
        '  // Simplified - returns empty lockfile',
        '  return omnisys_pkg_lockfile_new();',
        '}',
        '',
        'OmniResolution omnisys_pkg_resolve_versions(OmniPackageSpec* specs, int spec_count,',
        '                                             const char** registry_names,',
        '                                             const char*** registry_versions,',
        '                                             const char**** registry_deps,',
        '                                             int registry_count,',
        '                                             OmniLockfile* lockfile) {',
        '  return omni_pkg_resolve_versions(specs, spec_count, registry_names,',
        '                                    registry_versions, registry_deps,',
        '                                    registry_count, lockfile);',
        '}',
        '',
    ]

    # SQLite support
    lines.extend(
        [
            '#ifdef OMNI_HAVE_SQLITE',
            '// SQLite connection (single global connection)',
            'static sqlite3* _omni_sqlite_db = NULL;',
            '',
            '// db_open(path) - open or create SQLite database',
            '// path: NULL or ":memory:" for in-memory, otherwise file path',
            'void omnisys_db_open(const char* path) {',
            '  if (_omni_sqlite_db) {',
            '    sqlite3_close(_omni_sqlite_db);',
            '    _omni_sqlite_db = NULL;',
            '  }',
            '  const char* db_path = (path && path[0]) ? path : ":memory:";',
            '  int rc = sqlite3_open(db_path, &_omni_sqlite_db);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_open failed: %s\\n", sqlite3_errmsg(_omni_sqlite_db));',
            '    return;',
            '  }',
            '  sqlite3_exec(_omni_sqlite_db, "PRAGMA foreign_keys = ON", NULL, NULL, NULL);',
            '}',
            '',
            '// db_exec(sql, params_json) - execute DDL/DML',
            '// params_json: JSON array of parameters (simplified - uses first param only for demo)',  # noqa: E501
            'int omnisys_db_exec(const char* sql, const char* params_json) {',
            '  (void)params_json; // TODO: parse JSON params',
            '  if (!_omni_sqlite_db) return -1;',
            '  char* errmsg = NULL;',
            '  int rc = sqlite3_exec(_omni_sqlite_db, sql, NULL, NULL, &errmsg);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_exec failed: %s\\n", errmsg);',
            '    sqlite3_free(errmsg);',
            '    return -1;',
            '  }',
            '  return sqlite3_changes(_omni_sqlite_db);',
            '}',
            '',
            '// db_query(sql, params_json) - execute SELECT and return JSON',
            '// Returns a JSON string array of row objects',
            'const char* omnisys_db_query(const char* sql, const char* params_json) {',
            '  (void)params_json; // TODO: parse JSON params',
            '  if (!_omni_sqlite_db) return "[]";',
            '  sqlite3_stmt* stmt = NULL;',
            '  int rc = sqlite3_prepare_v2(_omni_sqlite_db, sql, -1, &stmt, NULL);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_prepare failed: %s\\n", sqlite3_errmsg(_omni_sqlite_db));',  # noqa: E501
            '    return "[]";',
            '  }',
            '  // Simplified: build JSON result in static buffer',
            '  static char result_buf[8192];',
            '  size_t off = 0;',
            "  result_buf[off++] = '[';",
            '  int first_row = 1;',
            '  while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {',
            '    if (!first_row) {',
            "      if (off + 1 < sizeof(result_buf)) result_buf[off++] = ',';",
            '    }',
            '    first_row = 0;',
            "    if (off + 1 < sizeof(result_buf)) result_buf[off++] = '{';",
            '    int col_count = sqlite3_column_count(stmt);',
            '    for (int i = 0; i < col_count; i++) {',
            '      const char* col_name = sqlite3_column_name(stmt, i);',
            '      const char* col_value = (const char*)sqlite3_column_text(stmt, i);',
            "      if (i > 0 && off + 1 < sizeof(result_buf)) result_buf[off++] = ',';",
            '      // Write key',
            '      size_t kn = strlen(col_name);',
            '      if (off + kn + 3 < sizeof(result_buf)) {',
            "        result_buf[off++] = '\"';",
            '        memcpy(result_buf + off, col_name, kn);',
            '        off += kn;',
            "        result_buf[off++] = '\"';",
            "        result_buf[off++] = ':';",
            '      }',
            '      // Write value',
            '      if (col_value) {',
            '        size_t vn = strlen(col_value);',
            '        if (off + vn + 3 < sizeof(result_buf)) {',
            "          result_buf[off++] = '\"';",
            '          memcpy(result_buf + off, col_value, vn);',
            '          off += vn;',
            "          result_buf[off++] = '\"';",
            '        }',
            '      } else {',
            '        if (off + 4 < sizeof(result_buf)) {',
            '          memcpy(result_buf + off, "null", 4);',
            '          off += 4;',
            '        }',
            '      }',
            '    }',
            "    if (off + 1 < sizeof(result_buf)) result_buf[off++] = '}';",
            '  }',
            "  if (off + 1 < sizeof(result_buf)) result_buf[off++] = ']';",
            "  result_buf[off] = '\\0';",
            '  sqlite3_finalize(stmt);',
            '  return result_buf;',
            '}',
            '',
            '// db_close() - close SQLite database',
            'void omnisys_db_close(void) {',
            '  if (_omni_sqlite_db) {',
            '    sqlite3_close(_omni_sqlite_db);',
            '    _omni_sqlite_db = NULL;',
            '  }',
            '}',
            '#endif // OMNI_HAVE_SQLITE',
            '',
        ]
    )

    custom_types = getattr(mir, 'types', {})
    lines.extend(_emit_c_type_decls(custom_types))

    for fn in mir.functions.values():
        params = ', '.join(f'{_c_type(p.type)} {p.name}' for p in fn.params) or 'void'
        ret = _c_type(fn.return_type)
        lines.append(f'{ret} {fn.name}({params});')
    if mir.functions:
        lines.append('')

    for fn in mir.functions.values():
        params = ', '.join(f'{_c_type(p.type)} {p.name}' for p in fn.params) or 'void'
        ret = _c_type(fn.return_type)
        lines.append(f'{ret} {fn.name}({params}) {{')
        declared = {p.name for p in fn.params}
        types: dict[str, str] = {p.name: p.type for p in fn.params}
        for stmt in fn.body:
            lines.append(_c_stmt(stmt, declared, custom_types, 2, types))
        lines.append('}')
        lines.append('')

    lines.append('int main(int argc, char** argv) {')
    lines.append('  (void)argc; (void)argv;')
    lines.append('  ecs_world_t* world = ecs_init();')
    lines.append('  (void)world;')
    lines.append('')

    main_types: dict[str, str] = {}
    constructs: dict[str, dict[str, Any]] = {}
    for stmt in mir.entry_point:
        if stmt.get('op') == 'assign' and stmt['expr'].get('op') == 'struct':
            constructs[stmt['name']] = stmt['expr']

    sim_system_lines, run_ticks = _emit_sim_lowering(mir, custom_types, constructs, main_types)
    lines.extend(sim_system_lines)

    lines.append('')
    if run_ticks is not None:
        lines.append(f'  for (int _omni_tick = 0; _omni_tick < {run_ticks}; _omni_tick++) {{')
        lines.append('    ecs_progress(world, 0);')
        lines.append('  }')
    else:
        lines.append('  ecs_progress(world, 0);')
    lines.append('  ecs_fini(world);')
    lines.append('  return 0;')
    lines.append('}')

    return '\n'.join(lines)

```

## File: `omni_compiler\checker.py`
```python
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

```

## File: `omni_compiler\cli.py`
```python
"""CLI Tool for OmniScript Compiler.

Commands: check, run, inspect, explain, build, verify, suggest, generate, trace, lsp.
"""

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.emitter import emit_js
from omni_compiler.formatter import FormatConfig, format_file
from omni_compiler.lexer import is_agent_mode, tokenize
from omni_compiler.mir import MIRModule, to_mir
from omni_compiler.parser import parse
from omni_compiler.wasm_emitter import emit_wasm, wasm_build_command


def _compile(file: Path, lang: str | None = None) -> tuple[Any, Any, MIRModule]:
    code = Path(file).read_text(encoding='utf-8')

    # Auto-detect agent mode if not specified
    if lang is None:
        lang = 'agent' if is_agent_mode(code) else 'en'

    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return ast, symbol_table, mir


def _mir_uses_omnisys(mir: MIRModule) -> bool:
    """Return True when the program actually invokes an ``omnisys.*`` function.

    Walks every MIR statement (entry point and function bodies) for a call node
    whose name begins with ``omnisys`` (the MIR normalizes ``OMNISYS.*`` to
    lowercase in :func:`omni_compiler.mir._normalize_call_name`).
    """

    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            if node.get('op') == 'call' and str(node.get('name', '')).startswith('omnisys'):
                return True
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return any(walk(v) for v in node)
        return False

    if walk(mir.entry_point):
        return True
    return any(walk(fn.body) for fn in mir.functions.values())


def _reject_omnisys_on_native_target(target: str, mir: MIRModule) -> None:
    """§8.3 per-capability gate: native lanes lack the OMNISYS runtime.

    The gate is capability-based, not import-based. ``import OMNISYS`` alone
    consumes no capability, so an import-only program may build on native
    targets (the documented §8.3 carve-out). Only a program that actually calls
    an ``omnisys.*`` function requires the JS lane — the reference OMNISYS
    back-end (spec §17.10.E/§17.10.R) — and is rejected with E-BACKEND-001.
    """
    if not _mir_uses_omnisys(mir):
        return
    click.echo(
        json.dumps(
            _diagnostic_from_exception(
                DiagnosticError(
                    'E-BACKEND-001',
                    'backend',
                    'error',
                    'OMNISYS functions require the JS lane.',
                    f"'{target}' does not provide the OMNISYS runtime. "
                    'The JS lane is the reference OMNISYS back-end (spec §17.10.E/§17.10.R). '
                    'Per spec §8.3 this gate is per-capability: an import-only program '
                    '(no `omnisys.*` call) builds on native targets.',
                    1,
                    1,
                    0,
                    0,
                    {'target': target, 'imports': mir.imports},
                    [
                        {
                            'id': 'target-js',
                            'kind': 'replace_span',
                            'applicability': 'automatic',
                            'description': 'Build with --target js, the OMNISYS reference '
                            'back-end.',
                            'edit': {
                                'operation': 'replace',
                                'span': {'start': 0, 'end': 0},
                                'text': '--target js',
                            },
                        }
                    ],
                )
            ),
            indent=2,
        )
    )
    sys.exit(1)


def _diagnostic_from_exception(e: Exception) -> dict[str, Any]:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-SYNTAX-001',
            'category': 'syntax',
            'severity': 'error',
            'message': 'Syntax error.',
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'fix-syntax',
                    'kind': 'replace_span',
                    'applicability': 'suggested',
                    'description': 'Fix the reported syntax issue.',
                    'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    if isinstance(e, NameError):
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-NAME-001',
            'category': 'name',
            'severity': 'error',
            'message': str(e),
            'details': str(e),
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'define-name',
                    'kind': 'suggested',
                    'applicability': 'suggested',
                    'description': 'Define the missing name or check the spelling.',
                    'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    return {
        'schema': 'omni.diagnostic',
        'version': '1.0',
        'code': 'E-INTERNAL-001',
        'category': 'internal',
        'severity': 'error',
        'message': str(e),
        'details': f'{type(e).__name__}: {e}',
        'span': {'start': 0, 'end': 0},
        'location': {'line': 1, 'column': 1},
        'context': {},
        'fixes': [],
    }


@click.group()
@click.version_option(version='0.1.0', prog_name='omni')
def cli() -> None:
    """OmniScript Compiler - AI-first language with declared effects and live links."""
    pass


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def check(file: Path, lang: str | None) -> None:
    """Type-check and effect-check an OmniScript file."""
    try:
        _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(f'omni check: OK — {file.name}')
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def run(file: Path, lang: str | None) -> None:
    """Compile and execute an OmniScript file (Node.js required)."""
    import subprocess  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    try:
        _, _, mir = _compile(file, lang)
        html = emit_js(mir)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        html_path = f.name

    try:
        runner = Path(__file__).resolve().parents[1] / 'scripts' / 'run-omnisys.js'
        result = subprocess.run(
            ['node', str(runner), html_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        click.echo(
            json.dumps(
                {
                    'schema': 'omni.diagnostic',
                    'version': '1.0',
                    'code': 'E-RUNTIME-001',
                    'category': 'runtime',
                    'severity': 'error',
                    'message': 'Node.js not found.',
                    'details': '`omni run` requires Node.js on PATH to execute the emitted '
                    'program.',
                    'span': {'start': 0, 'end': 0},
                    'location': {'line': 1, 'column': 1},
                    'context': {},
                    'fixes': [],
                },
                indent=2,
            )
        )
        sys.exit(1)
    finally:
        with contextlib.suppress(OSError):
            Path(html_path).unlink()
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, err=True, nl=False)
    sys.exit(result.returncode)


@cli.command()
@click.argument('symbol')
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def inspect(symbol: str, file: Path, lang: str | None) -> None:
    """Inspect a symbol in an OmniScript file."""
    try:
        _, symbol_table, _ = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    rec = symbol_table.inspect_symbol(symbol)
    if rec is None:
        click.echo(
            json.dumps(
                {
                    'schema': 'omni.symbol',
                    'version': '1.0',
                    'name': symbol,
                    'kind': 'unknown',
                    'type': 'unknown',
                    'declared_effects': {'uses': [], 'reads': [], 'writes': []},
                    'span': {'start': 0, 'end': 0},
                    'location': {'line': 1, 'column': 1},
                    'dependencies': [],
                    'exported': False,
                },
                indent=2,
            )
        )
        sys.exit(1)
    click.echo(json.dumps(rec, indent=2))
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def explain(file: Path, lang: str | None) -> None:
    """Explain an error in an OmniScript file."""
    try:
        _compile(file, lang)
    except Exception as e:
        d = _diagnostic_from_exception(e)
        d['hint'] = d.get('message', '')
        click.echo(json.dumps(d, indent=2))
        sys.exit(1)
    click.echo('omni explain: no errors found')
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--target',
    default='js',
    show_default=True,
    type=click.Choice(['js', 'c', 'rust', 'wasm-browser', 'wasm-wasi']),
)
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    help='Output path (defaults to the input stem + target suffix).',
)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def build(file: Path, target: str, output: Path | None, lang: str | None) -> None:
    """Build an OmniScript file to a target artifact."""
    try:
        _, _, mir = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)

    mode = None
    if target == 'js':
        content = emit_js(mir)
        out = output or file.with_suffix('.html')
    elif target == 'c':
        _reject_omnisys_on_native_target(target, mir)
        content = emit_c(mir)
        out = output or file.with_suffix('.c')
    elif target == 'rust':
        _reject_omnisys_on_native_target(target, mir)
        try:
            from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415 - optional peer module

            content = emit_rust(mir)
        except ImportError:
            click.echo(
                'omni build: rust target unavailable (rust_emitter.py has not landed yet)',
                err=True,
            )
            sys.exit(1)
        out = output or file.with_suffix('.rs')
    elif target in ('wasm-browser', 'wasm-wasi'):
        _reject_omnisys_on_native_target(target, mir)
        mode = 'browser' if target == 'wasm-browser' else 'wasi'
        content = emit_wasm(mir, mode=mode)
        default_out = file.with_suffix('.html' if mode == 'browser' else '.c')
        out = output or default_out
    else:  # pragma: no cover - click restricts valid targets
        click.echo(f'omni build: unknown target: {target}', err=True)
        sys.exit(1)

    out.write_text(content, encoding='utf-8')
    click.echo(f'omni build: wrote {out} (target={target})')
    if mode is not None:
        click.echo(f'  {wasm_build_command(mode)}', err=True)
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def verify(file: Path, lang: str | None) -> None:
    """Prove require/ensure contracts statically with an SMT solver."""
    try:
        from omni_compiler.smt import verify_contracts  # noqa: PLC0415

        ast, _, _ = _compile(file, lang)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    results = verify_contracts(ast)
    batch = {'schema': 'omni.verify.batch', 'version': '1.0', 'results': results}
    click.echo(json.dumps(batch, indent=2))
    failed = [r for r in results if r['status'] == 'failed']
    sys.exit(1 if failed else 0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def suggest(file: Path, lang: str | None) -> None:  # noqa: ARG001
    """Propose ranked fixes for errors in an OmniScript file."""
    try:
        from omni_compiler.ai_tools import suggest_fix  # noqa: PLC0415

        code = Path(file).read_text(encoding='utf-8')
        ast = parse(tokenize(code))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    fixes = suggest_fix(ast, None)
    if not fixes:
        click.echo('omni suggest: no errors found')
        sys.exit(0)
    click.echo(json.dumps({'schema': 'omni.suggest', 'version': '1.0', 'fixes': fixes}, indent=2))
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.argument('function')
@click.option(
    '--output',
    '-o',
    type=click.Path(path_type=Path),
    help='Write the generated test to this path instead of stdout.',
)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def generate(file: Path, function: str, output: Path | None, lang: str | None) -> None:
    """Draft a pytest test file for a function."""
    try:
        from omni_compiler.ai_tools import generate_test  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file, lang)
        test_source = generate_test(ast, symbol_table, function, source_file=str(file))
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    if output:
        output.write_text(test_source, encoding='utf-8')
        click.echo(f'omni generate: wrote {output}')
    else:
        click.echo(test_source)
    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.argument('function', required=False)
@click.option(
    '--lang',
    type=click.Choice(['en', 'agent']),
    default=None,
    help='Language mode (default: auto-detect).',
)
def trace(file: Path, function: str | None, lang: str | None) -> None:
    """Step through a function (or the entry block) and print trace events."""
    try:
        from omni_compiler.ai_tools import trace_execution, trace_to_json  # noqa: PLC0415

        ast, symbol_table, _ = _compile(file, lang)
        events = trace_execution(ast, symbol_table, function)
    except Exception as e:
        click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
        sys.exit(1)
    click.echo(trace_to_json(events))
    sys.exit(0)


@cli.command()
def lsp() -> None:
    """Run the OmniScript Language Server (stdio JSON-RPC)."""
    try:
        from omni_compiler.lsp import OmniLspServer  # noqa: PLC0415

        OmniLspServer().run()
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(0)


@cli.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--check', is_flag=True, help='Exit with code 1 if any file would be changed.')
@click.option('--write', is_flag=True, help='Write changes to files (default).')
@click.option('--diff', is_flag=True, help='Show diff instead of writing.')
@click.option('--indent', default=4, show_default=True, type=int, help='Indent size in spaces.')
@click.option('--tabs', is_flag=True, help='Use tabs for indentation.')
def fmt(  # noqa: PLR0913, PLR0917
    paths: tuple[Path, ...], check: bool, _write: bool, diff: bool, indent: int, tabs: bool
) -> None:
    """Format OmniScript (.omni) files to canonical layout."""
    if not paths:
        click.echo('omni fmt: no files specified', err=True)
        sys.exit(1)

    config = FormatConfig(indent_size=indent, use_tabs=tabs)
    any_changed = False
    any_error = False

    for path in paths:
        try:
            changed, formatted = format_file(str(path), config, check=check or diff, diff=diff)
        except Exception as e:
            click.echo(json.dumps(_diagnostic_from_exception(e), indent=2))
            any_error = True
            continue

        if changed:
            any_changed = True
            if diff:
                import difflib  # noqa: PLC0415

                original = Path(path).read_text(encoding='utf-8')
                diff_lines = list(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        formatted.splitlines(keepends=True),
                        fromfile=f'a/{path.name}',
                        tofile=f'b/{path.name}',
                    )
                )
                click.echo(''.join(diff_lines), nl=False)
            elif not check:
                click.echo(f'omni fmt: formatted {path}')
        elif not check and not diff:
            click.echo(f'omni fmt: unchanged {path}')

    if any_error:
        sys.exit(1)
    if check and any_changed:
        click.echo('omni fmt: some files would be reformatted', err=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    cli()

```

## File: `omni_compiler\emitter.py`
```python
"""JS Emitter Module.

Generates a self-contained ES6 HTML document from OMNI MIR with
live-link batching at the end of each top-level block.
"""

from pathlib import Path
from typing import Any

from omni_compiler.omnisys_registry import js_files_for


def _fp_is_nan(x: float) -> bool:
    """Check if value is NaN (JS: Number.isNaN)."""
    return x != x  # noqa: PLR0124


def _fp_is_finite(x: float) -> bool:
    """Check if value is finite (JS: Number.isFinite)."""
    return x != float('inf') and x != float('-inf') and x == x  # noqa: PLR0124


def _fp_is_infinite(x: float) -> bool:
    """Check if value is infinite (JS: !Number.isFinite && !Number.isNaN)."""
    return x == float('inf') or x == float('-inf')


def _fp_divide(a: float, b: float) -> float:
    """IEEE 754 division with proper edge cases."""
    if b == 0.0:
        if a == 0.0:
            return float('nan')
        return float('inf') if a > 0 else float('-inf')
    return a / b


def _fp_modulo(a: float, b: float) -> float:
    """IEEE 754 remainder with proper edge cases."""
    if b == 0.0 or a != a or b != b:  # noqa: PLR0124, PLR1714
        return float('nan')
    if a == float('inf') or a == float('-inf'):
        return float('nan')
    return a % b


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _assigned_names(stmts: list[dict[str, Any]]) -> set[str]:
    """Recursively collect all `assign` targets in a statement list.

    Includes names first assigned inside nested if/for blocks.
    """
    names: set[str] = set()
    for stmt in stmts:
        op = stmt.get('op')
        if op == 'assign':
            names.add(stmt['name'])
        elif op == 'if':
            names |= _assigned_names(stmt.get('body', []))
            names |= _assigned_names(stmt.get('else', []))
        elif op == 'for' or op == 'while':  # noqa: PLR1714
            names |= _assigned_names(stmt.get('body', []))
        elif op == 'try':
            names |= _assigned_names(stmt.get('body', []))
            names |= _assigned_names(stmt.get('on_error', []))
            names |= _assigned_names(stmt.get('finally', []))
        elif op == 'global':
            names.add(stmt['name'])
    return names


def _fp_runtime_helpers() -> list[str]:
    """Emit IEEE 754 floating-point conformance helpers for JS."""
    return [
        '// IEEE 754 Floating-Point Conformance Helpers',
        'const OmniFP = {',
        '  isNaN: (x) => x !== x,',
        '  isFinite: (x) => x !== Infinity && x !== -Infinity && x === x,',
        '  isInfinite: (x) => x === Infinity || x === -Infinity,',
        '  divide: (a, b) => {',
        '    // Use native division which preserves sign of zero',
        '    return a / b;',
        '  },',
        '  modulo: (a, b) => {',
        '    if (b === 0 || a !== a || b !== b) return NaN;',
        '    if (a === Infinity || a === -Infinity) return NaN;',
        '    return a % b;',
        '  },',
        '  negZero: () => -0,',
        '  copySign: (x, y) => Math.abs(x) * (y < 0 || Object.is(y, -0) ? -1 : 1),',
        '};',
        '',
    ]


def _omnisys_runtime(mir: Any) -> list[str]:
    """Inline the JS sources of the imported OMNISYS modules (deps first)."""
    files = js_files_for(mir.imports) if mir.imports else []
    lines: list[str] = []
    if files:
        lines.append('// OMNISYS runtime (inlined, dependency-ordered)')
        lines.append('// import OMNISYS[.<module>] -> portable standard library')
    lines.extend(_fp_runtime_helpers())
    for rel in files:
        source = (_REPO_ROOT / rel).read_text(encoding='utf-8')
        lines.append(source.rstrip())
        lines.append('')
    return lines


def _js_text(raw: str) -> str:
    r"""Render an OmniScript text literal (with {expr} slots) as JS expression.

    ``\{`` and ``\}`` are literal braces; ``{expr}`` interpolates an expression.
    """
    if len(raw) >= 2 and raw[0] in ('"', "'"):  # noqa: PLR2004, SIM108
        body = raw[1:-1]
    else:
        body = raw
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i + 1] in '{}.':  # noqa: PLR2004
            buf.append(body[i + 1])
            i += 2
        elif body[i] == '{':
            j = body.find('}', i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1 : j]
            if buf:
                parts.append('"' + ''.join(buf) + '"')
                buf = []
            parts.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        parts.append('"' + ''.join(buf) + '"')
    if not parts:
        return '""'
    return ' + '.join(parts)


def _js_expr(e: dict[str, Any], params: set[str]) -> str:  # noqa: PLR0911, PLR0912, PLR0915
    op = e.get('op')
    if op == 'number':
        return str(e['value'])
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return 'null'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        return _js_text(e['value'])
    if op == 'call':
        if e['name'] == 'join' and len(e['args']) == 2:  # noqa: PLR2004
            return f'({_js_expr(e["args"][0], params)}).join({_js_expr(e["args"][1], params)})'
        if e['name'] == 'range' and len(e['args']) == 1:
            return f'Array.from({{length: {_js_expr(e["args"][0], params)}}}, (_, i) => i)'
        return f'{e["name"]}({", ".join(_js_expr(a, params) for a in e["args"])})'
    if op == 'list':
        return '[' + ', '.join(_js_expr(i, params) for i in e['items']) + ']'
    if op == 'map':
        pairs = []
        for k, v in e['items'].items():
            quoted = _js_text('"' + k + '"')
            pairs.append(f'{quoted}: {_js_expr(v, params)}')
        return '{' + ', '.join(pairs) + '}'
    if op == 'index':
        return f'{_js_expr(e["object"], params)}[{_js_expr(e["index"], params)}]'
    if op == 'await':
        return f'await {_js_expr(e["expr"], params)}'
    if op == 'field':
        return f'{_js_expr(e["object"], params)}.{e["field"]}'
    if op == 'struct':
        parts = [f'{name}: {_js_expr(value, params)}' for name, value in e['args'].items()]
        return '{' + ', '.join(parts) + '}'
    if op == 'fn_literal':
        fn_params = ', '.join(p['name'] for p in e['params'])
        body_lines = []
        for stmt in e['body']:
            body_lines.append(
                '  ' + _js_stmt(stmt, set(fn_params.split(', ')) if fn_params else set())
            )
        body = '\n'.join(body_lines) if body_lines else ''
        return f'function({fn_params}) {{\n{body}\n}}'
    if op == 'group':
        return f'({_js_expr(e["expr"], params)})'
    if op == 'not':
        return f'!({_js_expr(e["operand"], params)})'
    if op == 'neg':
        operand = e['operand']
        if operand.get('op') == 'number' and operand.get('value') == 0:
            return '-0'
        return f'-({_js_expr(operand, params)})'
    if op == 'is':
        jop: str = '==='
    elif op == 'is not':
        jop = '!=='
    elif op == 'and':
        jop = '&&'
    elif op == 'or':
        jop = '||'
    elif op == '|>':
        # Pipe: x |> f  becomes  f(x)
        left_expr = _js_expr(e['left'], params)
        right_expr = _js_expr(e['right'], params)
        return f'{right_expr}({left_expr})'
    elif op == 'greater than':
        jop = '>'
    elif op == 'less than':
        jop = '<'
    elif op == 'greater or equal':
        jop = '>='
    elif op == 'less or equal':
        jop = '<='
    elif op == '/':
        return f'OmniFP.divide({_js_expr(e["left"], params)}, {_js_expr(e["right"], params)})'
    elif op == '%':
        return f'OmniFP.modulo({_js_expr(e["left"], params)}, {_js_expr(e["right"], params)})'
    else:
        jop = str(op)
    return f'{_js_expr(e["left"], params)} {jop} {_js_expr(e["right"], params)}'


def _js_stmt(s: dict[str, Any], params: set[str]) -> str:  # noqa: PLR0911, PLR0912
    op = s.get('op')
    if op == 'assign':
        return f'{s["name"]} = {_js_expr(s["expr"], params)};'
    if op == 'return':
        return f'return {_js_expr(s["expr"], params)};'
    if op == 'show':
        return f'console.log({_js_expr(s["expr"], params)});'
    if op == 'call':
        return f'{_js_expr(s, params)};'
    if op == 'break':
        return 'break;'
    if op == 'continue':
        return 'continue;'
    if op == 'if':
        lines = [f'if ({_js_expr(s["cond"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        if s.get('else'):
            lines.append('else {')
            for st in s['else']:
                lines.append('  ' + _js_stmt(st, params))
            lines.append('}')
        return '\n'.join(lines)
    if op == 'for':
        lines = [f'for (const {s["var"]} of {_js_expr(s["iterable"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'while ({_js_expr(s["cond"], params)}) {{']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('}')
        return '\n'.join(lines)
    if op == 'try':
        lines = ['try {']
        for st in s['body']:
            lines.append('  ' + _js_stmt(st, params))
        lines.append('} catch (_e) {')
        if s.get('error_var'):
            lines.append(f'  const {s["error_var"]} = String(_e && _e.message ? _e.message : _e);')
        for st in s.get('on_error', []):
            lines.append('  ' + _js_stmt(st, params))
        if s.get('finally'):
            lines.append('} finally {')
            for st in s['finally']:
                lines.append('  ' + _js_stmt(st, params))
            lines.append('}')
        else:
            lines.append('}')
        return '\n'.join(lines)
    if op == 'global':
        return f'// global {s["name"]}'
    return f'// unknown statement: {s!r}'


def _is_style_open(html: str, i: int) -> bool:
    """Return True when the ``<style`` open tag begins at ``i`` in ``html``."""
    return html[i : i + 6].lower() == '<style' and (i + 6 >= len(html) or html[i + 6] in '> \t\r\n')


def _is_style_close(html: str, i: int) -> bool:
    """Return True when the ``</style`` close tag begins at ``i`` in ``html``."""
    return html[i : i + 7].lower() == '</style' and (
        i + 7 >= len(html) or html[i + 7] in '> \t\r\n'
    )


def _js_template(html: str) -> str:  # noqa: PLR0912, PLR0915
    """Convert {slot} HTML placeholders to JS template-literal ${slot}.

    ``{{`` and ``}}`` are literal braces. Inside ``<style>`` blocks every
    brace is literal too, so CSS rules like ``.panel { padding: 8px; }``
    survive untouched instead of being mangled into ``${ ... }`` slots.
    """
    out: list[str] = []
    buf: list[str] = []
    i = 0
    in_style = False
    while i < len(html):
        if html[i] == '<':
            if not in_style and _is_style_open(html, i):
                in_style = True
            elif in_style and _is_style_close(html, i):
                in_style = False
        if in_style:
            if html[i] == '{':
                if i + 1 < len(html) and html[i + 1] == '{':
                    buf.append('{')
                    i += 2
                    continue
                buf.append('{')
                i += 1
                continue
            if html[i] == '}':
                if i + 1 < len(html) and html[i + 1] == '}':
                    buf.append('}')
                    i += 2
                    continue
                buf.append('}')
                i += 1
                continue
            buf.append(html[i])
            i += 1
            continue
        if html[i] == '{':
            if i + 1 < len(html) and html[i + 1] == '{':
                buf.append('{')
                i += 2
                continue
            j = html.find('}', i)
            if j == -1:
                buf.append(html[i:])
                break
            slot = html[i + 1 : j]
            if buf:
                out.append(''.join(buf))
                buf = []
            out.append('${' + slot + '}')
            i = j + 1
        elif html[i] == '}':
            if i + 1 < len(html) and html[i + 1] == '}':
                buf.append('}')
                i += 2
                continue
            buf.append(html[i])
            i += 1
        else:
            buf.append(html[i])
            i += 1
    if buf:
        out.append(''.join(buf))
    return ''.join(out)


def _js_attr_value(v: dict[str, Any], params: set[str]) -> str:
    if v.get('op') == 'slot':
        return _js_expr(v['expr'], params)
    return _js_expr(v, params)


def _js_scene_number(v: dict[str, Any], params: set[str]) -> str:
    """Render a scene attribute value as a JS number (quoted numerics become numbers)."""
    raw = _js_attr_value(v, params)
    if v.get('op') == 'text':
        val = str(v['value'])
        return str(float(val)) if _is_numeric(val) else raw
    return raw


def _js_scene_pos_set(var_name: str, pos: dict[str, Any], params: set[str]) -> list[str]:
    """Emit position.set(...) for a scene object's `pos` attribute.

    Literal text positions ("1,2,3") are split at compile time; slot-valued
    positions ({var}) are split at runtime since the value isn't known yet.
    """
    if pos.get('op') == 'text':
        coords = [c.strip() for c in str(pos['value']).strip('"').split(',')]
        if len(coords) == 3:  # noqa: PLR2004
            return [f'  {var_name}.position.set({coords[0]}, {coords[1]}, {coords[2]});']
        return []
    expr_js = _js_attr_value(pos, params)
    return [
        '  (function() {',
        f"    const _p = String({expr_js}).split(',').map(Number);",
        f'    if (_p.length === 3) {var_name}.position.set(_p[0], _p[1], _p[2]);',
        '  })();',
    ]


def _is_numeric(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    return True


def _js_scene(mir: Any) -> list[str]:  # noqa: PLR0915
    if not mir.scene:
        return []
    lines: list[str] = []
    lines.append('// 3D scene (Three.js)')
    lines.append('let __omniSceneReady = false;')
    lines.append(
        'if (typeof document !== "undefined" && typeof document.createElement === "function") {'
    )  # noqa: E501
    lines.append('  const three = document.createElement("script");')
    lines.append('  three.src = "https://cdn.jsdelivr.net/npm/three@0.152.0/build/three.min.js";')
    lines.append('  three.onload = function() { initScene(); };')
    lines.append('  document.head.appendChild(three);')
    lines.append('  if (typeof THREE !== "undefined") initScene();')
    lines.append('}')
    lines.append('')
    lines.append('function initScene() {')
    lines.append('  if (__omniSceneReady) return;')
    lines.append('  __omniSceneReady = true;')
    lines.append('  const scene = new THREE.Scene();')
    lines.append(
        '  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);'  # noqa: E501
    )  # noqa: E501
    lines.append('  camera.position.z = 5;')
    lines.append('  const renderer = new THREE.WebGLRenderer();')
    lines.append('  renderer.setSize(window.innerWidth, window.innerHeight);')
    lines.append('  document.body.appendChild(renderer.domElement);')
    lines.append('')

    material_idx = 0
    for obj in mir.scene:
        shape = obj['shape']
        attrs = obj.get('attrs', {})
        color = attrs.get('color', {'op': 'text', 'value': '"#ffffff"'})
        size = attrs.get('size', {'op': 'number', 'value': 1})
        if shape == 'box':
            sz = _js_scene_number(size, set())
            lines.append(f'  const box_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.BoxGeometry({sz}, {sz}, {sz}),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'sphere':
            sz = _js_scene_number(size, set())
            lines.append(f'  const sphere_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.SphereGeometry({sz} / 2, 32, 16),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'cylinder':
            sz = _js_scene_number(size, set())
            lines.append(f'  const cylinder_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.CylinderGeometry({sz} / 2, {sz} / 2, {sz}, 32),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'plane':
            sz = _js_scene_number(size, set())
            lines.append(f'  const plane_{material_idx} = new THREE.Mesh(')
            lines.append(f'    new THREE.PlaneGeometry({sz}, {sz}),')
            lines.append(
                f'    new THREE.MeshStandardMaterial({{ color: {_js_attr_value(color, set())} }})'
            )  # noqa: E501
            lines.append('  );')
        elif shape == 'light':
            light_type = attrs.get('type', {'op': 'text', 'value': '"directional"'})
            light_js_type = {
                'directional': 'DirectionalLight',
                'point': 'PointLight',
                'ambient': 'AmbientLight',
                'spot': 'SpotLight',
            }.get('directional', 'DirectionalLight')
            lt = _js_attr_value(light_type, set()).strip('"')
            light_js_type = {
                'directional': 'DirectionalLight',
                'point': 'PointLight',
                'ambient': 'AmbientLight',
                'spot': 'SpotLight',
            }.get(lt, 'DirectionalLight')
            intensity = attrs.get('intensity', {'op': 'number', 'value': 1})
            lines.append(
                f'  const light_{material_idx} = new THREE.{light_js_type}({_js_attr_value(color, set())}, {_js_scene_number(intensity, set())});'  # noqa: E501
            )  # noqa: E501
        elif shape == 'camera':
            pos = attrs.get('pos', {'op': 'text', 'value': '0,0,5'})
            lines.extend(_js_scene_pos_set('camera', pos, set()))

        var_name = f'{shape}_{material_idx}'
        if shape != 'light' and shape != 'camera':  # noqa: PLR1714
            pos = attrs.get('pos')
            if pos:
                lines.extend(_js_scene_pos_set(var_name, pos, set()))
            lines.append(f'  scene.add({var_name});')
        elif shape == 'light':
            lines.append(f'  scene.add(light_{material_idx});')
        material_idx += 1  # noqa: SIM113

    lines.append('')
    lines.append('  function animate() {')
    lines.append('    requestAnimationFrame(animate);')
    lines.append('    renderer.render(scene, camera);')
    lines.append('  }')
    lines.append('  animate();')
    lines.append('}')
    lines.append('')
    return lines


def emit_js(mir: Any) -> str:  # noqa: PLR0915
    """Emit a self-contained HTML document with embedded ES6 JS from OMNI MIR."""
    js: list[str] = []
    js.append('// Generated by the OmniScript JS Emitter')
    js.extend(_omnisys_runtime(mir))
    if mir.imports:
        js.append('// OMNISYS namespace: omnisys.<module>.<fn>')
        js.append('')

    # Emit custom type declarations as TS-style interface JSDoc.
    for tname, fields in mir.types.items():
        js.append(f'// interface {tname} {{')
        for fname, ftype in fields.items():
            js.append(f'//   {fname}: {ftype};')
        js.append('// }')
    if mir.types:
        js.append('')

    # Module-scope state: names assigned anywhere in the entry point (including
    # nested if/for). These persist across batchUpdate() invocations, so
    # functions and click handlers can read them. Names assigned only inside a
    # function body become function-local declarations (see the function loop).
    module_scope = _assigned_names(mir.entry_point)
    for v in sorted(module_scope):
        js.append(f'let {v};')
    js.append('')

    template = _js_template(mir.ui_template) if mir.ui_template else '<p></p>'
    js.append('function renderUI() {')
    js.append('  const app = document.getElementById("app");')
    js.append('  if (app) app.innerHTML = `' + template + '`;')
    js.append('}')
    js.append('')
    js.append('async function batchUpdate(fn) {')
    js.append('  await fn();')
    js.append('  renderUI();')
    js.append('}')
    js.append('')

    def _extract_cap_names(effects_list: list[Any]) -> list[Any]:
        """Extract capability names from effects list (handles both old string format and new tuple format)."""  # noqa: E501
        return [cap if isinstance(cap, str) else cap[0] for cap in effects_list]

    for fn in mir.functions.values():
        params = ', '.join(p.name for p in fn.params)
        uses = _extract_cap_names(fn.effects.uses)
        async_pref = 'async ' if 'network' in uses else ''
        js.append(f'{async_pref}function {fn.name}({params}) {{')
        if uses:
            js.append(f'  // capability: {", ".join(uses)}')
        fn_params = set(p.name for p in fn.params)
        fn_locals = sorted(_assigned_names(fn.body) - fn_params - module_scope)
        if fn_locals:
            js.append('  let ' + ', '.join(fn_locals) + ';')
        for stmt in fn.body:
            js.append('  ' + _js_stmt(stmt, fn_params))
        js.append('}')
        js.append('')

    if mir.entry_point:
        js.append('batchUpdate(async function() {')
        for stmt in mir.entry_point:
            js.append('  ' + _js_stmt(stmt, set()))
        js.append('});')
        js.append('')

    js.append('function bindClicks() {')
    js.append('  const app = document.getElementById("app");')
    js.append('  if (!app || typeof app.addEventListener !== "function") return;')
    js.append('  app.addEventListener("click", function(e) {')
    js.append('    const el = e.target.closest("[click]");')
    js.append('    if (!el) return;')
    js.append('    const fn = window[el.getAttribute("click")];')
    js.append('    if (typeof fn === "function") batchUpdate(fn);')
    js.append('  });')
    js.append('}')
    js.append('bindClicks();')
    js.append(
        'if (typeof omnisys !== "undefined" && omnisys.ui) '
        'omnisys.ui._setGlobalOnStateChange(batchUpdate);'
    )

    scene_js = _js_scene(mir)
    if scene_js:
        js.append('')
        js.extend(scene_js)

    body = '\n'.join(js)
    return '\n'.join(
        [
            '<!DOCTYPE html>',
            '<html>',
            '<head><meta charset="utf-8"><title>OmniScript App</title></head>',
            '<body>',
            '  <div id="app"></div>',
            '  <script>',
            body,
            '  </script>',
            '</body>',
            '</html>',
        ]
    )


def emit_js_with_runtime(mir: Any) -> str:
    """Emit a complete HTML file with embedded JS runtime (alias of emit_js)."""
    return emit_js(mir)

```

## File: `omni_compiler\formatter.py`
```python
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

```

## File: `omni_compiler\lexer.py`
```python
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

```

## File: `omni_compiler\lsp.py`
```python
"""v4.2: minimal OmniScript Language Server Protocol implementation (stdlib only)."""

import json
import sys
from typing import Any, BinaryIO, cast

from omni_compiler.checker import DiagnosticError, SymbolTable, analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse

SERVER_NAME = 'omni-lsp'
SERVER_VERSION = '0.1.0'


def _diagnostic_from_exception(e: Exception) -> dict[str, Any]:
    if isinstance(e, DiagnosticError):
        return e.to_dict()
    if isinstance(e, SyntaxError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-SYNTAX-001',
            'category': 'syntax',
            'severity': 'error',
            'message': 'Syntax error.',
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'fix-syntax',
                    'kind': 'replace_span',
                    'applicability': 'suggested',
                    'description': 'Fix the reported syntax issue.',
                    'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    if isinstance(e, NameError):
        msg = str(e)
        return {
            'schema': 'omni.diagnostic',
            'version': '1.0',
            'code': 'E-NAME-001',
            'category': 'name',
            'severity': 'error',
            'message': msg,
            'details': msg,
            'span': {'start': 0, 'end': 0},
            'location': {'line': 1, 'column': 1},
            'context': {},
            'fixes': [
                {
                    'id': 'define-name',
                    'kind': 'suggested',
                    'applicability': 'suggested',
                    'description': 'Define the missing name or check the spelling.',
                    'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
                }
            ],
        }
    return {
        'schema': 'omni.diagnostic',
        'version': '1.0',
        'code': 'E-INTERNAL-001',
        'category': 'internal',
        'severity': 'error',
        'message': str(e),
        'details': f'{type(e).__name__}: {e}',
        'span': {'start': 0, 'end': 0},
        'location': {'line': 1, 'column': 1},
        'context': {},
        'fixes': [],
    }


def content_length_header(body_len: int) -> str:
    """Build the LSP Content-Length framing header for a message body."""
    return f'Content-Length: {body_len}\r\n\r\n'


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    """Read a Content-Length framed JSON-RPC message, or None at EOF."""
    headers: dict[bytes, bytes] = {}
    while True:
        raw = stream.readline()
        if not raw:
            return None
        raw = raw.rstrip(b'\r\n')
        if not raw:
            break
        key, _, value = raw.partition(b':')
        headers[key.strip().lower()] = value.strip()
    raw_length = headers.get(b'content-length', b'0')
    body = stream.read(int(raw_length))
    if not body:
        return None
    return cast(dict[str, Any], json.loads(body))


def write_message(stream: BinaryIO, msg: dict[str, Any]) -> None:
    """Write a JSON-RPC message to a stream using Content-Length framing."""
    body = json.dumps(msg).encode('utf-8')
    header = content_length_header(len(body)).encode('ascii')
    stream.write(header + body)
    stream.flush()


def _diagnostic_to_lsp(d: dict[str, Any]) -> dict[str, Any]:
    loc = d.get('location') or {'line': 1, 'column': 1}
    line = max(int(loc.get('line', 1)) - 1, 0)
    column = max(int(loc.get('column', 1)) - 1, 0)
    return {
        'range': {
            'start': {'line': line, 'character': column},
            'end': {'line': line, 'character': column},
        },
        'severity': 1,
        'code': d.get('code', ''),
        'message': d.get('message', ''),
        'source': 'omni',
    }


def _identifier_at(text: str, line: int, character: int) -> str | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    content = lines[line]
    if character < 0 or character > len(content):
        return None
    start = character
    while start > 0 and (content[start - 1].isalnum() or content[start - 1] in '_.'):
        start -= 1
    end = character
    while end < len(content) and (content[end].isalnum() or content[end] in '_.'):
        end += 1
    token = content[start:end]
    if not token or not (token[0].isalpha() or token[0] == '_'):
        return None
    return token


class OmniLspServer:
    """Minimal LSP server exposing OmniScript diagnostics and hover support."""

    def __init__(self) -> None:
        """Create a server with no open documents."""
        self._docs: dict[str, dict[str, Any]] = {}
        self._exiting = False

    def _response(self, msg_id: Any, result: Any) -> dict[str, Any]:
        return {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    def _notification(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {'jsonrpc': '2.0', 'method': method, 'params': params}

    def _analyze_document(self, text: str) -> tuple[list[dict[str, Any]], SymbolTable | None]:
        try:
            ast = parse(tokenize(text))
            table = analyze(ast)
            return [], table
        except Exception as e:
            diagnostic = _diagnostic_from_exception(e)
            return [_diagnostic_to_lsp(diagnostic)], None

    def _hover(self, uri: str, line: int, character: int) -> dict[str, Any]:
        doc = self._docs.get(uri)
        if doc is None:
            return {'kind': 'markdown', 'value': ''}
        ident = _identifier_at(str(doc['text']), line, character)
        table = doc['symbol_table']
        if ident is None or table is None:
            return {'kind': 'markdown', 'value': ''}
        symbol = table.inspect_symbol(ident)
        if symbol is None:
            return {'kind': 'markdown', 'value': ''}
        value = f'**{symbol["name"]}**\n\n- kind: {symbol["kind"]}\n- type: {symbol["type"]}'
        return {'kind': 'markdown', 'value': value}

    def handle_message(self, msg: dict[str, Any]) -> list[dict[str, Any]] | None:
        """Handle one JSON-RPC message; return responses/notifications to send."""
        method = msg.get('method')
        msg_id = msg.get('id')
        result: list[dict[str, Any]] | None
        if method == 'initialize':
            result = [
                self._response(
                    msg_id,
                    {
                        'capabilities': {'textDocumentSync': 1, 'hoverProvider': True},
                        'serverInfo': {'name': SERVER_NAME, 'version': SERVER_VERSION},
                    },
                )
            ]
        elif method == 'initialized':
            result = []
        elif method == 'textDocument/didOpen':
            params = msg.get('params') or {}
            text_document = params.get('textDocument') or {}
            uri = str(text_document.get('uri', ''))
            text = str(text_document.get('text', ''))
            diagnostics, table = self._analyze_document(text)
            self._docs[uri] = {'text': text, 'symbol_table': table}
            result = [
                self._notification(
                    'textDocument/publishDiagnostics',
                    {'uri': uri, 'diagnostics': diagnostics},
                )
            ]
        elif method == 'textDocument/hover':
            params = msg.get('params') or {}
            text_document = params.get('textDocument') or {}
            position = params.get('position') or {}
            uri = str(text_document.get('uri', ''))
            line = int(position.get('line', 0))
            character = int(position.get('character', 0))
            contents = self._hover(uri, line, character)
            result = [self._response(msg_id, {'contents': contents})]
        elif method == 'shutdown':
            result = [self._response(msg_id, None)]
        elif method == 'exit':
            self._exiting = True
            result = None
        elif msg_id is not None:
            result = [self._response(msg_id, None)]
        else:
            result = None
        return result

    def run(self) -> None:
        """Serve requests from stdin until an exit message or EOF."""
        stdin = cast(BinaryIO, sys.stdin.buffer)
        stdout = cast(BinaryIO, sys.stdout.buffer)
        while not self._exiting:
            msg = read_message(stdin)
            if msg is None:
                break
            outputs = self.handle_message(msg)
            if outputs:
                for out in outputs:
                    write_message(stdout, out)


if __name__ == '__main__':
    OmniLspServer().run()

```

## File: `omni_compiler\mir.py`
```python
"""OMNI MIR (Middle Intermediate Representation) Module.

Converts a checked AST into a typed, effect-aware, serializable representation.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from omni_compiler.parser import (
    Assignment,
    AwaitExpr,
    BinaryExpr,
    BreakStmt,
    ContinueStmt,
    FieldAccess,
    ForBlock,
    FunctionCall,
    FunctionLiteral,
    GlobalDecl,
    GroupExpr,
    Identifier,
    IfBlock,
    IndexExpr,
    ListLiteral,
    Literal,
    MapLiteral,
    ReturnStmt,
    SceneBlock,
    ShowStmt,
    Slot,
    StructConstruct,
    TryBlock,
    UnaryExpr,
    WhileBlock,
)


@dataclass
class MIRParameter:
    """A named parameter of a MIR function."""

    name: str
    type: str


@dataclass
class MIREffects:
    """Declared capability effects for a MIR function."""

    uses: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    borrows: list[str] = field(default_factory=list)
    pure: bool = False


@dataclass
class MIRFunction:
    """A lowered function in the MIR module."""

    name: str
    params: list[MIRParameter] = field(default_factory=list)
    return_type: str = 'None'
    effects: MIREffects = field(default_factory=MIREffects)
    body: list[dict[str, Any]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    ensures: list[str] = field(default_factory=list)


@dataclass
class MIRModule:
    """The top-level MIR module emitted for a program."""

    schema: str = 'omni.mir'
    version: str = '1.0'
    functions: dict[str, MIRFunction] = field(default_factory=dict)
    entry_point: list[dict[str, Any]] = field(default_factory=list)
    ui_template: str | None = None
    scene: list[dict[str, Any]] = field(default_factory=list)
    types: dict[str, Any] = field(default_factory=dict)
    imports: list[list[str]] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize this module to a JSON string."""
        return json.dumps(
            {
                'schema': self.schema,
                'version': self.version,
                'imports': self.imports,
                'functions': {
                    name: {
                        'name': fn.name,
                        'params': [{'name': p.name, 'type': p.type} for p in fn.params],
                        'return_type': fn.return_type,
                        'effects': {
                            'uses': fn.effects.uses,
                            'reads': fn.effects.reads,
                            'writes': fn.effects.writes,
                            'borrows': fn.effects.borrows,
                            'pure': fn.effects.pure,
                        },
                        'body': fn.body,
                        'requires': fn.requires,
                        'ensures': fn.ensures,
                    }
                    for name, fn in self.functions.items()
                },
                'entry_point': self.entry_point,
                'ui_template': self.ui_template,
                'scene': self.scene,
                'types': self.types,
            },
            indent=2,
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MIRModule':
        """Deserialize an MIRModule from a JSON string."""
        data = json.loads(json_str)
        module = cls(schema=data['schema'], version=data['version'])
        for name, fn_data in data.get('functions', {}).items():
            params = [
                MIRParameter(name=p['name'], type=p['type']) for p in fn_data.get('params', [])
            ]
            eff = fn_data.get('effects', {})
            effects = MIREffects(
                uses=list(eff.get('uses', [])),
                reads=list(eff.get('reads', [])),
                writes=list(eff.get('writes', [])),
                borrows=list(eff.get('borrows', [])),
                pure=bool(eff.get('pure', False)),
            )
            fn = MIRFunction(
                name=fn_data['name'],
                params=params,
                return_type=fn_data['return_type'],
                effects=effects,
                body=list(fn_data.get('body', [])),
                requires=list(fn_data.get('requires', [])),
                ensures=list(fn_data.get('ensures', [])),
            )
            module.functions[name] = fn
        module.entry_point = list(data.get('entry_point', []))
        module.ui_template = data.get('ui_template')
        module.scene = list(data.get('scene', []))
        module.types = dict(data.get('types', {}))
        module.imports = [list(p) for p in data.get('imports', [])]
        return module


def _normalize_call_name(name: str) -> str:
    """Lower the OMNISYS root namespace to match the JS runtime's registration.

    The parser preserves user-written case; omnisys/*.js only ever registers
    lowercase `omnisys.<module>.<fn>`.
    """
    if name == 'OMNISYS' or name.startswith('OMNISYS.'):
        return 'omnisys' + name[len('OMNISYS') :]
    return name


def _expr_to_mir(e: Any) -> dict[str, Any]:  # noqa: PLR0911, PLR0912
    if isinstance(e, Literal):
        if e.value_type == 'Number':
            return {'op': 'number', 'value': e.value}
        if e.value_type == 'Text':
            return {'op': 'text', 'value': e.value}
        if e.value_type == 'Boolean':
            return {'op': 'boolean', 'value': bool(e.value)}
        if e.value_type == 'None':
            return {'op': 'none'}
    if isinstance(e, Identifier):
        return {'op': 'ident', 'name': e.name}
    if isinstance(e, FieldAccess):
        return {'op': 'field', 'object': _expr_to_mir(e.object), 'field': e.field}
    if isinstance(e, IndexExpr):
        return {'op': 'index', 'object': _expr_to_mir(e.object), 'index': _expr_to_mir(e.index)}
    if isinstance(e, AwaitExpr):
        return {'op': 'await', 'expr': _expr_to_mir(e.expr)}
    if isinstance(e, MapLiteral):
        return {'op': 'map', 'items': {k: _expr_to_mir(v) for k, v in e.items.items()}}
    if isinstance(e, StructConstruct):
        return {
            'op': 'struct',
            'name': e.name,
            'args': {name: _expr_to_mir(value) for name, value in e.args.items()},
        }
    if isinstance(e, ListLiteral):
        return {'op': 'list', 'items': [_expr_to_mir(i) for i in e.items]}
    if isinstance(e, FunctionCall):
        return {
            'op': 'call',
            'name': _normalize_call_name(e.name),
            'args': [_expr_to_mir(a) for a in e.args],
        }
    if isinstance(e, GroupExpr):
        return {'op': 'group', 'expr': _expr_to_mir(e.expr)}
    if isinstance(e, UnaryExpr):
        return {'op': e.op, 'operand': _expr_to_mir(e.operand)}
    if isinstance(e, BinaryExpr):
        return {'op': e.op, 'left': _expr_to_mir(e.left), 'right': _expr_to_mir(e.right)}
    if isinstance(e, FunctionLiteral):
        return {
            'op': 'fn_literal',
            'params': [{'name': p.name, 'type': p.type} for p in e.params],
            'return_type': e.return_type,
            'body': [_stmt_to_mir(s) for s in e.body],
        }
    raise TypeError(f'Unknown expression node: {e!r}')


def _stmt_to_mir(s: Any) -> dict[str, Any]:  # noqa: PLR0911
    if isinstance(s, Assignment):
        return {'op': 'assign', 'name': s.name, 'expr': _expr_to_mir(s.expr)}
    if isinstance(s, ReturnStmt):
        return {'op': 'return', 'expr': _expr_to_mir(s.expr)}
    if isinstance(s, ShowStmt):
        return {'op': 'show', 'expr': _expr_to_mir(s.expr)}
    if isinstance(s, BreakStmt):
        return {'op': 'break'}
    if isinstance(s, ContinueStmt):
        return {'op': 'continue'}
    if isinstance(s, IfBlock):
        return {
            'op': 'if',
            'cond': _expr_to_mir(s.condition),
            'body': [_stmt_to_mir(x) for x in s.body],
            'else': [_stmt_to_mir(x) for x in s.else_body],
        }
    if isinstance(s, ForBlock):
        return {
            'op': 'for',
            'var': s.variable,
            'var_type': s.var_type,
            'iterable': _expr_to_mir(s.iterable),
            'body': [_stmt_to_mir(x) for x in s.body],
        }
    if isinstance(s, WhileBlock):
        return {
            'op': 'while',
            'cond': _expr_to_mir(s.condition),
            'body': [_stmt_to_mir(x) for x in s.body],
        }
    if isinstance(s, TryBlock):
        return {
            'op': 'try',
            'body': [_stmt_to_mir(x) for x in s.body],
            'error_var': s.error_var,
            'on_error': [_stmt_to_mir(x) for x in s.on_error_body],
            'finally': [_stmt_to_mir(x) for x in s.finally_body],
        }
    if isinstance(s, GlobalDecl):
        return {'op': 'global', 'name': s.name}
    if isinstance(s, FunctionCall):
        return _expr_to_mir(s)
    if isinstance(s, AwaitExpr):
        return {'op': 'await', 'expr': _expr_to_mir(s.expr)}
    raise TypeError(f'Unknown statement node: {s!r}')


def _expr_to_string(e: Any) -> str:  # noqa: PLR0911
    if isinstance(e, Literal):
        if e.value_type == 'Text':
            return str(e.value)
        return str(e.value)
    if isinstance(e, Identifier):
        return e.name
    if isinstance(e, GroupExpr):
        return f'({_expr_to_string(e.expr)})'
    if isinstance(e, UnaryExpr):
        prefix = 'not ' if e.op == 'not' else '-'
        return prefix + _expr_to_string(e.operand)
    if isinstance(e, FunctionCall):
        return f'{e.name}({", ".join(_expr_to_string(a) for a in e.args)})'
    if isinstance(e, BinaryExpr):
        return f'{_expr_to_string(e.left)} {e.op} {_expr_to_string(e.right)}'
    return str(e)


def _scene_attr_to_mir(v: Any) -> dict[str, Any]:
    if isinstance(v, Slot):
        return {'op': 'slot', 'expr': _expr_to_mir(v.expr)}
    return _expr_to_mir(v)


def _scene_to_mir(scene: SceneBlock) -> list[dict[str, Any]]:
    objects = []
    for obj in scene.objects:
        objects.append(
            {
                'shape': obj.shape,
                'attrs': {name: _scene_attr_to_mir(value) for name, value in obj.attrs.items()},
            }
        )
    return objects


def to_mir(ast: Any, symbol_table: Any = None) -> MIRModule:
    """Convert a checked AST to OMNI MIR."""
    del symbol_table
    module = MIRModule()

    for fn in ast.functions:
        params = [MIRParameter(name=p.name, type=p.type) for p in fn.params]
        effects = MIREffects(
            uses=list(fn.effects.get('uses', [])),
            reads=list(fn.effects.get('reads', [])),
            writes=list(fn.effects.get('writes', [])),
            borrows=list(fn.effects.get('borrows', [])),
            pure=bool(fn.effects.get('pure', False)),
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

    entry: list[Any] = []
    if ast.app_block:
        entry.extend(_stmt_to_mir(s) for s in ast.app_block.body)
    for s in ast.statements:
        entry.append(_stmt_to_mir(s))
    module.entry_point = entry
    module.ui_template = ast.ui_template
    if ast.scene_block:
        module.scene = _scene_to_mir(ast.scene_block)
    for td in ast.types:
        module.types[str(td.name)] = {'fields': dict(td.fields)}
    module.imports = [list(imp.path) for imp in ast.imports]

    return module

```

## File: `omni_compiler\omnisys_registry.py`
```python
"""OMNISYS module registry (v6).

The single source of truth the compiler uses to resolve `import OMNISYS[.module]`
and to enforce the effect system across the OMNISYS standard library.

Each module records:
  - js_file: the JS implementation file (repo-relative) that is inlined by the
    JS emitter when the module is imported.
  - js_deps: OMNISYS modules that must be inlined first (dependency order).
  - functions: symbol -> {"type": signature, "effects": declared capabilities}.
    `effects["uses"]` is the capability vocabulary the checker enforces
    (network, filesystem, database, camera, microphone, GPU, process, secrets,
    dom, panic). `panic` marks functions that may abort control flow (throw):
    they are NOT pure and must be declared (`uses panic`) at every boundary.

Additional declarative memory effects (Pillar 2, for WASM/embedded targets):
  - allocates: function may allocate memory
  - mutates_heap: function may mutate heap memory

These are purely declarative (not auto-detected) and do not conflict with any
existing OMNISYS capability names.

Design rule (spec §17.3, "Do Not Wrap — Design Native"): the registry describes
portable semantic APIs, never host-library shapes.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OmnisysFunction:
    """A single OMNISYS standard-library function."""

    type: str
    effects: frozenset[str] = frozenset()


@dataclass(frozen=True)
class OmnisysModule:
    """One OMNISYS module (a top-level namespace under `omnisys`)."""

    js_file: str
    functions: dict[str, OmnisysFunction] = field(default_factory=dict)
    js_deps: tuple[str, ...] = ()


def _fn(type_: str, *effects: str) -> OmnisysFunction:
    return OmnisysFunction(type=type_, effects=frozenset(effects))


def _module(
    _name: str,
    js_file: str,
    deps: tuple[str, ...] = (),
    **fns: OmnisysFunction,
) -> OmnisysModule:
    return OmnisysModule(js_file=js_file, functions=dict(fns), js_deps=deps)


def _pure(type_: str) -> OmnisysFunction:
    return _fn(type_)


OMNISYS_MODULES: dict[str, OmnisysModule] = {
    'core': _module(
        'core',
        'omnisys/core.js',
        option=_pure('fn(any) -> Option'),
        some=_pure('fn(any) -> Option'),
        none=_pure('fn() -> Option'),
        is_some=_pure('fn(Option) -> Boolean'),
        is_none=_pure('fn(Option) -> Boolean'),
        ok=_pure('fn(any) -> Result'),
        err=_pure('fn(any) -> Result'),
        is_ok=_pure('fn(Result) -> Boolean'),
        is_err=_pure('fn(Result) -> Boolean'),
        identity=_pure('fn(any) -> any'),
        type_of=_pure('fn(any) -> Text'),
        panic=_fn('fn(Text) -> None', 'panic'),
        abs=_pure('fn(Number) -> Number'),
        min=_pure('fn(Number, Number) -> Number'),
        max=_pure('fn(Number, Number) -> Number'),
        clamp=_pure('fn(Number, Number, Number) -> Number'),
        round=_pure('fn(Number) -> Number'),
        floor=_pure('fn(Number) -> Number'),
        ceil=_pure('fn(Number) -> Number'),
        sqrt=_pure('fn(Number) -> Number'),
        length=_pure('fn(any) -> Number'),
        is_empty=_pure('fn(any) -> Boolean'),
        split=_pure('fn(Text, Text) -> List'),
        char_at=_pure('fn(Text, Number) -> Text'),
        substring=_pure('fn(Text, Number, Number) -> Text'),
        to_number=_pure('fn(Text) -> Number'),
    ),
    'collections': _module(
        'collections',
        'omnisys/collections.js',
        ('core',),
        list_push=_pure('fn(List, any) -> List'),
        list_pop=_pure('fn(List) -> any'),
        list_get=_pure('fn(List, Number) -> any'),
        list_set=_pure('fn(List, Number, any) -> List'),
        list_slice=_pure('fn(List, Number, Number) -> List'),
        list_append=_pure('fn(List, List) -> List'),
        list_contains=_pure('fn(List, any) -> Boolean'),
        list_index_of=_pure('fn(List, any) -> Number'),
        list_remove=_pure('fn(List, Number) -> List'),
        list_sort=_pure('fn(List) -> List'),
        list_reverse=_pure('fn(List) -> List'),
        list_fold=_pure('fn(List, fn, any) -> any'),
        list_map=_pure('fn(List, fn) -> List'),
        list_filter=_pure('fn(List, fn) -> List'),
        list_join=_pure('fn(List, Text) -> Text'),
        list_zip=_pure('fn(List, List) -> List'),
        map_get=_pure('fn(Map, any) -> any'),
        map_set=_pure('fn(Map, any, any) -> Map'),
        map_remove=_pure('fn(Map, any) -> Map'),
        map_has=_pure('fn(Map, any) -> Boolean'),
        map_keys=_pure('fn(Map) -> List'),
        map_values=_pure('fn(Map) -> List'),
        map_size=_pure('fn(Map) -> Number'),
        set_add=_pure('fn(Set, any) -> Set'),
        set_remove=_pure('fn(Set, any) -> Set'),
        set_has=_pure('fn(Set, any) -> Boolean'),
        set_size=_pure('fn(Set) -> Number'),
        set_union=_pure('fn(Set, Set) -> Set'),
        set_intersection=_pure('fn(Set, Set) -> Set'),
        set_difference=_pure('fn(Set, Set) -> Set'),
        deque_push_front=_pure('fn(Deque, any) -> Deque'),
        deque_push_back=_pure('fn(Deque, any) -> Deque'),
        deque_pop_front=_pure('fn(Deque) -> any'),
        deque_pop_back=_pure('fn(Deque) -> any'),
        deque_size=_pure('fn(Deque) -> Number'),
        heap_push=_pure('fn(Heap, any) -> Heap'),
        heap_pop=_pure('fn(Heap) -> any'),
        heap_peek=_pure('fn(Heap) -> any'),
        heap_size=_pure('fn(Heap) -> Number'),
        ring_new=_pure('fn(Number) -> RingBuffer'),
        ring_push=_pure('fn(RingBuffer, any) -> RingBuffer'),
        ring_pop=_pure('fn(RingBuffer) -> any'),
        ring_size=_pure('fn(RingBuffer) -> Number'),
    ),
    'error': _module(
        'error',
        'omnisys/error.js',
        ('core',),
        error=_pure('fn(Text) -> Error'),
        error_code=_pure('fn(Text, Text) -> Error'),
        error_message=_pure('fn(Error) -> Text'),
        error_code_of=_pure('fn(Error) -> Text'),
        error_stack=_pure('fn(Error) -> Text'),
        error_with_context=_pure('fn(Error, Text, any) -> Error'),
        error_has_context=_pure('fn(Error, Text) -> Boolean'),
        error_to_dict=_pure('fn(Error) -> Map'),
        throw_error=_fn('fn(Error) -> None', 'panic'),
        is_error=_pure('fn(any) -> Boolean'),
    ),
    'serde': _module(
        'serde',
        'omnisys/serde.js',
        ('core',),
        json_encode=_pure('fn(any) -> Text'),
        json_decode=_fn('fn(Text) -> any', 'panic'),
        csv_encode=_pure('fn(List) -> Text'),
        csv_decode=_pure('fn(Text) -> List'),
        to_hex=_pure('fn(Text) -> Text'),
        from_hex=_pure('fn(Text) -> Text'),
        base64_encode=_pure('fn(Text) -> Text'),
        base64_decode=_fn('fn(Text) -> Text', 'panic'),
        schema_validate=_pure('fn(any, Map) -> Boolean'),
    ),
    'async': _module(
        'async',
        'omnisys/async.js',
        ('core',),
        task=_pure('fn(fn) -> Task'),
        delay=_pure('fn(Number) -> Task'),
        interval=_pure('fn(Number, fn() -> None) -> Task'),
        timeout=_pure('fn(Number, fn() -> None) -> Task'),
        tick=_pure('fn(fn() -> None) -> Task'),
        cancel=_pure('fn(Task) -> None'),
        **{'await': _pure('fn(Task) -> Any')},
        all=_pure('fn(List) -> Task'),
        race=_pure('fn(List) -> Task'),
        any=_pure('fn(List) -> Task'),
        channel=_pure('fn(Number) -> Channel'),
        channel_send=_pure('fn(Channel, any) -> Task'),
        channel_recv=_pure('fn(Channel) -> Task'),
        is_promise=_pure('fn(any) -> Boolean'),
        with_timeout=_pure('fn(Task, Number) -> Task'),
    ),
    'fs': _module(
        'fs',
        'omnisys/fs.js',
        ('core',),
        read_file=_fn('fn(Text) -> Text', 'filesystem'),
        write_file=_fn('fn(Text, Text) -> Text', 'filesystem'),
        append_file=_fn('fn(Text, Text) -> Text', 'filesystem'),
        delete_file=_fn('fn(Text) -> Boolean', 'filesystem'),
        file_exists=_fn('fn(Text) -> Boolean', 'filesystem'),
        file_size=_fn('fn(Text) -> Number', 'filesystem'),
        list_dir=_fn('fn(Text) -> List', 'filesystem'),
        make_dir=_fn('fn(Text) -> Boolean', 'filesystem'),
        remove_dir=_fn('fn(Text) -> Boolean', 'filesystem'),
        rename_file=_fn('fn(Text, Text) -> Boolean', 'filesystem'),
        copy_file=_fn('fn(Text, Text) -> Boolean', 'filesystem'),
        join_path=_pure('fn(Text, Text) -> Text'),
        basename=_pure('fn(Text) -> Text'),
        dirname=_pure('fn(Text) -> Text'),
    ),
    'test': _module(
        'test',
        'omnisys/test.js',
        ('core', 'collections'),
        assert_true=_pure('fn(Boolean, Text) -> None'),
        assert_eq=_pure('fn(any, any) -> None'),
        assert_throws=_pure('fn(fn) -> Boolean'),
        property=_pure('fn(fn, Number) -> Boolean'),
        bench=_pure('fn(fn, Number) -> Number'),
        fail=_pure('fn(Text) -> None'),
    ),
    'ui': _module(
        'ui',
        'omnisys/ui.js',
        ('core', 'collections'),
        element=_pure('fn(Text, Map, List) -> Element'),
        text=_pure('fn(Text) -> Element'),
        button=_pure('fn(Text, fn) -> Element'),
        row=_pure('fn(List) -> Element'),
        column=_pure('fn(List) -> Element'),
        input=_pure('fn(Text, Text) -> Element'),
        render=_pure('fn(Element) -> Text'),
        to_html=_pure('fn(Element) -> Text'),
        bind=_pure('fn(Element, Text, any) -> Element'),
        state=_pure('fn(any) -> State'),
        state_get=_pure('fn(State) -> any'),
        state_set=_pure('fn(State, any) -> State'),
        state_on_change=_pure('fn(State, fn) -> None'),
        get_value=_fn('fn(Text) -> Text', 'dom'),
        get_form_data=_fn('fn(Text) -> Map', 'dom'),
    ),
    'db': _module(
        'db',
        'omnisys/db.js',
        ('core', 'collections'),
        create_db=_fn('fn(Text) -> Database', 'database'),
        create_table=_fn('fn(Database, Text, Map) -> Table', 'database'),
        insert=_fn('fn(Table, Map) -> Map', 'database'),
        select=_fn('fn(Table, fn) -> List', 'database'),
        update=_fn('fn(Table, fn, Map) -> Number', 'database'),
        delete=_fn('fn(Table, fn) -> Number', 'database'),
        count=_fn('fn(Table, fn) -> Number', 'database'),
        drop_table=_fn('fn(Database, Text) -> Boolean', 'database'),
        schema=_fn('fn(Table) -> Map', 'database'),
        table_size=_fn('fn(Table) -> Number', 'database'),
        db_open=_fn('fn(Text) -> None', 'database', 'filesystem'),
        db_query=_fn('fn(Text, List) -> List', 'database'),
        db_exec=_fn('fn(Text, List) -> Number', 'database'),
        db_close=_fn('fn() -> None', 'database'),
    ),
    'net': _module(
        'net',
        'omnisys/net.js',
        ('core', 'collections'),
        server=_fn('fn(fn) -> Server', 'network'),
        start=_fn('fn(Server) -> Server', 'network'),
        request=_fn('fn(Server, Text, Text, Text) -> Response', 'network'),
        get=_fn('fn(Server, Text) -> Response', 'network'),
        post=_fn('fn(Server, Text, Text) -> Response', 'network'),
        middleware=_fn('fn(fn, List) -> fn', 'network'),
        response=_pure('fn(Number, Text) -> Response'),
        response_json=_pure('fn(Number, any) -> Response'),
        status_of=_pure('fn(Response) -> Number'),
        body_of=_pure('fn(Response) -> Text'),
    ),
    'http': _module(
        'http',
        'omnisys/http.js',
        ('core', 'net', 'async'),
        client=_pure('fn() -> Client'),
        send=_fn('fn(Client, Text, Text, Text, Number) -> Task', 'network'),
        get=_fn('fn(Text, Number) -> Task', 'network'),
        post=_fn('fn(Text, Text, Number) -> Task', 'network'),
        put=_fn('fn(Text, Text, Number) -> Task', 'network'),
        delete=_fn('fn(Text, Number) -> Task', 'network'),
        json_get=_fn('fn(Text, Number) -> Task', 'network'),
        json_post=_fn('fn(Text, any, Number) -> Task', 'network'),
        redirect=_pure('fn(Text, Number) -> Response'),
        not_found=_pure('fn(Text) -> Response'),
        response=_pure('fn(Number, Text) -> Response'),
        response_json=_pure('fn(Number, any) -> Response'),
    ),
    'graphics': _module(
        'graphics',
        'omnisys/graphics.js',
        ('core',),
        canvas=_pure('fn(Number, Number) -> Canvas'),
        clear=_pure('fn(Canvas, Text) -> Canvas'),
        line=_pure('fn(Canvas, Number, Number, Number, Number, Text) -> Canvas'),
        rect=_pure('fn(Canvas, Number, Number, Number, Number, Text) -> Canvas'),
        circle=_pure('fn(Canvas, Number, Number, Number, Text) -> Canvas'),
        polygon=_pure('fn(Canvas, List, Text) -> Canvas'),
        text=_pure('fn(Canvas, Text, Number, Number, Text) -> Canvas'),
        fill=_pure('fn(Canvas, Text) -> Canvas'),
        stroke=_pure('fn(Canvas, Text) -> Canvas'),
        render=_pure('fn(Canvas) -> List'),
        to_json=_pure('fn(Canvas) -> Map'),
    ),
    'gpu': _module(
        'gpu',
        'omnisys/gpu.js',
        ('core', 'graphics'),
        buffer=_fn('fn(List) -> Buffer', 'GPU'),
        compute=_fn('fn(fn, List, Number) -> List', 'GPU'),
        parallel=_fn('fn(fn, List) -> List', 'GPU'),
        add=_fn('fn(List, List) -> List', 'GPU'),
        scale=_fn('fn(List, Number) -> List', 'GPU'),
        dot=_fn('fn(List, List) -> Number', 'GPU'),
        matmul=_fn('fn(List, List) -> List', 'GPU'),
        normalize=_fn('fn(List) -> List', 'GPU'),
        device_info=_fn('fn() -> Map', 'GPU'),
    ),
    'scene': _module(
        'scene',
        'omnisys/scene.js',
        ('core',),
        new_scene=_pure('fn() -> Scene'),
        node=_pure('fn(Scene, Text) -> Node'),
        mesh=_pure('fn(Scene, Text, Text) -> Node'),
        camera=_pure('fn(Scene, Text) -> Node'),
        light=_pure('fn(Scene, Text, Text) -> Node'),
        add=_pure('fn(Scene, Text, Text) -> Scene'),
        transform=_pure('fn(Scene, Text, Map) -> Scene'),
        remove=_pure('fn(Scene, Text) -> Scene'),
        snapshot=_pure('fn(Scene) -> Map'),
        update=_pure('fn(Scene, Number) -> Scene'),
        to_json=_pure('fn(Scene) -> Map'),
    ),
    'sim': _module(
        'sim',
        'omnisys/sim.js',
        ('core', 'collections'),
        world=_pure('fn() -> World'),
        entity=_pure('fn(World, Text) -> Entity'),
        component=_pure('fn(World, Text, Text, any) -> World'),
        get=_pure('fn(World, Text, Text) -> any'),
        system=_pure('fn(World, fn) -> World'),
        run=_pure('fn(World, Number) -> World'),
        query=_pure('fn(World, Text) -> List'),
        remove_entity=_pure('fn(World, Text) -> World'),
        snapshot=_pure('fn(World) -> Map'),
        entities=_pure('fn(World) -> List'),
    ),
    'audio': _module(
        'audio',
        'omnisys/audio.js',
        ('core',),
        buffer=_pure('fn(Number) -> AudioBuffer'),
        tone=_pure('fn(Number, Number, Number) -> AudioBuffer'),
        silence=_pure('fn(Number, Number) -> AudioBuffer'),
        sample=_pure('fn(AudioBuffer, Number) -> Number'),
        mix=_pure('fn(AudioBuffer, AudioBuffer) -> AudioBuffer'),
        append=_pure('fn(AudioBuffer, AudioBuffer) -> AudioBuffer'),
        gain=_pure('fn(AudioBuffer, Number) -> AudioBuffer'),
        encode_wav=_pure('fn(AudioBuffer) -> Text'),
        duration=_pure('fn(AudioBuffer) -> Number'),
        length=_pure('fn(AudioBuffer) -> Number'),
    ),
    'video': _module(
        'video',
        'omnisys/video.js',
        ('core', 'audio'),
        frame=_pure('fn(Number, Number) -> VideoFrame'),
        frame_from_ascii=_pure('fn(List) -> VideoFrame'),
        set_pixel=_pure('fn(VideoFrame, Number, Number, Text) -> VideoFrame'),
        timeline=_pure('fn(Number) -> Timeline'),
        add_frame=_pure('fn(Timeline, VideoFrame) -> Timeline'),
        seek=_pure('fn(Timeline, Number) -> VideoFrame'),
        frame_count=_pure('fn(Timeline) -> Number'),
        fps_of=_pure('fn(Timeline) -> Number'),
        metadata=_pure('fn(Timeline) -> Map'),
    ),
    'platform': _module(
        'platform',
        'omnisys/platform.js',
        ('core',),
        info=_fn('fn() -> Map', 'process'),
        os=_fn('fn() -> Text', 'process'),
        arch=_fn('fn() -> Text', 'process'),
        env=_fn('fn(Text, Text?) -> Text', 'process'),
        now=_pure('fn() -> Number'),
        sleep_ms=_fn('fn(Number) -> Number', 'process'),
        capabilities=_pure('fn() -> List'),
    ),
    'crypto': _module(
        'crypto',
        'omnisys/crypto.js',
        ('core', 'error'),
        sha256=_pure('fn(Text) -> Text'),
        sha1=_pure('fn(Text) -> Text'),
        hmac=_pure('fn(Text, Text) -> Text'),
        to_hex=_pure('fn(Text) -> Text'),
        from_hex=_pure('fn(Text) -> Text'),
        random_bytes=_fn('fn(Number) -> Text', 'secrets'),
        encrypt_aes=_fn('fn(Text, Text) -> Map', 'secrets'),
        decrypt_aes=_fn('fn(Map, Text) -> Text', 'secrets'),
        kdf=_fn('fn(Text, Text, Number) -> Text', 'secrets'),
        constant_time_eq=_pure('fn(Text, Text) -> Boolean'),
    ),
    'auth': _module(
        'auth',
        'omnisys/auth.js',
        ('core', 'crypto'),
        token=_fn('fn(Text, Map, Text) -> Text', 'secrets'),
        verify_token=_fn('fn(Text, Text) -> Map', 'secrets'),
        token_subject=_fn('fn(Text) -> Text', 'secrets'),
        hash_password=_fn('fn(Text, Text) -> Text', 'secrets'),
        verify_password=_fn('fn(Text, Text) -> Boolean', 'secrets'),
        session_new=_fn('fn(Text, Text, Number) -> Map', 'secrets'),
        session_valid=_fn('fn(Map) -> Boolean', 'secrets'),
    ),
    'observability': _module(
        'observability',
        'omnisys/observability.js',
        ('core', 'collections'),
        log=_pure('fn(Text, Text, Map) -> None'),
        info=_pure('fn(Text, Map) -> None'),
        warn=_pure('fn(Text, Map) -> None'),
        error=_pure('fn(Text, Map) -> None'),
        metric=_pure('fn(Text, Number) -> None'),
        metric_value=_pure('fn(Text) -> Number'),
        trace_begin=_pure('fn(Text) -> Number'),
        trace_end=_pure('fn(Number, Map) -> None'),
        snapshot=_pure('fn() -> Map'),
        clear=_pure('fn() -> None'),
        profile=_pure('fn(fn, Number) -> Number'),
    ),
    'tool': _module(
        'tool',
        'omnisys/tool.js',
        ('core',),
        tokenize=_pure('fn(Text) -> List'),
        check=_fn('fn(Text) -> Map', 'process'),
        explain=_fn('fn(Text) -> Map', 'process'),
        line_count=_pure('fn(Text) -> Number'),
        identifier_count=_pure('fn(Text) -> Number'),
    ),
    'ai': _module(
        'ai',
        'omnisys/ai.js',
        ('core',),
        tensor=_pure('fn(List, List) -> Tensor'),
        tensor_zeros=_pure('fn(List) -> Tensor'),
        tensor_ones=_pure('fn(List) -> Tensor'),
        tensor_shape=_pure('fn(Tensor) -> List'),
        tensor_add=_pure('fn(Tensor, Tensor) -> Tensor'),
        tensor_scale=_pure('fn(Tensor, Number) -> Tensor'),
        tensor_matmul=_pure('fn(Tensor, Tensor) -> Tensor'),
        tensor_relu=_pure('fn(Tensor) -> Tensor'),
        tensor_sigmoid=_pure('fn(Tensor) -> Tensor'),
        tensor_sum=_pure('fn(Tensor) -> Number'),
        tensor_to_json=_pure('fn(Tensor) -> Map'),
        tensor_from_json=_pure('fn(Map) -> Tensor'),
        linear=_pure('fn(List, List, List) -> List'),
        softmax=_pure('fn(List) -> List'),
        predict=_pure('fn(List, List) -> List'),
    ),
    'pkg': _module(
        'pkg',
        'omnisys/pkg.js',
        ('core', 'serde', 'fs'),
        manifest=_fn('fn(Text) -> Map', 'filesystem'),
        create=_pure('fn(Text, Text, Map) -> Map'),
        resolve=_pure('fn(Text, Text, Map) -> List'),
        install=_fn('fn(Text, Map) -> Map', 'filesystem'),
        registry_add=_pure('fn(Map, Text, Map) -> Map'),
        registry_get=_pure('fn(Map, Text, Text) -> Map'),
        list_dependencies=_pure('fn(Map) -> List'),
        parse_version=_pure('fn(Text) -> Map'),
        satisfies=_pure('fn(Text, Text) -> Boolean'),
        resolve_versions=_pure('fn(List, Map, Map) -> Map'),
        compute_checksum=_pure('fn(Text) -> Text'),
    ),
}


ROOT_NAMESPACES = ('omnisys', 'OMNISYS')


def resolve_import(path: tuple[str, ...]) -> OmnisysModule | None:
    """Resolve an `import` path to an OMNISYS module (or None when invalid)."""
    if not path:
        return None
    if path[0] != 'OMNISYS':
        return None
    if len(path) == 1:
        return OMNISYS_MODULES['core']
    if len(path) == 2:  # noqa: PLR2004
        return OMNISYS_MODULES.get(path[1])
    return None


def is_omnisys_call(name: str) -> bool:
    """Return True when `name` is a dotted OMNISYS call (`omnisys.<module>.<fn>`)."""
    for root in ROOT_NAMESPACES:
        if name.startswith(root + '.'):
            parts = name.split('.')
            return (
                len(parts) == 3  # noqa: PLR2004
                and parts[1] in OMNISYS_MODULES
                and parts[2] in OMNISYS_MODULES[parts[1]].functions
            )
    return False


def omnisys_effects(name: str) -> set[str]:
    """Return the declared capability effects for an OMNISYS call name."""
    if not is_omnisys_call(name):
        return set()
    _, module_name, fn_name = name.split('.')
    fn = OMNISYS_MODULES[module_name].functions[fn_name]
    return set(fn.effects)


def js_files_for(imports: list[list[str]]) -> list[str]:
    """Return repo-relative JS implementation files for the imported modules.

    Files are returned in dependency order (deps first, deduplicated).
    """
    wanted: dict[str, OmnisysModule] = {}
    for path in imports:
        resolved = resolve_import(tuple(path))
        if resolved is None:
            continue
        _collect_deps(resolved, wanted)
    ordered: list[str] = []
    seen: set[str] = set()
    for module_name in sorted(wanted):
        module = wanted[module_name]
        for dep_name in module.js_deps:
            dep = OMNISYS_MODULES[dep_name]
            if dep.js_file not in seen:
                seen.add(dep.js_file)
                ordered.append(dep.js_file)
        if module.js_file not in seen:
            seen.add(module.js_file)
            ordered.append(module.js_file)
    return ordered


def _collect_deps(module: OmnisysModule, into: dict[str, OmnisysModule]) -> None:
    for dep_name in module.js_deps:
        dep = OMNISYS_MODULES[dep_name]
        if dep_name not in into:
            _collect_deps(dep, into)
            into[dep_name] = dep
    into[module_name_of(module.js_file)] = module


def module_name_of(js_file: str) -> str:
    """Return the OMNISYS module name for a repo-relative JS implementation file."""
    return js_file.rsplit('/', 1)[-1].removesuffix('.js')


def module_names() -> list[str]:
    """Return the sorted OMNISYS module names."""
    return sorted(OMNISYS_MODULES)

```

## File: `omni_compiler\parser.py`
```python
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

```

## File: `omni_compiler\rust_emitter.py`
```python
# ruff: noqa: Q000, PLR0911, PLR0912
"""Rust Emitter Module with Bevy ECS Adapter and SQLite Support.

Generates Rust 2021 code from OMNI MIR for native targets. The emitted code
uses the ``bevy`` crate for the simulation layer (``sim.*`` calls) and is a
plain, dependency-free program otherwise. Bevy sections are delimited by
comments so the simulation parts can be stripped and the file still compiles.

SQLite support is enabled via the ``sqlite`` feature flag which adds
``rusqlite`` and ``serde_json`` dependencies.

Floating-point conformance: Rust's f64 follows IEEE 754 by default.
This module provides explicit helpers for consistent behavior across backends.
"""

from typing import Any

MIN_QUOTE_LEN = 2


def _rs_type(omni_type: str) -> str:
    """Map an OmniScript type to a Rust type."""
    type_map = {
        'Number': 'f64',
        'Text': 'String',
        'Boolean': 'bool',
        'List': 'Vec<f64>',
        'None': '()',
    }
    return type_map.get(omni_type, omni_type)


def _rs_text(raw: str) -> str:
    """Format a string literal for Rust."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    return f'"{body}"'


def _rs_text_expr(raw: str) -> str:
    """Render a text literal with ``{slot}`` interpolation as a format! call."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    fmt_parts: list[str] = []
    args: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i + 1] in '{}.}':
            buf.append(body[i + 1])
            i += 2
        elif body[i] == '{':
            j = body.find('}', i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1 : j]
            if buf:
                fmt_parts.append(''.join(buf).replace('{', '{{').replace('}', '}}'))
                buf = []
            fmt_parts.append('{}')
            args.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append(''.join(buf).replace('{', '{{').replace('}', '}}'))
    fmt = ''.join(fmt_parts)
    if not args:
        return f'String::from("{fmt}")'
    return f'format!("{fmt}", {", ".join(args)})'


def _rs_expr(e: dict[str, Any], declared: set[str]) -> str:
    op = e.get('op')
    if op == 'number':
        val = str(e['value'])
        return f'{val}.0' if '.' not in val and 'e' not in val.lower() else val
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return '()'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        return _rs_text_expr(str(e['value']))
    if op == 'call':
        if e['name'] == 'join' and len(e['args']) == MIN_QUOTE_LEN:
            lst = _rs_expr(e['args'][0], declared)
            sep = _rs_expr(e['args'][1], declared)
            return f'omni_join({lst}, {sep})'
        if str(e['name']).startswith('sim.'):
            return _rs_sim_call(e, declared)
        args = ', '.join(_rs_expr(a, declared) for a in e['args'])
        return f'{e["name"]}({args})'
    if op == 'list':
        items = ', '.join(_rs_expr(i, declared) for i in e['items'])
        return f'vec![{items}]'
    if op == 'map':
        pairs = ', '.join(
            f'("{k}".to_string(), {_rs_expr(v, declared)})' for k, v in e.get('items', {}).items()
        )
        return f'omni_map(vec![{pairs}])'
    if op == 'index':
        return (
            f'{_rs_expr(e.get("object", {}), declared)}[{_rs_expr(e.get("index", {}), declared)}]'
        )
    if op == 'await':
        return _rs_expr(e.get('expr', {}), declared)
    if op == 'field':
        return f'{_rs_expr(e["object"], declared)}.{e["field"]}'
    if op == 'struct':
        parts = [f'{name}: {_rs_expr(value, declared)}' for name, value in e['args'].items()]
        return f'{e["name"]} {{ {", ".join(parts)} }}'
    if op == 'group':
        return f'({_rs_expr(e["expr"], declared)})'
    if op == 'not':
        return f'(!{_rs_expr(e["operand"], declared)})'
    if op == 'neg':
        return f'(-{_rs_expr(e["operand"], declared)})'
    op_str = str(op)
    if op_str == '/':
        return f'omni_fp_divide({_rs_expr(e["left"], declared)}, {_rs_expr(e["right"], declared)})'
    if op_str == '%':
        return f'omni_fp_modulo({_rs_expr(e["left"], declared)}, {_rs_expr(e["right"], declared)})'
    op_map = {
        'is': '==',
        'is not': '!=',
        'and': '&&',
        'or': '||',
        'greater than': '>',
        'less than': '<',
        'greater or equal': '>=',
        'less or equal': '<=',
    }
    cop = op_map.get(op_str, op_str)
    return f'{_rs_expr(e["left"], declared)} {cop} {_rs_expr(e["right"], declared)}'


def _rs_sim_call(e: dict[str, Any], declared: set[str]) -> str:
    """Lower a sim.* call inside a function to its Bevy/plain form."""
    name = str(e.get('name', ''))
    args = e.get('args', [])
    if name == 'sim.entity':
        name_arg = _rs_text(str(args[0].get('value', 'entity')))
        return f'// sim.entity {name_arg} -> Bevy spawn in App setup'
    if name == 'sim.system':
        fn_arg = str(args[1].get('name', '')) if len(args) > 1 else ''
        return f'// sim.system {fn_arg} -> Bevy Update system'
    if name == 'sim.for_each':
        return '// sim.for_each -> Bevy Query'
    if name == 'sim.run':
        n = _rs_expr(args[0], declared) if args else '0'
        return f'// sim.run {n} -> Bevy run {n} frames'
    if name == 'sim.query':
        comp = _rs_text(str(args[0].get('value', ''))) if args else '""'
        return f'// sim.query {comp} -> Bevy Query'
    return f'{name}({", ".join(_rs_expr(a, declared) for a in args)})'


def _rs_sim_assign(stmt: dict[str, Any]) -> str:
    """Lower an assignment whose value is a ``sim.*`` call to a compilable stub."""
    name = str(stmt['name'])
    sim_name = str(stmt['expr'].get('name', ''))
    args = stmt['expr'].get('args', [])
    if sim_name == 'sim.query':
        comp = _rs_text(str(args[0].get('value', ''))) if args else '""'
        return f'let mut {name}: Vec<f64> = Vec::new(); // sim.query {comp} -> Bevy Query'
    if sim_name == 'sim.run':
        n = _rs_expr(args[0], set()) if args else '0'
        return f'let mut {name} = 0.0; // sim.run {n} -> Bevy run frames'
    return f'let mut {name} = 0.0; // {sim_name} -> Bevy'


def _rs_stmt(s: dict[str, Any], declared: set[str], indent: int = 4) -> str:
    pad = ' ' * indent
    op = s.get('op')
    if op == 'assign':
        var_name = s['name']
        if var_name not in declared:
            declared.add(var_name)
            return f'{pad}let mut {var_name} = {_rs_expr(s["expr"], declared)};'
        return f'{pad}{var_name} = {_rs_expr(s["expr"], declared)};'
    if op == 'return':
        return f'{pad}return {_rs_expr(s["expr"], declared)};'
    if op == 'show':
        return f'{pad}println!("{{}}", {_rs_expr(s["expr"], declared)});'
    if op == 'break':
        return f'{pad}break;'
    if op == 'continue':
        return f'{pad}continue;'
    if op == 'if':
        lines = [f'{pad}if {_rs_expr(s["cond"], declared)} {{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        if s.get('else'):
            lines.append(f'{pad}else {{')
            for st in s['else']:
                lines.append(_rs_stmt(st, declared, indent + 2))
            lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'for':
        var = s['var']
        iterable = _rs_expr(s['iterable'], declared)
        lines = [f'{pad}for x in &{iterable} {{', f'{pad}  let {var} = x;']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'{pad}while {_rs_expr(s["cond"], declared)} {{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'try':
        lines = [f'{pad}// try/catch lowered to a match guard', f'{pad}{{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        for st in s.get('on_error', []):
            lines.append(_rs_stmt(st, declared, indent + 2))
        if s.get('finally'):
            for st in s['finally']:
                lines.append(_rs_stmt(st, declared, indent + 2))
        return '\n'.join(lines)
    if op == 'global':
        return f'{pad}// global {s.get("name", "")}'
    if op == 'call':
        return f'{pad}{_rs_expr(s, declared)};'
    return f'{pad}// unknown statement: {s!r}'


def _rs_preamble(custom_types: dict[str, Any]) -> list[str]:  # noqa: PLR0915
    lines = [
        '// Generated by the OmniScript Rust Emitter (v3.4)',
        '',
        '// Bevy ECS integration (optional).',
        '// Remove the `bevy` sections below to build as a plain Rust program.',
        '// #[cfg(feature = "bevy")]',
        '// use bevy::prelude::*;',
        '',
        '// SQLite support (optional, enabled via `sqlite` feature)',
        '// #[cfg(feature = "sqlite")]',
        '// use rusqlite::{Connection, Result as SqliteResult, params, params_from_iter};',
        '// #[cfg(feature = "sqlite")]',
        '// use serde_json::{json, Value as JsonValue};',
        '// #[cfg(feature = "sqlite")]',
        '// use std::sync::Mutex;',
        '// #[cfg(feature = "sqlite")]',
        '// static SQLITE_DB: Mutex<Option<Connection>> = Mutex::new(None);',
        '',
        '// IEEE 754 Floating-Point Conformance Helpers (Rust f64 is IEEE 754 compliant)',
        'fn omni_fp_is_nan(x: f64) -> bool { x.is_nan() }',
        'fn omni_fp_is_finite(x: f64) -> bool { x.is_finite() }',
        'fn omni_fp_is_infinite(x: f64) -> bool { x.is_infinite() }',
        'fn omni_fp_divide(a: f64, b: f64) -> f64 {',
        '    if b == 0.0 {',
        '        if a == 0.0 { return f64::NAN; }',
        '        return if a > 0.0 { f64::INFINITY } else { f64::NEG_INFINITY };',
        '    }',
        '    a / b',
        '}',
        'fn omni_fp_modulo(a: f64, b: f64) -> f64 {',
        '    if b == 0.0 || a.is_nan() || b.is_nan() { return f64::NAN; }',
        '    if a.is_infinite() { return f64::NAN; }',
        '    a % b',
        '}',
        'fn omni_fp_neg_zero() -> f64 { -0.0 }',
        'fn omni_fp_copy_sign(x: f64, y: f64) -> f64 { x.copysign(y) }',
        '',
    ]

    # SQLite functions (enabled via `sqlite` feature)
    lines.extend(
        [
            '#[cfg(feature = "sqlite")]',
            '// Global SQLite connection',
            'static SQLITE_DB: Mutex<Option<Connection>> = Mutex::new(None);',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_open(path) - open or create SQLite database',
            '// path: None for in-memory, Some(path) for file',
            'fn omnisys_db_open(path: Option<String>) -> Result<(), Box<dyn std::error::Error>> {',
            '    let mut db = SQLITE_DB.lock().unwrap();',
            '    if db.is_some() {',
            '        *db = None;',
            '    }',
            '    let conn = match path {',
            '        Some(p) if !p.is_empty() => Connection::open(p)?,',
            '        _ => Connection::open_in_memory()?,',
            '    };',
            '    conn.execute("PRAGMA foreign_keys = ON", [])?;',
            '    *db = Some(conn);',
            '    Ok(())',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_exec(sql, params_json) - execute DDL/DML',
            '// params_json: JSON array of parameters',
            'fn omnisys_db_exec(sql: &str, params_json: &str) -> Result<i64, Box<dyn std::error::Error>> {',  # noqa: E501
            '    let db = SQLITE_DB.lock().unwrap();',
            '    let conn = db.as_ref().ok_or("No database open")?;',
            '    let params: Vec<JsonValue> = serde_json::from_str(params_json).unwrap_or_default();',  # noqa: E501
            '    let mut stmt = conn.prepare(sql)?;',
            '    let param_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|v| v as &dyn rusqlite::ToSql).collect();',  # noqa: E501
            '    let changed = stmt.execute(params_from_iter(param_refs))?;',
            '    Ok(changed as i64)',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_query(sql, params_json) - execute SELECT and return JSON string',
            'fn omnisys_db_query(sql: &str, params_json: &str) -> Result<String, Box<dyn std::error::Error>> {',  # noqa: E501
            '    let db = SQLITE_DB.lock().unwrap();',
            '    let conn = db.as_ref().ok_or("No database open")?;',
            '    let params: Vec<JsonValue> = serde_json::from_str(params_json).unwrap_or_default();',  # noqa: E501
            '    let mut stmt = conn.prepare(sql)?;',
            '    let param_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|v| v as &dyn rusqlite::ToSql).collect();',  # noqa: E501
            '    let rows = stmt.query_map(params_from_iter(param_refs), |row| {',
            '        let col_count = row.column_count();',
            '        let mut map = serde_json::Map::new();',
            '        for i in 0..col_count {',
            '            let name = row.column_name(i).unwrap_or("").to_string();',
            '            let value: JsonValue = match row.get_ref(i)? {',
            '                rusqlite::types::ValueRef::Null => JsonValue::Null,',
            '                rusqlite::types::ValueRef::Integer(i) => json!(i),',
            '                rusqlite::types::ValueRef::Real(f) => json!(f),',
            '                rusqlite::types::ValueRef::Text(t) => json!(String::from_utf8_lossy(t).to_string()),',  # noqa: E501
            '                rusqlite::types::ValueRef::Blob(b) => json!(b.to_vec()),',
            '            };',
            '            map.insert(name, value);',
            '        }',
            '        Ok(JsonValue::Object(map))',
            '    })?;',
            '    let mut results = Vec::new();',
            '    for row in rows {',
            '        results.push(row?);',
            '    }',
            '    Ok(serde_json::to_string(&results)?)',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_close() - close SQLite database',
            'fn omnisys_db_close() {',
            '    let mut db = SQLITE_DB.lock().unwrap();',
            '    *db = None;',
            '}',
            '',
        ]
    )

    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        lines.append('#[derive(Clone, Debug)]')
        lines.append(f'struct {tname} {{')
        for fname, ftype in fields.items():
            lines.append(f'    {fname}: {_rs_type(ftype)},')
        lines.append('}')
        lines.append('')
    lines.append('fn omni_join(list: Vec<String>, sep: &str) -> String {')
    lines.append('    list.join(sep)')
    lines.append('}')
    lines.append('')
    lines.append('fn omni_map<K, V>(pairs: Vec<(K, V)>) -> std::collections::HashMap<K, V> {')
    lines.append('    pairs.into_iter().collect()')
    lines.append('}')
    lines.append('')
    lines.append('// OMNISYS.async stubs (no-op for Rust target)')
    lines.append('struct OmniTask {')
    lines.append('    handle: *mut std::ffi::c_void,')
    lines.append('    cancel: fn(*mut std::ffi::c_void),')
    lines.append('}')
    lines.append('fn omni_async_cancel_stub(_handle: *mut std::ffi::c_void) {}')
    lines.append(
        'fn omnisys_async_task(fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: fn, cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_delay(_ms: f64) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_interval(_ms: f64, _fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_timeout(_ms: f64, _fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_tick(_fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append('fn omnisys_async_cancel(task: OmniTask) { (task.cancel)(task.handle); }')
    lines.append('fn omnisys_async_await(task: OmniTask) -> *mut std::ffi::c_void { task.handle }')
    lines.append('')

    # OMNISYS.pkg — Semantic Versioning & Lockfile Support
    lines.append('/// Parsed semantic version (SemVer 2.0.0)')
    lines.append('#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]')
    lines.append('struct OmniVersion {')
    lines.append('    major: u64,')
    lines.append('    minor: u64,')
    lines.append('    patch: u64,')
    lines.append('    prerelease: String,')
    lines.append('    build: String,')
    lines.append('}')
    lines.append('')
    lines.append('impl std::fmt::Display for OmniVersion {')
    lines.append("    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {")
    lines.append('        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)?;')
    lines.append('        if !self.prerelease.is_empty() {')
    lines.append('            write!(f, "-{}", self.prerelease)?;')
    lines.append('        }')
    lines.append('        if !self.build.is_empty() {')
    lines.append('            write!(f, "+{}", self.build)?;')
    lines.append('        }')
    lines.append('        Ok(())')
    lines.append('    }')
    lines.append('}')
    lines.append('')
    lines.append('/// Parse a semantic version string')
    lines.append('fn omni_pkg_parse_version(version: &str) -> Result<OmniVersion, String> {')
    lines.append('    let version = version.trim();')
    lines.append('    let re = regex::Regex::new(')
    lines.append(
        '        r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"'  # noqa: E501
    )
    lines.append('    ).map_err(|_| "Invalid regex".to_string())?;')
    lines.append(
        '    let caps = re.captures(version).ok_or_else(|| format!("Invalid semantic version: {}", version))?;'  # noqa: E501
    )
    lines.append('    Ok(OmniVersion {')
    lines.append('        major: caps[1].parse().unwrap(),')
    lines.append('        minor: caps[2].parse().unwrap(),')
    lines.append('        patch: caps[3].parse().unwrap(),')
    lines.append(
        '        prerelease: caps.get(4).map(|m| m.as_str().to_string()).unwrap_or_default(),'
    )
    lines.append('        build: caps.get(5).map(|m| m.as_str().to_string()).unwrap_or_default(),')
    lines.append('    })')
    lines.append('}')
    lines.append('')
    lines.append('/// Compare two versions')
    lines.append(
        'fn omni_pkg_cmp_version(a: &OmniVersion, b: &OmniVersion) -> std::cmp::Ordering {'
    )
    lines.append('    match a.major.cmp(&b.major) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    match a.minor.cmp(&b.minor) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    match a.patch.cmp(&b.patch) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    let a_pre = !a.prerelease.is_empty();')
    lines.append('    let b_pre = !b.prerelease.is_empty();')
    lines.append('    match (a_pre, b_pre) {')
    lines.append('        (true, false) => return std::cmp::Ordering::Less,')
    lines.append('        (false, true) => return std::cmp::Ordering::Greater,')
    lines.append('        (true, true) => return a.prerelease.cmp(&b.prerelease),')
    lines.append('        _ => {}')
    lines.append('    }')
    lines.append('    std::cmp::Ordering::Equal')
    lines.append('}')
    lines.append('')
    lines.append('/// Check if version satisfies constraint')
    lines.append('/// Supports: ^ (caret), ~ (tilde), >=, <=, >, <, =, ==, || (union)')
    lines.append('fn omni_pkg_satisfies(version: &str, constraint: &str) -> bool {')
    lines.append('    let v = match omni_pkg_parse_version(version) {')
    lines.append('        Ok(v) => v,')
    lines.append('        Err(_) => return false,')
    lines.append('    };')
    lines.append('    for part in constraint.split("||") {')
    lines.append('        let part = part.trim();')
    lines.append('        if part.is_empty() { continue; }')
    lines.append("        if part.starts_with('^') {")
    lines.append('            if let Ok(target) = omni_pkg_parse_version(&part[1..]) {')
    lines.append('                let upper = if target.major == 0 {')
    lines.append('                    if target.minor == 0 {')
    lines.append(
        '                        OmniVersion { major: 0, minor: 0, patch: target.patch + 1, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                    } else {')
    lines.append(
        '                        OmniVersion { major: 0, minor: target.minor + 1, patch: 0, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                    }')
    lines.append('                } else {')
    lines.append(
        '                    OmniVersion { major: target.major + 1, minor: 0, patch: 0, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                };')
    lines.append('                if v >= target && v < upper { return true; }')
    lines.append('            }')
    lines.append("        } else if part.starts_with('~') {")
    lines.append('            if let Ok(target) = omni_pkg_parse_version(&part[1..]) {')
    lines.append(
        '                let upper = OmniVersion { major: target.major, minor: target.minor + 1, patch: 0, prerelease: String::new(), build: String::new() };'  # noqa: E501
    )
    lines.append('                if v >= target && v < upper { return true; }')
    lines.append('            }')
    lines.append(
        '        } else if part.starts_with(">=") || part.starts_with("<=") || part.starts_with(">") || part.starts_with("<") || part.starts_with("==") || part.starts_with(\'=\') {'  # noqa: E501
    )
    lines.append(
        '            let (op, ver_str) = if part.starts_with(">=") || part.starts_with("<=") || part.starts_with("==") {'  # noqa: E501
    )
    lines.append('                (&part[..2], &part[2..])')
    lines.append('            } else {')
    lines.append('                (&part[..1], &part[1..])')
    lines.append('            };')
    lines.append('            let ver_str = ver_str.trim();')
    lines.append('            if let Ok(target) = omni_pkg_parse_version(ver_str) {')
    lines.append('                let cmp = v.cmp(&target);')
    lines.append('                let matches = match op {')
    lines.append('                    ">=" => cmp >= std::cmp::Ordering::Equal,')
    lines.append('                    "<=" => cmp <= std::cmp::Ordering::Equal,')
    lines.append('                    ">" => cmp == std::cmp::Ordering::Greater,')
    lines.append('                    "<" => cmp == std::cmp::Ordering::Less,')
    lines.append('                    "=" | "==" => cmp == std::cmp::Ordering::Equal,')
    lines.append('                    _ => false,')
    lines.append('                };')
    lines.append('                if matches { return true; }')
    lines.append('            }')
    lines.append('        } else {')
    lines.append('            if let Ok(target) = omni_pkg_parse_version(part) {')
    lines.append('                if v == target { return true; }')
    lines.append('            }')
    lines.append('        }')
    lines.append('    }')
    lines.append('    false')
    lines.append('}')
    lines.append('')
    lines.append('/// Compute SHA256 checksum of content')
    lines.append('fn omni_pkg_compute_checksum(content: &str) -> String {')
    lines.append('    use sha2::{Sha256, Digest};')
    lines.append('    let mut hasher = Sha256::new();')
    lines.append('    hasher.update(content.as_bytes());')
    lines.append('    let result = hasher.finalize();')
    lines.append('    format!("sha256:{}", hex::encode(result))')
    lines.append('}')
    lines.append('')
    lines.append('/// Lockfile entry')
    lines.append('#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]')
    lines.append('struct OmniLockfileEntry {')
    lines.append('    name: String,')
    lines.append('    version: String,')
    lines.append('    checksum: String,')
    lines.append('    dependencies: std::collections::HashMap<String, String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Lockfile')
    lines.append('#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]')
    lines.append('struct OmniLockfile {')
    lines.append('    version: u32,')
    lines.append('    packages: Vec<OmniLockfileEntry>,')
    lines.append('    metadata: std::collections::HashMap<String, serde_json::Value>,')
    lines.append('}')
    lines.append('')
    lines.append('impl OmniLockfile {')
    lines.append('    fn new() -> Self {')
    lines.append(
        '        Self { version: 1, packages: Vec::new(), metadata: std::collections::HashMap::new() }'  # noqa: E501
    )
    lines.append('    }')
    lines.append('    fn add(&mut self, entry: OmniLockfileEntry) { self.packages.push(entry); }')
    lines.append(
        '    fn get(&self, name: &str) -> Option<&OmniLockfileEntry> { self.packages.iter().find(|e| e.name == name) }'  # noqa: E501
    )
    lines.append(
        '    fn to_json(&self) -> String { serde_json::to_string(self).unwrap_or_default() }'
    )
    lines.append(
        '    fn from_json(json: &str) -> Result<Self, serde_json::Error> { serde_json::from_str(json) }'  # noqa: E501
    )
    lines.append('}')
    lines.append('')
    lines.append('/// Package spec for resolution')
    lines.append('#[derive(Debug, Clone)]')
    lines.append('struct OmniPackageSpec {')
    lines.append('    name: String,')
    lines.append('    version_constraint: String,')
    lines.append('    dependencies: std::collections::HashMap<String, String>,')
    lines.append('    checksum: Option<String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Resolution result')
    lines.append('#[derive(Debug, Clone)]')
    lines.append('struct OmniResolution {')
    lines.append('    packages: Vec<OmniLockfileEntry>,')
    lines.append('    lockfile: OmniLockfile,')
    lines.append('    warnings: Vec<String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Deterministic version resolution')
    lines.append('fn omni_pkg_resolve_versions(')
    lines.append('    specs: &[OmniPackageSpec],')
    lines.append(
        '    registry: &std::collections::HashMap<String, std::collections::HashMap<String, serde_json::Value>>,'  # noqa: E501
    )
    lines.append('    lockfile: Option<&OmniLockfile>,')
    lines.append(') -> OmniResolution {')
    lines.append('    use std::collections::{HashMap, HashSet};')
    lines.append(
        '    let spec_by_name: HashMap<_, _> = specs.iter().map(|s| (s.name.clone(), s)).collect();'
    )
    lines.append('    let mut resolved: HashMap<String, OmniLockfileEntry> = HashMap::new();')
    lines.append('    let mut warnings = Vec::new();')
    lines.append('    let mut visiting = HashSet::new();')
    lines.append('    let mut visited = HashSet::new();')
    lines.append('')
    lines.append('    fn visit(')
    lines.append('        name: &str,')
    lines.append('        spec_by_name: &HashMap<String, &OmniPackageSpec>,')
    lines.append('        registry: &HashMap<String, HashMap<String, serde_json::Value>>,')
    lines.append('        lockfile: Option<&OmniLockfile>,')
    lines.append('        resolved: &mut HashMap<String, OmniLockfileEntry>,')
    lines.append('        visiting: &mut HashSet<String>,')
    lines.append('        visited: &mut HashSet<String>,')
    lines.append('        warnings: &mut Vec<String>,')
    lines.append('    ) {')
    lines.append('        if resolved.contains_key(name) { return; }')
    lines.append('        if visiting.contains(name) {')
    lines.append(
        '            warnings.push(format!("Circular dependency detected involving {}", name));'
    )
    lines.append('            return;')
    lines.append('        }')
    lines.append('        let Some(spec) = spec_by_name.get(name) else {')
    lines.append('            warnings.push(format!("Package {} not found in specs", name));')
    lines.append('            return;')
    lines.append('        };')
    lines.append('        visiting.insert(name.to_string());')
    lines.append('        for (dep_name, dep_constraint) in &spec.dependencies {')
    lines.append(
        '            visit(dep_name, spec_by_name, registry, lockfile, resolved, visiting, visited, warnings);'  # noqa: E501
    )
    lines.append('        }')
    lines.append(
        '        let selected_version = select_best_version(registry, name, &spec.version_constraint, lockfile);'  # noqa: E501
    )
    lines.append('        let selected_version = match selected_version {')
    lines.append('            Some(v) => v,')
    lines.append('            None => {')
    lines.append(
        '                warnings.push(format!("No version found for {} matching {}", name, spec.version_constraint));'  # noqa: E501
    )
    lines.append('                visiting.remove(name);')
    lines.append('                return;')
    lines.append('            }')
    lines.append('        };')
    lines.append(
        '        let reg_entry = registry.get(name).and_then(|v| v.get(&selected_version));'
    )
    lines.append('        let mut dep_versions = HashMap::new();')
    lines.append('        for (dep_name, _) in &spec.dependencies {')
    lines.append('            if let Some(entry) = resolved.get(dep_name) {')
    lines.append('                dep_versions.insert(dep_name.clone(), entry.version.clone());')
    lines.append('            }')
    lines.append('        }')
    lines.append('        let checksum = spec.checksum.clone().unwrap_or_else(|| {')
    lines.append('            let content = serde_json::to_string(&reg_entry).unwrap_or_default();')
    lines.append('            omni_pkg_compute_checksum(&content)')
    lines.append('        });')
    lines.append('        let entry = OmniLockfileEntry {')
    lines.append('            name: name.to_string(),')
    lines.append('            version: selected_version,')
    lines.append('            checksum,')
    lines.append('            dependencies: dep_versions,')
    lines.append('        };')
    lines.append('        resolved.insert(name.to_string(), entry);')
    lines.append('        visiting.remove(name);')
    lines.append('        visited.insert(name.to_string());')
    lines.append('    }')
    lines.append('')
    lines.append('    fn select_best_version(')
    lines.append('        registry: &HashMap<String, HashMap<String, serde_json::Value>>,')
    lines.append('        name: &str,')
    lines.append('        constraint: &str,')
    lines.append('        lockfile: Option<&OmniLockfile>,')
    lines.append('    ) -> Option<String> {')
    lines.append('        if let Some(lf) = lockfile {')
    lines.append('            if let Some(locked) = lf.get(name) {')
    lines.append('                if omni_pkg_satisfies(&locked.version, constraint) {')
    lines.append(
        '                    if registry.get(name).map(|v| v.contains_key(&locked.version)).unwrap_or(false) {'  # noqa: E501
    )
    lines.append('                        return Some(locked.version.clone());')
    lines.append('                    }')
    lines.append('                }')
    lines.append('            }')
    lines.append('        }')
    lines.append('        let versions = registry.get(name)?;')
    lines.append('        let mut vers: Vec<_> = versions.keys()')
    lines.append('            .filter_map(|v| omni_pkg_parse_version(v).ok())')
    lines.append('            .collect();')
    lines.append('        vers.sort_by(|a, b| b.cmp(a));')
    lines.append('        for v in vers {')
    lines.append('            if omni_pkg_satisfies(&v.to_string(), constraint) {')
    lines.append('                return Some(v.to_string());')
    lines.append('            }')
    lines.append('        }')
    lines.append('        None')
    lines.append('    }')
    lines.append('')
    lines.append(
        '    for spec in specs { visit(&spec.name, &spec_by_name, registry, lockfile, &mut resolved, &mut visiting, &mut visited, &mut warnings); }'  # noqa: E501
    )
    lines.append('')
    lines.append('    let mut ordered = Vec::new();')
    lines.append('    let mut seen = HashSet::new();')
    lines.append('')
    lines.append('    fn order(')
    lines.append('        name: &str,')
    lines.append('        resolved: &HashMap<String, OmniLockfileEntry>,')
    lines.append('        ordered: &mut Vec<OmniLockfileEntry>,')
    lines.append('        seen: &mut HashSet<String>,')
    lines.append('    ) {')
    lines.append('        if seen.contains(name) || !resolved.contains_key(name) { return; }')
    lines.append('        let entry = &resolved[name];')
    lines.append(
        '        for dep in entry.dependencies.keys() { order(dep, resolved, ordered, seen); }'
    )
    lines.append(
        '        if !seen.contains(name) { seen.insert(name.to_string()); ordered.push(entry.clone()); }'  # noqa: E501
    )
    lines.append('    }')
    lines.append('')
    lines.append('    for spec in specs { order(&spec.name, &resolved, &mut ordered, &mut seen); }')
    lines.append('')
    lines.append(
        '    let lockfile = OmniLockfile { version: 1, packages: ordered.clone(), metadata: std::collections::HashMap::new() };'  # noqa: E501
    )
    lines.append('    OmniResolution { packages: ordered, lockfile, warnings }')
    lines.append('}')
    lines.append('')
    lines.append('/// OMNISYS.pkg function exports for Rust target')
    lines.append(
        'fn omnisys_pkg_parse_version(version: &str) -> Result<OmniVersion, String> { omni_pkg_parse_version(version) }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_pkg_satisfies(version: &str, constraint: &str) -> bool { omni_pkg_satisfies(version, constraint) }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_pkg_compute_checksum(content: &str) -> String { omni_pkg_compute_checksum(content) }'  # noqa: E501
    )
    lines.append('fn omnisys_pkg_lockfile_new() -> OmniLockfile { OmniLockfile::new() }')
    lines.append('fn omnisys_pkg_lockfile_to_json(lf: &OmniLockfile) -> String { lf.to_json() }')
    lines.append(
        'fn omnisys_pkg_lockfile_from_json(json: &str) -> Result<OmniLockfile, serde_json::Error> { OmniLockfile::from_json(json) }'  # noqa: E501
    )
    lines.append('fn omnisys_pkg_resolve_versions(')
    lines.append('    specs: &[OmniPackageSpec],')
    lines.append(
        '    registry: &std::collections::HashMap<String, std::collections::HashMap<String, serde_json::Value>>,'  # noqa: E501
    )
    lines.append('    lockfile: Option<&OmniLockfile>,')
    lines.append(') -> OmniResolution { omni_pkg_resolve_versions(specs, registry, lockfile) }')
    lines.append('')
    return lines


def _rs_sim_components(mir: Any) -> tuple[list[str], list[str]]:
    """Return (component structs, spawn functions) for sim.* usage in entry point."""
    used: list[str] = []
    structs: list[str] = []
    spawn_lines: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get('op') != 'call' or not str(stmt.get('name', '')).startswith('sim.'):
            continue
        for arg in stmt.get('args', []):
            if arg.get('op') != 'list':
                continue
            for item in arg.get('items', []):
                if item.get('op') == 'struct' and item['name'] not in used:
                    used.append(item['name'])
    for tname in used:
        fields_info = mir.types.get(tname, {})
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        structs.append('#[derive(Component, Clone, Debug)]')
        structs.append(f'struct {tname} {{')
        for fname, ftype in fields.items():
            structs.append(f'    {fname}: {_rs_type(ftype)},')
        structs.append('}')
        structs.append('')
    if used:
        spawn_lines.append('// Bevy app setup (sim.entity / sim.system / sim.for_each)')
        spawn_lines.append('#[cfg(feature = "bevy")]')
        spawn_lines.append('fn setup(mut commands: Commands) {')
        for stmt in mir.entry_point:
            is_entity = (
                stmt.get('op') == 'call'
                and str(stmt.get('name', '')) == 'sim.entity'
                and len(stmt.get('args', [])) >= MIN_QUOTE_LEN
            )
            if is_entity:
                name_arg = _rs_text(str(stmt['args'][0].get('value', 'entity')))
                spawn_lines.append('    commands.spawn((')
                for item in stmt['args'][1].get('items', []):
                    if item.get('op') == 'struct':
                        spawn_lines.append(f'        {_rs_expr(item, set())},')
                spawn_lines.append(f'    )).insert(Name::new({name_arg}));')
        spawn_lines.append('}')
        spawn_lines.append('')
    return structs, spawn_lines


def emit_rust(mir: Any) -> str:
    """Emit Rust 2021 code with a Bevy adapter from OMNI MIR."""
    lines = _rs_preamble(mir.types)

    component_structs, spawn = _rs_sim_components(mir)
    if component_structs:
        lines.append('// Bevy components (sim.* usage)')
        lines.extend(component_structs)

    def _extract_cap_names(effects_list: list[Any]) -> list[Any]:
        """Extract capability names from effects list (handles both old string format and new tuple format)."""  # noqa: E501
        return [cap if isinstance(cap, str) else cap[0] for cap in effects_list]

    for fn in mir.functions.values():
        params = ', '.join(f'{p.name}: {_rs_type(p.type)}' for p in fn.params)
        ret = _rs_type(fn.return_type)
        ret_arrow = f' -> {ret}' if fn.return_type != 'None' else ''
        lines.append(f'fn {fn.name}({params}){ret_arrow} {{')
        if fn.effects.uses or fn.effects.reads or fn.effects.writes:
            uses = ', '.join(_extract_cap_names(fn.effects.uses))
            reads = ', '.join(_extract_cap_names(fn.effects.reads))
            writes = ', '.join(_extract_cap_names(fn.effects.writes))
            lines.append(f'    // effects: uses=[{uses}] reads=[{reads}] writes=[{writes}]')
        declared: set[str] = {p.name for p in fn.params}
        for stmt in fn.body:
            lines.append(_rs_stmt(stmt, declared, 4))
        lines.append('}')
        lines.append('')

    lines.extend(spawn)

    lines.append('fn main() {')
    lines.append('    // when app starts')
    declared_main: set[str] = set()
    for stmt in mir.entry_point:
        if stmt.get('op') == 'call' and str(stmt.get('name', '')).startswith('sim.'):
            lines.append('    ' + _rs_expr(stmt, declared_main))
            continue
        if (
            stmt.get('op') == 'assign'
            and stmt['expr'].get('op') == 'call'
            and str(stmt['expr'].get('name', '')).startswith('sim.')
        ):
            lines.append('    ' + _rs_sim_assign(stmt))
            continue
        lines.append(_rs_stmt(stmt, declared_main, 4))
    lines.append('}')
    lines.append('')

    if mir.scene:
        lines.append('// 3D scene: render via the JS/WebGPU lane or a Bevy scene plugin.')
        lines.append('// scene objects: ' + ', '.join(o['shape'] for o in mir.scene))

    return '\n'.join(lines)


def emit_rust_with_runtime(mir: Any) -> str:
    """Emit Rust code with the embedded runtime (alias of emit_rust)."""
    return emit_rust(mir)

```

## File: `omni_compiler\smt.py`
```python
# ruff: noqa: Q000

"""SMT verification of `require`/`ensure` contracts using Z3.

For every function in a program, the function body is proved to satisfy its
`ensure` postconditions whenever its `require` preconditions hold.  Each
return path is symbolically executed and Z3 proves the implication

    require  AND  path_condition  ==>  ensure[result := return_value]

by checking that its negation is unsatisfiable.  When the negation is
satisfiable, a concrete counterexample (parameter values and the result) is
extracted from the Z3 model.

Result schema ("omni.verify", version "1.0"), one dict per function:

    {
      "schema": "omni.verify",
      "version": "1.0",
      "function": "<name>",
      "status": "verified" | "failed" | "unsupported" | "no-contracts",
      "require": "<source text>" | None,
      "ensure": "<source text>" | None,
      "counterexample": {"<param>": value, "result": value} | None,
      "reason": "human readable explanation" | None
    }

Statuses:

* no-contracts - the function declares no `ensure` clause, so there is
  nothing to prove (also used when only `require` clauses exist).
* verified     - every return path was proved to satisfy the ensures.
* failed       - some return path violates an ensure; `counterexample`
  holds concrete inputs for which the violation occurs.
* unsupported  - the body uses a construct that cannot be modelled yet
  (lists, slots, regex, recursive calls, loops whose trip count may exceed
  the unrolling bound, ...) or Z3 could not decide the query; `reason`
  explains why.

Design notes:

* Number values are translated to Z3 Reals.  Reals are a strict superset of
  the integers used by integer literals, so the choice is sound and
  integer-looking counterexample values are rendered as Python ints (see
  `render_counterexample`).
* Division by a symbolic denominator emits `denominator != 0` as a path
  condition, so a counterexample can never rely on an ill-defined division.
* `result` inside an `ensure` is substituted with the return expression of
  the path being verified.
* Struct types (`type Point = { x: Number, y: Number }`) are modelled as Z3
  algebraic datatypes; construction and field access translate to
  datatype constructors and accessors.  Struct fields may be primitives or
  other (acyclic) struct types.
* User-defined functions called from contracts are inlined: the callee's
  `require` clauses are assumed, its body is symbolically executed, and a
  fresh result constant is constrained to match the return path taken.
  Recursive calls are reported `unsupported`.
* Loops are verified by bounded unrolling (`_LOOP_BOUND` iterations).
  A loop whose trip count is provably bounded (by `require` clauses or a
  literal iterable) is fully verified; when the trip count may exceed the
  bound, the function is reported `unsupported` rather than claiming a
  proof that was not made.  `break` and `continue` inside loops are
  modelled.

Floating-point conformance limitation:
Z3 Reals (used for Number type) are mathematical reals, NOT IEEE 754 floats.
This means:
- No NaN, +Inf, -Inf, -0.0 representations
- Division by zero is excluded via path conditions (denominator != 0)
- No rounding errors or precision limits
- All arithmetic is exact mathematical arithmetic

For IEEE 754 floating-point verification, Z3's Float16/32/64 theories
(FP theory) would be needed, which is significantly more complex and
not currently implemented. The SMT backend is suitable for verifying
mathematical properties but not for verifying IEEE 754 edge cases.
"""

import contextlib
from dataclasses import dataclass
from typing import Any

import z3  # type: ignore[import-untyped]

from omni_compiler.checker import SymbolTable
from omni_compiler.parser import (
    Assignment,
    BinaryExpr,
    BreakStmt,
    ContinueStmt,
    FieldAccess,
    ForBlock,
    FunctionCall,
    FunctionDef,
    GroupExpr,
    Identifier,
    IfBlock,
    ListLiteral,
    Literal,
    Program,
    ReturnStmt,
    ShowStmt,
    Slot,
    StructConstruct,
    UnaryExpr,
    WhileBlock,
)


class _UnsupportedError(Exception):
    """Raised when a construct cannot be modelled in SMT."""


_LOOP_BOUND = 3
"""Maximum number of iterations a loop is unrolled during verification.

When a loop's trip count can provably not exceed this bound (via ``require``
clauses or a literal iterable), the loop is fully verified.  When the trip
count may exceed the bound, the function is reported ``unsupported`` rather
than claiming a proof that was not made.
"""

_STRUCT_PRIMITIVE_SORTS = {
    'Number': z3.RealSort(),
    'Boolean': z3.BoolSort(),
    'Text': z3.StringSort(),
}


def _and_expr(exprs: list[Any]) -> Any:
    """Conjoin a list of Z3 terms; an empty list yields the literal True."""
    if not exprs:
        return z3.BoolVal(True)
    return z3.And(*exprs)


def _build_struct_sorts(
    types: list[Any],
) -> tuple[dict[str, Any], dict[str, list[str]], str | None]:
    """Build a Z3 ``Datatype`` per struct ``TypeDecl`` (dependency order).

    Returns ``(name -> DatatypeRef, name -> ordered field names, error)``.
    ``error`` is set when a struct type cannot be modelled (recursion), so
    callers can report ``unsupported`` precisely for functions that use it.
    """
    by_name = {t.name: t for t in types}
    order: list[str] = []
    visited: dict[str, int] = {}
    visiting = 1
    done = 2

    def visit(name: str) -> None:
        if visited.get(name) == done:
            return
        if visited.get(name) == visiting:
            raise _UnsupportedError(f"recursive struct type '{name}' is not supported")
        visited[name] = visiting
        for ftype in by_name[name].fields.values():
            if ftype in _STRUCT_PRIMITIVE_SORTS:
                continue
            if ftype not in by_name:
                raise _UnsupportedError(f"struct field type '{ftype}' is not supported")
            visit(ftype)
        visited[name] = done
        order.append(name)

    try:
        for name in by_name:
            visit(name)
    except _UnsupportedError as exc:
        return {}, {}, str(exc)

    datatypes: dict[str, Any] = {}
    field_order: dict[str, list[str]] = {}
    for name in order:
        decl = by_name[name]
        dtype = z3.Datatype(name)
        fields = [
            (
                field,
                _STRUCT_PRIMITIVE_SORTS[ftype]
                if ftype in _STRUCT_PRIMITIVE_SORTS
                else datatypes[ftype],
            )
            for field, ftype in decl.fields.items()
        ]
        dtype.declare(f'mk_{name.lower()}', *fields)
        datatypes[name] = dtype.create()
        field_order[name] = list(decl.fields.keys())
    return datatypes, field_order, None


@dataclass
class _PathState:
    env: dict[str, Any]
    conds: list[Any]
    disposition: str | None = None  # None | 'break' | 'continue'


@dataclass
class _ReturnPath:
    expr: Any
    conds: list[Any]
    env: dict[str, Any]


def _expr_to_string(expr: Any) -> str:  # noqa: PLR0911
    if isinstance(expr, Literal):
        if expr.value_type == 'Text':
            return f'"{expr.value}"'
        return str(expr.value)
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, FunctionCall):
        return f'{expr.name}({", ".join(_expr_to_string(a) for a in expr.args)})'
    if isinstance(expr, BinaryExpr):
        return f'{_expr_to_string(expr.left)} {expr.op} {_expr_to_string(expr.right)}'
    if isinstance(expr, GroupExpr):
        return f'({_expr_to_string(expr.expr)})'
    if isinstance(expr, UnaryExpr):
        if expr.op == 'not':
            return f'not {_expr_to_string(expr.operand)}'
        return f'-{_expr_to_string(expr.operand)}'
    if isinstance(expr, ListLiteral):
        return f'[{", ".join(_expr_to_string(i) for i in expr.items)}]'
    if isinstance(expr, StructConstruct):
        args = ', '.join(f'{k}={_expr_to_string(v)}' for k, v in expr.args.items())
        return f'{expr.name}({args})'
    if isinstance(expr, FieldAccess):
        return f'{_expr_to_string(expr.object)}.{expr.field}'
    return str(expr)


def _model_value_to_py(value: Any) -> int | float | bool | str:  # noqa: PLR0911
    if z3.is_true(value):
        return True
    if z3.is_false(value):
        return False
    if z3.is_int_value(value):
        return int(value.as_long())
    if z3.is_rational_value(value):
        numerator = int(value.numerator().as_long())
        denominator = int(value.denominator().as_long())
        if denominator == 1:
            return numerator
        return numerator / denominator
    if z3.is_string(value):
        s = str(value)
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':  # noqa: PLR2004
            return s[1:-1]
        return s
    return str(value)


def render_counterexample(model: Any, params: list[str]) -> dict[str, int | float | bool | str]:
    """Map each parameter name to its concrete Python value in `model`."""
    declarations = {decl.name(): decl for decl in model.decls()}
    out: dict[str, int | float | bool | str] = {}
    for name in params:
        decl = declarations.get(name)
        if decl is None:
            continue
        out[name] = _model_value_to_py(model.eval(decl(), model_completion=True))
    return out


class _FunctionVerifier:
    """Symbolically executes one function body and checks its contracts."""

    _ARITH: dict[str, Any] = {
        '+': lambda left, right: left + right,
        '-': lambda left, right: left - right,
        '*': lambda left, right: left * right,
        'is': lambda left, right: left == right,
        'is not': lambda left, right: left != right,
        'greater than': lambda left, right: left > right,
        'less than': lambda left, right: left < right,
        'greater or equal': lambda left, right: left >= right,
        'less or equal': lambda left, right: left <= right,
    }

    _STR_OPS: dict[str, Any] = {
        '+': z3.Concat,
        'is': lambda left, right: left == right,
        'is not': lambda left, right: left != right,
    }

    def __init__(
        self,
        fn: FunctionDef,
        functions: dict[str, FunctionDef],
        datatypes: dict[str, Any],
        struct_fields: dict[str, list[str]],
        struct_error: str | None,
    ) -> None:
        self.fn = fn
        self._functions = functions
        self._datatypes = datatypes
        self._struct_fields = struct_fields
        self._struct_error = struct_error
        self._inline_stack: set[str] = set()
        self._LOOP_BOUND = _LOOP_BOUND
        self.params: dict[str, Any] = {}
        for param in fn.params:
            self.params[param.name] = self._fresh_const(param.name, param.type)
        self.env: dict[str, Any] = dict(self.params)

    def _fresh_const(self, name: str, ptype: str) -> Any:
        """Create a fresh Z3 constant for an OmniScript value of ``ptype``."""
        if ptype == 'Number':
            return z3.Real(name)
        if ptype == 'Boolean':
            return z3.Bool(name)
        if ptype == 'Text':
            return z3.String(name)
        if ptype in self._datatypes:
            return z3.Const(name, self._datatypes[ptype])
        raise _UnsupportedError(f"parameter type '{ptype}' is not supported")

    def _translate_literal(self, expr: Literal) -> Any:
        if expr.value_type == 'Number':
            return z3.RealVal(expr.value)
        if expr.value_type == 'Boolean':
            return z3.BoolVal(bool(expr.value))
        if expr.value_type == 'Text':
            # String literals from the lexer include quotes (e.g., '"hello"')
            # Strip the surrounding quotes for Z3
            val = str(expr.value)
            if len(val) >= 2 and (  # noqa: PLR2004
                (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")
            ):
                val = val[1:-1]
            return z3.StringVal(val)
        raise _UnsupportedError(f"literal of type '{expr.value_type}' is not supported")

    def _translate_identifier(self, expr: Identifier, env: dict[str, Any]) -> Any:
        if expr.name in env:
            return env[expr.name]
        raise _UnsupportedError(f"identifier '{expr.name}' is not bound to a modelled value")

    def _translate_division(self, left: Any, right: Any, guards: list[Any]) -> Any:
        if z3.is_rational_value(right) and int(right.numerator().as_long()) == 0:
            raise _UnsupportedError('division by a literal zero is not defined')
        guards.append(right != 0)
        return left / right

    def _apply_arith(self, op: str, left: Any, right: Any) -> Any:
        apply = self._ARITH.get(op)
        if apply is None:
            raise _UnsupportedError(f"operator '{op}' is not supported")
        return apply(left, right)

    def _translate_expr(self, expr: Any, env: dict[str, Any], guards: list[Any]) -> Any:  # noqa: PLR0911, PLR0912
        if isinstance(expr, Literal):
            return self._translate_literal(expr)
        if isinstance(expr, Identifier):
            return self._translate_identifier(expr, env)
        if isinstance(expr, BinaryExpr):
            return self._translate_binary(expr, env, guards)
        if isinstance(expr, FunctionCall):
            return self._translate_function_call(expr, env, guards)
        if isinstance(expr, ListLiteral):
            raise _UnsupportedError('list literals are not yet supported')
        if isinstance(expr, FieldAccess):
            obj = self._translate_expr(expr.object, env, guards)
            sort_name = str(obj.sort())
            dtype = self._datatypes.get(sort_name)
            if dtype is None:
                raise _UnsupportedError(f'field access on a value of non-struct type {sort_name}')
            accessor = getattr(dtype, expr.field, None)
            if accessor is None:
                raise _UnsupportedError(f"struct '{sort_name}' has no field '{expr.field}'")
            return accessor(obj)
        if isinstance(expr, StructConstruct):
            dtype = self._datatypes.get(expr.name)
            if dtype is None:
                raise _UnsupportedError(
                    self._struct_error or f"struct type '{expr.name}' is not supported"
                )
            fields = self._struct_fields.get(expr.name)
            if fields is None:
                raise _UnsupportedError(f"struct type '{expr.name}' has no declared fields")
            constructor = getattr(dtype, f'mk_{expr.name.lower()}')
            values = [self._translate_expr(expr.args[field], env, guards) for field in fields]
            return constructor(*values)
        if isinstance(expr, Slot):
            raise _UnsupportedError('slot expressions are not yet supported')
        if isinstance(expr, GroupExpr):
            return self._translate_expr(expr.expr, env, guards)
        if isinstance(expr, UnaryExpr):
            operand = self._translate_expr(expr.operand, env, guards)
            if expr.op == 'not':
                return z3.Not(operand)
            if expr.op == 'neg':
                return -operand
            raise _UnsupportedError(f"unary operator '{expr.op}' is not supported")
        raise _UnsupportedError(f'unsupported expression node {type(expr).__name__}')

    def _translate_function_call(  # noqa: PLR0911, PLR0912
        self, expr: FunctionCall, env: dict[str, Any], guards: list[Any]
    ) -> Any:
        """Translate string operations, user-defined functions, and other calls."""
        args = [self._translate_expr(arg, env, guards) for arg in expr.args]
        if expr.name == 'length':
            if len(args) != 1:
                raise _UnsupportedError('length() requires exactly 1 argument')
            return z3.Length(args[0])
        if expr.name == 'contains':
            if len(args) != 2:  # noqa: PLR2004
                raise _UnsupportedError('contains() requires exactly 2 arguments')
            return z3.Contains(args[0], args[1])
        if expr.name == 'starts_with':
            if len(args) != 2:  # noqa: PLR2004
                raise _UnsupportedError('starts_with() requires exactly 2 arguments')
            return z3.PrefixOf(args[1], args[0])
        if expr.name == 'ends_with':
            if len(args) != 2:  # noqa: PLR2004
                raise _UnsupportedError('ends_with() requires exactly 2 arguments')
            return z3.SuffixOf(args[1], args[0])
        if expr.name == 'substring':
            if len(args) != 3:  # noqa: PLR2004
                raise _UnsupportedError(
                    'substring() requires exactly 3 arguments (text, start, end)'
                )
            # Z3 SubSeq requires Int indices. Convert from Real (Number type) if needed.
            # length() returns Int, so check if already Int
            start = args[1]
            end = args[2]
            if z3.is_real(start):
                start = z3.ToInt(start)
            if z3.is_real(end):
                end = z3.ToInt(end)
            length_int = end - start
            return z3.SubSeq(args[0], start, length_int)
        if expr.name == 'range' and len(args) == 1:
            return args[0]
        if expr.name == 'regex_match':
            raise _UnsupportedError('regex_match() is not supported in SMT verification')
        if expr.name in self._functions:
            return self._inline_call(self._functions[expr.name], args, guards)
        raise _UnsupportedError(f"function call '{expr.name}' is not yet supported")

    def _inline_call(self, fn: FunctionDef, arg_values: list[Any], guards: list[Any]) -> Any:
        """Inline a user-defined function by symbolically executing its body.

        The callee's ``require`` clauses are assumed (they are proven as part
        of the callee's own contract verification).  Each argument is bound to
        a fresh constant, so callee parameters can never capture the caller's
        names.  A fresh result constant is constrained to equal the callee's
        return value on whichever return path is taken.
        """
        if fn.name in self._inline_stack:
            raise _UnsupportedError(f"recursive call to '{fn.name}' is not supported in contracts")
        if len(arg_values) != len(fn.params):
            raise _UnsupportedError(f"call to '{fn.name}' has the wrong number of arguments")
        callee_env: dict[str, Any] = {}
        for param, value in zip(fn.params, arg_values, strict=True):
            fresh = self._fresh_const(f'{fn.name}_{param.name}', param.type)
            callee_env[param.name] = fresh
            guards.append(fresh == value)
        for req in fn.requires:
            req_guards: list[Any] = []
            guards.append(self._translate_expr(req, callee_env, req_guards))
            guards.extend(req_guards)
        self._inline_stack.add(fn.name)
        try:
            returns, fallthroughs = self._exec(fn.body, callee_env, [])
        finally:
            self._inline_stack.discard(fn.name)
        if fallthroughs or not returns:
            raise _UnsupportedError(
                f"function '{fn.name}' cannot be inlined (no single return value)"
            )
        result = self._fresh_const(f'{fn.name}_result', fn.return_type)
        guards.append(z3.Or(*[_and_expr(ret.conds) for ret in returns]))
        for ret in returns:
            guards.append(z3.Implies(_and_expr(ret.conds), result == ret.expr))
        return result

    def _translate_binary(self, expr: BinaryExpr, env: dict[str, Any], guards: list[Any]) -> Any:
        left = self._translate_expr(expr.left, env, guards)
        right = self._translate_expr(expr.right, env, guards)
        if expr.op == '/':
            return self._translate_division(left, right, guards)
        if expr.op == 'and':
            return z3.And(left, right)
        if expr.op == 'or':
            return z3.Or(left, right)
        if z3.is_string(left) or z3.is_string(right):
            if expr.op in self._STR_OPS:
                return self._STR_OPS[expr.op](left, right)
            raise _UnsupportedError(f"string operator '{expr.op}' is not supported")
        return self._apply_arith(expr.op, left, right)

    def _exec(
        self, stmts: list[Any], env: dict[str, Any], conds: list[Any]
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        states: list[_PathState] = [_PathState(env=env, conds=conds)]
        returns: list[_ReturnPath] = []
        for stmt in stmts:
            next_states: list[_PathState] = []
            for state in states:
                stmt_returns, stmt_states = self._exec_one(stmt, state.env, state.conds)
                returns.extend(stmt_returns)
                next_states.extend(stmt_states)
            states = next_states
        return returns, states

    def _exec_one(  # noqa: PLR0911
        self, stmt: Any, env: dict[str, Any], conds: list[Any]
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        if isinstance(stmt, Assignment):
            guards: list[Any] = []
            value = self._translate_expr(stmt.expr, env, guards)
            new_env = dict(env)
            new_env[stmt.name] = value
            return [], [_PathState(env=new_env, conds=[*conds, *guards])]
        if isinstance(stmt, ReturnStmt):
            guards = []
            value = self._translate_expr(stmt.expr, env, guards)
            return [_ReturnPath(expr=value, conds=[*conds, *guards], env=env)], []
        if isinstance(stmt, ShowStmt):
            self._translate_expr(stmt.expr, env, [])
            return [], [_PathState(env=env, conds=conds)]
        if isinstance(stmt, IfBlock):
            guards = []
            condition = self._translate_expr(stmt.condition, env, guards)
            base_conds = [*conds, *guards]
            then_returns, then_states = self._exec(stmt.body, env, [*base_conds, condition])
            else_returns, else_states = self._exec(
                stmt.else_body, env, [*base_conds, z3.Not(condition)]
            )
            return then_returns + else_returns, then_states + else_states
        if isinstance(stmt, ForBlock):
            return self._exec_for(stmt, env, conds)
        if isinstance(stmt, WhileBlock):
            return self._exec_while(stmt, env, conds)
        if isinstance(stmt, FunctionCall):
            guards = []
            self._translate_function_call(stmt, env, guards)
            return [], [_PathState(env=env, conds=[*conds, *guards])]
        if isinstance(stmt, BreakStmt):
            return [], [_PathState(env=env, conds=conds, disposition='break')]
        if isinstance(stmt, ContinueStmt):
            return [], [_PathState(env=env, conds=conds, disposition='continue')]
        return [], [_PathState(env=env, conds=conds)]

    def _exec_for(
        self, stmt: ForBlock, env: dict[str, Any], conds: list[Any]
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        """Execute a ``for`` block by unrolling its iterations.

        Supported iterables: ``range(n)`` / a bare ``Number`` (values ``0..n-1``)
        and list literals.  ``break``/``continue`` inside the body are handled.
        """
        iterable = stmt.iterable
        if (
            isinstance(iterable, FunctionCall)
            and iterable.name == 'range'
            and len(iterable.args) == 1
        ):
            guards: list[Any] = []
            n = self._translate_expr(iterable.args[0], env, guards)
            return self._bounded_range(n, stmt.body, env, [*conds, *guards], stmt.variable)
        if isinstance(iterable, ListLiteral):
            return self._bounded_list(iterable.items, stmt.body, env, conds, stmt.variable)
        if isinstance(iterable, Identifier):
            value = self._translate_identifier(iterable, env)
            if z3.is_real(value) or z3.is_int(value):
                return self._bounded_range(value, stmt.body, env, conds, stmt.variable)
            raise _UnsupportedError('loop iterable must be range(n), a Number, or a list literal')
        raise _UnsupportedError('loop iterable must be range(n), a Number, or a list literal')

    def _exec_while(
        self, stmt: WhileBlock, env: dict[str, Any], conds: list[Any]
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        """Execute a ``while`` block by bounded unrolling.

        When the condition can still hold after ``_LOOP_BOUND`` iterations the
        verification is reported ``unsupported`` rather than unsoundly bounded.
        """
        returns: list[_ReturnPath] = []
        exited: list[_PathState] = []
        active = [_PathState(env=env, conds=conds)]
        for _ in range(self._LOOP_BOUND):
            entering: list[_PathState] = []
            for state in active:
                guards: list[Any] = []
                condition = self._translate_expr(stmt.condition, state.env, guards)
                entering.append(_PathState(env=state.env, conds=[*state.conds, *guards, condition]))
                exited.append(
                    _PathState(env=state.env, conds=[*state.conds, *guards, z3.Not(condition)])
                )
            active = self._step_loop_body(stmt.body, entering, returns)
            if not active:
                break
        if active:
            for state in active:
                guards = []
                condition = self._translate_expr(stmt.condition, state.env, guards)
                solver = z3.Solver()
                solver.add(*self._pre, *state.conds, *guards, condition)
                if solver.check() == z3.sat:
                    raise _UnsupportedError('loop may not terminate within the unrolling bound')
            for state in active:
                guards = []
                condition = self._translate_expr(stmt.condition, state.env, guards)
                exited.append(
                    _PathState(env=state.env, conds=[*state.conds, *guards, z3.Not(condition)])
                )
        return returns, exited

    def _step_loop_body(
        self, body: list[Any], entering: list[_PathState], returns: list[_ReturnPath]
    ) -> list[_PathState]:
        """Run one loop-body pass; ``break`` states exit, the rest iterate."""
        next_active: list[_PathState] = []
        for state in entering:
            body_returns, body_states = self._exec(body, state.env, state.conds)
            returns.extend(body_returns)
            for body_state in body_states:
                if body_state.disposition == 'break':
                    continue
                next_active.append(_PathState(env=body_state.env, conds=body_state.conds))
        return next_active

    def _bounded_range(
        self, n: Any, body: list[Any], env: dict[str, Any], conds: list[Any], var: str
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        """Unroll ``for var in range(n)``; ``var`` takes values ``0..n-1``."""
        returns: list[_ReturnPath] = []
        exited: list[_PathState] = []
        active = [_PathState(env=env, conds=conds)]
        for k in range(self._LOOP_BOUND):
            entering: list[_PathState] = []
            for state in active:
                entering.append(_PathState(env=state.env, conds=[*state.conds, z3.RealVal(k) < n]))
                exited.append(_PathState(env=state.env, conds=[*state.conds, z3.RealVal(k) >= n]))
            stepped: list[_PathState] = []
            for state in entering:
                body_env = dict(state.env)
                body_env[var] = z3.RealVal(k)
                body_returns, body_states = self._exec(body, body_env, state.conds)
                returns.extend(body_returns)
                for body_state in body_states:
                    if body_state.disposition == 'break':
                        exited.append(_PathState(env=body_state.env, conds=body_state.conds))
                    else:
                        stepped.append(_PathState(env=body_state.env, conds=body_state.conds))
            active = stepped
            if not active:
                break
        if active:
            for state in active:
                solver = z3.Solver()
                solver.add(*self._pre, *state.conds, z3.RealVal(self._LOOP_BOUND) < n)
                if solver.check() == z3.sat:
                    raise _UnsupportedError(
                        'loop trip count may exceed the unrolling bound; add a require bounding it'
                    )
            for state in active:
                exited.append(
                    _PathState(
                        env=state.env,
                        conds=[*state.conds, z3.RealVal(self._LOOP_BOUND) >= n],
                    )
                )
        return returns, exited

    def _bounded_list(
        self, items: list[Any], body: list[Any], env: dict[str, Any], conds: list[Any], var: str
    ) -> tuple[list[_ReturnPath], list[_PathState]]:
        """Unroll ``for var in [items...]``; each literal element is visited once."""
        returns: list[_ReturnPath] = []
        exited: list[_PathState] = []
        active = [_PathState(env=env, conds=conds)]
        for item in items:
            guards: list[Any] = []
            value = self._translate_expr(item, env, guards)
            stepped: list[_PathState] = []
            for state in active:
                body_env = dict(state.env)
                body_env[var] = value
                body_returns, body_states = self._exec(body, body_env, [*state.conds, *guards])
                returns.extend(body_returns)
                for body_state in body_states:
                    if body_state.disposition == 'break':
                        exited.append(_PathState(env=body_state.env, conds=body_state.conds))
                    else:
                        stepped.append(_PathState(env=body_state.env, conds=body_state.conds))
            active = stepped
            if not active:
                break
        exited.extend(active)
        return returns, exited

    def _check_path(
        self, pre: list[Any], conds: list[Any], post: list[Any], ret_expr: Any
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        solver = z3.Solver()
        solver.add(*pre, *conds)
        solver.add(z3.Not(_and_expr(post)))
        check = solver.check()
        if check == z3.sat:
            model = solver.model()
            counterexample = render_counterexample(model, [param.name for param in self.fn.params])
            with contextlib.suppress(Exception):
                counterexample['result'] = _model_value_to_py(
                    model.eval(ret_expr, model_completion=True)
                )
            return 'failed', counterexample, 'the ensure clause does not hold for these inputs'
        if check == z3.unknown:
            return 'unsupported', None, 'Z3 could not decide the verification query (unknown)'
        return 'verified', None, None

    def _verify(self, base: dict[str, Any]) -> dict[str, Any]:
        pre: list[Any] = []
        for req in self.fn.requires:
            guards: list[Any] = []
            pre.append(self._translate_expr(req, self.env, guards))
            pre.extend(guards)
        self._pre = pre
        returns, fallthroughs = self._exec(self.fn.body, self.env, [])
        if fallthroughs:
            for state in fallthroughs:
                if state.disposition in ('break', 'continue'):
                    return {
                        **base,
                        'status': 'unsupported',
                        'reason': "'break'/'continue' escaped its enclosing loop",
                    }
            return {
                **base,
                'status': 'unsupported',
                'reason': 'a control path falls through without an explicit return',
            }
        if not returns:
            return {
                **base,
                'status': 'unsupported',
                'reason': 'function has no explicit return statement',
            }
        for ret in returns:
            post_env = dict(ret.env)
            post_env['result'] = ret.expr
            post: list[Any] = []
            assumed: list[Any] = []
            for ens in self.fn.ensures:
                guards = []
                post.append(self._translate_expr(ens, post_env, guards))
                assumed.extend(guards)
            status, counterexample, reason = self._check_path(
                [*pre, *assumed], ret.conds, post, ret.expr
            )
            if status == 'failed':
                return {
                    **base,
                    'status': 'failed',
                    'counterexample': counterexample,
                    'reason': reason,
                }
            if status == 'unsupported':
                return {
                    **base,
                    'status': 'unsupported',
                    'reason': reason,
                }
        return {**base, 'status': 'verified'}


def _verify_function(
    fn: FunctionDef,
    functions: dict[str, FunctionDef],
    datatypes: dict[str, Any],
    struct_fields: dict[str, list[str]],
    struct_error: str | None,
) -> dict[str, Any]:
    requires = ' and '.join(_expr_to_string(req) for req in fn.requires)
    ensures = ' and '.join(_expr_to_string(ens) for ens in fn.ensures)
    base: dict[str, Any] = {
        'schema': 'omni.verify',
        'version': '1.0',
        'function': fn.name,
        'require': requires or None,
        'ensure': ensures or None,
        'counterexample': None,
        'reason': None,
    }
    if not fn.ensures:
        return {**base, 'status': 'no-contracts'}
    try:
        verifier = _FunctionVerifier(fn, functions, datatypes, struct_fields, struct_error)
        return verifier._verify(base)
    except _UnsupportedError as exc:
        return {**base, 'status': 'unsupported', 'reason': str(exc)}
    except z3.Z3Exception as exc:
        return {**base, 'status': 'unsupported', 'reason': f'Z3 error: {exc}'}


def verify_contracts(
    prog: Program, symbol_table: SymbolTable | None = None
) -> list[dict[str, Any]]:
    """Verify the require/ensure contracts of every function in ``prog``.

    Returns one verification result dict per function (see the module
    docstring for the schema).  ``symbol_table`` is accepted for API
    symmetry with ``mir.to_mir``; contract well-typedness is already
    enforced by the semantic checker, so it is not consulted here.
    """
    del symbol_table
    functions = {fn.name: fn for fn in prog.functions}
    datatypes, struct_fields, struct_error = _build_struct_sorts(prog.types)
    results: list[dict[str, Any]] = []
    for fn in prog.functions:
        results.append(_verify_function(fn, functions, datatypes, struct_fields, struct_error))
    return results

```

## File: `omni_compiler\wasm_emitter.py`
```python
# ruff: noqa: Q000 - single quotes are the repo style; lint Q000 defaults to double.

"""WASM Emitter Module (v3.5).

Wraps the C emitter output for WebAssembly targets:
- browser: a self-contained HTML page with a canvas, the embedded C
  source, and JS glue that instantiates the module and mirrors printf.
- wasi: the C source plus wasm32-wasi build/run command comments for
  server/edge runtimes such as wasmtime.

SQLite persistence in browser uses sql.js (SQLite compiled to WASM).

Floating-point conformance: WASM FP is IEEE 754 compliant.
The C emitter provides the conformance helpers which are used by WASM.
"""

from typing import Any

_WASM_BROWSER_BUILD = (
    'clang --target=wasm32 --no-standard-libraries '
    '-Wl,--no-entry -Wl,--export-all -o app.wasm app.c'
)
_WASM_WASI_BUILD = 'clang --target=wasm32-wasi -o app.wasm app.c'


def wasm_build_command(mode: str = 'browser') -> str:
    """Return the clang invocation that compiles app.c into app.wasm."""
    if mode == 'wasi':
        return _WASM_WASI_BUILD
    return _WASM_BROWSER_BUILD


def _c_source(mir: Any) -> str:
    """Emit C via the C emitter, adapting defensively if the module changed."""
    try:
        from omni_compiler import c_emitter  # noqa: PLC0415 - lazy import re-reads peer module

        return c_emitter.emit_c(mir)
    except Exception:
        return '// C emitter unavailable; re-read c_emitter.py and adapt.'


def _glue_imports() -> list[str]:
    """JS import shim that maps printf to console.log and allocates memory."""
    return [
        '// WASM import shim (app.js): maps printf to console.log.',
        'const memory = new WebAssembly.Memory({ initial: 256 });',
        'function _mirror(text) {',
        "  const out = document.getElementById('output');",
        '  if (out) { out.textContent += String(text) + String.fromCharCode(10); }',
        '}',
        'function wasmPrintf(fmt) {',
        '  const args = Array.prototype.slice.call(arguments, 1);',
        '  let i = 0;',
        '  const msg = String(fmt).replace(/%[a-zA-Z]/g, function () {',
        "    return i < args.length ? String(args[i++]) : '';",
        '  });',
        "  console.log('[wasm] ' + msg);",
        '  _mirror(msg);',
        '  return msg.length;',
        '}',
        'const imports = {',
        '  env: {',
        '    memory: memory,',
        '    printf: wasmPrintf,',
        '    emscripten_notify_memory_growth: function (index) {',
        "      console.log('[wasm] memory growth notification:', index);",
        '    },',
        '  },',
        '};',
        '',
    ]


def _default_arg(omni_type: str) -> str:
    """Return a neutral default argument value for an OmniScript type."""
    return {
        'Number': '0',
        'Text': '0',
        'Boolean': '0',
        'List': '0',
        'None': '0',
    }.get(omni_type, '0')


def _export_calls(mir: Any) -> list[str]:
    """JS wrappers that call each exported wasm function once."""
    lines = ['// Call every exported WASM function once for a smoke check.']
    lines.append('function callExports(instance) {')
    for fn in mir.functions.values():
        args = ', '.join(_default_arg(p.type) for p in fn.params)
        if not args:
            args = '0'
        lines.append(f"  const {fn.name} = instance.exports['{fn.name}'];")
        lines.append(f"  if (typeof {fn.name} === 'function') {{")
        lines.append(f"    console.log('calling wasm export {fn.name}()');")
        lines.append(f'    {fn.name}({args});')
        lines.append('  }')
    lines.append('}')
    lines.append('')
    return lines


def _load_glue() -> list[str]:
    """JS loader that instantiates the wasm module via fetch."""
    return [
        'async function loadApp() {',
        "  // glue pattern: WebAssembly.instantiateStreaming(fetch('app.wasm'), {})",
        '  try {',
        '    const { instance } = await '
        "WebAssembly.instantiateStreaming(fetch('app.wasm'), imports);",
        "    console.log('wasm module instantiated');",
        '    callExports(instance);',
        '  } catch (err) {',
        "    console.warn('instantiateStreaming failed, falling back:', err);",
        "    const bytes = await (await fetch('app.wasm')).arrayBuffer();",
        '    const { instance } = await WebAssembly.instantiate(bytes, imports);',
        '    callExports(instance);',
        '  }',
        '}',
        'loadApp();',
        '',
    ]


def _scene_js(mir: Any) -> list[str]:
    """Reuse the JS emitter's Three.js scene snippet when available."""
    try:
        from omni_compiler import emitter  # noqa: PLC0415 - lazy import re-reads peer-edited module

        scene_fn = getattr(emitter, '_js_scene', None)
        if scene_fn is None:
            return []
        return list(scene_fn(mir))
    except Exception:
        return []


def _sqlite_js_glue() -> list[str]:
    """JS glue for sql.js (SQLite in WASM) persistence."""
    return [
        '// sql.js (SQLite WASM) integration for db persistence',
        'let _sqlJsDb = null;',
        'let _sqlJsFile = null;',
        '',
        'async function initSqlJsDb(path) {',
        '  const SQL = await initSqlJs({ locateFile: (file) => `https://sql.js.org/dist/${file}` });',  # noqa: E501
        '  if (!path || path === ":memory:") {',
        '    _sqlJsDb = new SQL.Database();',
        '    _sqlJsFile = null;',
        '  } else {',
        '    try {',
        '      const response = await fetch(path);',
        '      if (response.ok) {',
        '        const arrayBuffer = await response.arrayBuffer();',
        '        _sqlJsFile = new Uint8Array(arrayBuffer);',
        '        _sqlJsDb = new SQL.Database(_sqlJsFile);',
        '      } else {',
        '        _sqlJsDb = new SQL.Database();',
        '        _sqlJsFile = null;',
        '      }',
        '    } catch {',
        '      _sqlJsDb = new SQL.Database();',
        '      _sqlJsFile = null;',
        '    }',
        '  }',
        '  _sqlJsDb.run("PRAGMA foreign_keys = ON");',
        '}',
        '',
        'function sqlJsQuery(sql, params) {',
        '  if (!_sqlJsDb) throw new Error("No database open. Call db_open() first.");',
        '  const stmt = _sqlJsDb.prepare(sql);',
        '  const results = [];',
        '  if (params && params.length) {',
        '    stmt.bind(params);',
        '  }',
        '  while (stmt.step()) {',
        '    results.push(stmt.getAsObject());',
        '  }',
        '  stmt.free();',
        '  return results;',
        '}',
        '',
        'function sqlJsExec(sql, params) {',
        '  if (!_sqlJsDb) throw new Error("No database open. Call db_open() first.");',
        '  const stmt = _sqlJsDb.prepare(sql);',
        '  if (params && params.length) {',
        '    stmt.bind(params);',
        '  }',
        '  stmt.step();',
        '  const changes = _sqlJsDb.getRowsModified();',
        '  stmt.free();',
        '  if (_sqlJsFile !== null) {',
        '    _sqlJsFile = _sqlJsDb.export();',
        '  }',
        '  return changes;',
        '}',
        '',
        'function sqlJsClose() {',
        '  if (_sqlJsDb) {',
        '    if (_sqlJsFile !== null) {',
        '      _sqlJsFile = _sqlJsDb.export();',
        '    }',
        '    _sqlJsDb.close();',
        '    _sqlJsDb = null;',
        '  }',
        '}',
        '',
        'function sqlJsExport() {',
        '  if (!_sqlJsDb || _sqlJsFile === null) return null;',
        '  return _sqlJsFile;',
        '}',
        '',
    ]


def emit_wasm_browser(mir: Any) -> str:
    """Emit a self-contained HTML page that loads the wasm build with sql.js."""
    c_code = _c_source(mir)
    build = wasm_build_command('browser')
    scene_js = _scene_js(mir)

    js = [
        '// Generated by OmniScript WASM Emitter (v3.4) — browser mode',
        f'// build: {build}',
        '// Compile with the build comment, then serve this page beside app.wasm.',
        '// Includes sql.js for SQLite persistence.',
        '',
    ]
    js.extend(_glue_imports())
    js.extend(_sqlite_js_glue())
    js.extend(_export_calls(mir))
    js.extend(_load_glue())
    js.extend(scene_js)

    body = '\n'.join(js)
    return '\n'.join(
        [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <meta charset="utf-8"><title>OmniScript WASM App</title>',
            '  <script src="https://sql.js.org/dist/sql-wasm.js"></script>',
            '</head>',
            '<body>',
            '  <canvas id="wasm-canvas" width="512" height="512"></canvas>',
            '  <div id="output"></div>',
            '  <script type="text/emscripten">',
            '  // C source emitted by the OmniScript C Emitter (compile with the build comment).',
            c_code,
            '  </script>',
            '  <script>',
            body,
            '  </script>',
            '</body>',
            '</html>',
        ]
    )


def emit_wasm_wasi(mir: Any) -> str:
    """Emit C source targeting wasm32-wasi for server/edge runtimes."""
    c_code = _c_source(mir)
    header = [
        '// Generated by OmniScript WASM Emitter (v3.3) — wasi mode',
        f'// build: {wasm_build_command("wasi")}',
        '// run: wasmtime app.wasm',
        '',
    ]
    return '\n'.join(header + [c_code])


def emit_wasm(mir: Any, mode: str = 'browser') -> str:
    """Emit a WASM target for the given MIR (browser HTML or wasi C source)."""
    if mode == 'wasi':
        return emit_wasm_wasi(mir)
    return emit_wasm_browser(mir)

```

