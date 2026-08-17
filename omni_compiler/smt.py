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
  (loops, function calls, structs, lists, text, ...) or Z3 could not
  decide the query; `reason` explains why.

Design notes:

* Number values are translated to Z3 Reals.  Reals are a strict superset of
  the integers used by integer literals, so the choice is sound and
  integer-looking counterexample values are rendered as Python ints (see
  `render_counterexample`).
* Division by a symbolic denominator emits `denominator != 0` as a path
  condition, so a counterexample can never rely on an ill-defined division.
* `result` inside an `ensure` is substituted with the return expression of
  the path being verified.
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


class _UnsupportedError(Exception):
    """Raised when a construct cannot be modelled in SMT."""


@dataclass
class _PathState:
    env: dict[str, Any]
    conds: list[Any]


@dataclass
class _ReturnPath:
    expr: Any
    conds: list[Any]
    env: dict[str, Any]


def _expr_to_string(expr: Any) -> str:
    if isinstance(expr, Literal):
        return str(expr.value)
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, FunctionCall):
        return f'{expr.name}({", ".join(_expr_to_string(a) for a in expr.args)})'
    if isinstance(expr, BinaryExpr):
        return f'{_expr_to_string(expr.left)} {expr.op} {_expr_to_string(expr.right)}'
    if isinstance(expr, ListLiteral):
        return f'[{", ".join(_expr_to_string(i) for i in expr.items)}]'
    return str(expr)


def _model_value_to_py(value: Any) -> int | float | bool | str:
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

    def __init__(self, fn: FunctionDef) -> None:
        self.fn = fn
        self.params: dict[str, Any] = {}
        for param in fn.params:
            if param.type == 'Number':
                self.params[param.name] = z3.Real(param.name)
            elif param.type == 'Boolean':
                self.params[param.name] = z3.Bool(param.name)
            else:
                raise _UnsupportedError(f"parameter type '{param.type}' is not supported")
        self.env: dict[str, Any] = dict(self.params)

    def _translate_literal(self, expr: Literal) -> Any:
        if expr.value_type == 'Number':
            return z3.RealVal(expr.value)
        if expr.value_type == 'Boolean':
            return z3.BoolVal(bool(expr.value))
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

    def _translate_expr(self, expr: Any, env: dict[str, Any], guards: list[Any]) -> Any:
        if isinstance(expr, Literal):
            return self._translate_literal(expr)
        if isinstance(expr, Identifier):
            return self._translate_identifier(expr, env)
        if isinstance(expr, BinaryExpr):
            return self._translate_binary(expr, env, guards)
        if isinstance(expr, FunctionCall):
            raise _UnsupportedError(f"function call '{expr.name}' is not yet supported")
        if isinstance(expr, ListLiteral):
            raise _UnsupportedError('list literals are not yet supported')
        if isinstance(expr, FieldAccess):
            raise _UnsupportedError('struct field access is not yet supported')
        if isinstance(expr, StructConstruct):
            raise _UnsupportedError('struct construction is not yet supported')
        if isinstance(expr, Slot):
            raise _UnsupportedError('slot expressions are not yet supported')
        raise _UnsupportedError(f'unsupported expression node {type(expr).__name__}')

    def _translate_binary(self, expr: BinaryExpr, env: dict[str, Any], guards: list[Any]) -> Any:
        left = self._translate_expr(expr.left, env, guards)
        right = self._translate_expr(expr.right, env, guards)
        if expr.op == '/':
            return self._translate_division(left, right, guards)
        if expr.op == 'and':
            return z3.And(left, right)
        if expr.op == 'or':
            return z3.Or(left, right)
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

    def _exec_one(
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
            raise _UnsupportedError('loops (for blocks) are not yet supported')
        if isinstance(stmt, FunctionCall):
            raise _UnsupportedError(f"function call '{stmt.name}' is not yet supported")
        if isinstance(stmt, BreakStmt):
            raise _UnsupportedError("'break' is not yet supported")
        if isinstance(stmt, ContinueStmt):
            raise _UnsupportedError("'continue' is not yet supported")
        return [], [_PathState(env=env, conds=conds)]

    def _check_path(
        self, pre: list[Any], conds: list[Any], post: list[Any], ret_expr: Any
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        solver = z3.Solver()
        solver.add(*pre, *conds)
        solver.add(z3.Not(z3.And(*post)))
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
        returns, fallthroughs = self._exec(self.fn.body, self.env, [])
        if fallthroughs:
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
            for ens in self.fn.ensures:
                guards = []
                post.append(self._translate_expr(ens, post_env, guards))
                post.extend(guards)
            status, counterexample, reason = self._check_path(pre, ret.conds, post, ret.expr)
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


def _verify_function(fn: FunctionDef) -> dict[str, Any]:
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
        verifier = _FunctionVerifier(fn)
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
    results: list[dict[str, Any]] = []
    for fn in prog.functions:
        results.append(_verify_function(fn))
    return results
