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
