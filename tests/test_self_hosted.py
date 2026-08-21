"""v5.1: Self-hosting compiler — a compiler written in OmniScript.

The self-hosted compiler lives in ``self_hosted/compiler.omni``. It is a
structured-AST code generator written in OmniScript: it consumes a List of
``Stmt``/``Expr`` records and emits ES6 JavaScript text (functions, entry
statements, renderUI). Because the OmniScript core has no string-processing
builtins beyond ``join``, the front-end's structured output is the boundary —
this is the emitter half of the compiler, written in the language itself.

Bootstrap proof (compiler compiles itself):
  1. ``compiler.omni`` is valid OmniScript and compiles through the reference
     pipeline (tokenize -> parse -> analyze -> to_mir -> emit_js).
  2. The emitted JS, run in Node, exposes ``compile_program``.
  3. ``compiler.omni`` embeds a structured description of its own ``emit_expr``
     function and compiles it at startup (``compiled_self``) — the compiler
     compiles (a description of) itself into working JS.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse

SELF_HOSTED = Path('self_hosted/compiler.omni')

HARNESS = """
global.document = {
  getElementById: function () { return { innerHTML: "", addEventListener: function () {} }; },
  querySelectorAll: function () { return []; },
};
"""


def _node_available() -> bool:
    return shutil.which('node') is not None


needs_node = pytest.mark.skipif(not _node_available(), reason='node not installed')


def _emit_self_hosted() -> str:
    code = SELF_HOSTED.read_text(encoding='utf-8')
    ast = parse(tokenize(code))
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def _script_of(html: str) -> str:
    match = re.search(r'<script>(.*)</script>', html, re.DOTALL)
    assert match is not None, 'emitted HTML contains no <script> block'
    return match.group(1)


def _run_node(source: str) -> str:
    result = subprocess.run(
        ['node', '-e', source],
        capture_output=True,
        text=True,
        cwd='.',
        check=False,
    )
    assert result.returncode == 0, f'node failed:\n{result.stderr}\n{result.stdout}'
    return result.stdout


class TestSelfHostedSource:
    """The self-hosted compiler is valid OmniScript."""

    def test_compiler_omni_is_valid_omnscript(self) -> None:
        js = _emit_self_hosted()
        assert isinstance(js, str)
        assert len(js) > 0

    def test_compiler_omni_emits_its_own_functions(self) -> None:
        js = _emit_self_hosted()
        for fn in ['compile_program', 'emit_fn', 'emit_stmt', 'emit_block', 'emit_expr']:
            assert f'function {fn}' in js, f'self-hosted compiler missing function {fn}'

    def test_compiler_omni_declares_pure(self) -> None:
        code = SELF_HOSTED.read_text(encoding='utf-8')
        ast = parse(tokenize(code))
        for fn in ast.functions:
            assert fn.effects.get('pure') is True, f'{fn.name} must be declared pure'


class TestBootstrap:
    """The compiler compiles itself: it embeds its own emit_expr as data."""

    @needs_node
    def test_compiler_compiles_itself_in_node(self) -> None:
        node_src = HARNESS + _script_of(_emit_self_hosted()) + '\nconsole.log(compiled_self);'
        out = _run_node(node_src)
        assert 'function emit_expr' in out, f'self-compiled output missing emit_expr:\n{out}'
        assert "e.kind === 'number'" in out
        assert 'return e.value;' in out

    @needs_node
    def test_self_compiled_output_is_syntax_valid_js(self) -> None:
        node_src = HARNESS + _script_of(_emit_self_hosted()) + '\nconsole.log(compiled_self);'
        out = _run_node(node_src)
        result = subprocess.run(
            ['node', '--check', '-'],
            input=out,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f'self-compiled output is not valid JS:\n{result.stderr}'


class TestCompileProgram:
    """compile_program emits valid JS for a structured program."""

    @needs_node
    def test_emits_function_and_statements(self) -> None:
        node_src = (
            HARNESS
            + _script_of(_emit_self_hosted())
            + """
const prog = [
  { kind: "fn", name: "add", params: "a, b", ret: "Number", value: "",
    cond: "", variable: "", iterable: "", body: [
      { kind: "return", name: "", value: "a + b", cond: "", variable: "",
        iterable: "", params: "", ret: "", body: [], other: [] }
    ], other: [] },
  { kind: "assign", name: "total", value: "add(1, 2)", cond: "", variable: "",
    iterable: "", params: "", ret: "", body: [], other: [] },
  { kind: "show", name: "", value: "total", cond: "", variable: "",
    iterable: "", params: "", ret: "", body: [], other: [] }
];
console.log(compile_program(prog));
"""
        )
        out = _run_node(node_src)
        assert 'function add(a, b)' in out
        assert 'return a + b;' in out
        assert 'total = add(1, 2);' in out
        assert 'console.log(total);' in out

    @needs_node
    def test_generated_program_runs_and_prints_result(self) -> None:
        node_src = (
            HARNESS
            + _script_of(_emit_self_hosted())
            + """
const prog = [
  { kind: "fn", name: "add", params: "a, b", ret: "Number", value: "",
    cond: "", variable: "", iterable: "", body: [
      { kind: "return", name: "", value: "a + b", cond: "", variable: "",
        iterable: "", params: "", ret: "", body: [], other: [] }
    ], other: [] },
  { kind: "assign", name: "total", value: "add(1, 2)", cond: "", variable: "",
    iterable: "", params: "", ret: "", body: [], other: [] },
  { kind: "show", name: "", value: "total", cond: "", variable: "",
    iterable: "", params: "", ret: "", body: [], other: [] }
];
eval(compile_program(prog));
"""
        )
        out = _run_node(node_src)
        assert '3' in out.splitlines(), f"expected '3' in output:\n{out}"

    @needs_node
    def test_generated_program_syntax_checked(self) -> None:
        node_src = (
            HARNESS
            + _script_of(_emit_self_hosted())
            + """
const prog = [
  { kind: "if", name: "", value: "", cond: "x > 0", variable: "",
    iterable: "", params: "", ret: "", body: [
      { kind: "assign", name: "y", value: "x * 2", cond: "", variable: "",
        iterable: "", params: "", ret: "", body: [], other: [] }
    ], other: [
      { kind: "assign", name: "y", value: "0", cond: "", variable: "",
        iterable: "", params: "", ret: "", body: [], other: [] }
    ] },
  { kind: "for", name: "", value: "", cond: "", variable: "n",
    iterable: "items", params: "", ret: "", body: [
      { kind: "show", name: "", value: "n", cond: "", variable: "",
        iterable: "", params: "", ret: "", body: [], other: [] }
    ], other: [] }
];
console.log(compile_program(prog));
"""
        )
        out = _run_node(node_src)
        assert 'if (x > 0)' in out
        assert 'for (const n of items)' in out
        result = subprocess.run(
            ['node', '--check', '-'],
            input=out,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f'generated JS invalid:\n{result.stderr}'
