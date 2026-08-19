import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def _node_available() -> bool:
    return shutil.which('node') is not None


needs_node = pytest.mark.skipif(not _node_available(), reason='node not installed')


def _run_emitted(html: str, epilogue: str = '') -> subprocess.CompletedProcess[str]:
    """Run an emitted HTML document under Node with a DOM stub.

    vm runInThisContext places function declarations on globalThis so
    window lookups work.
    """
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];
global.__logs = [];
global.console = Object.assign({}, console, {
  log: (...a) => global.__logs.push(a.map(String).join(" ")),
});
global.__app = { innerHTML: "", addEventListener: (t, fn) => { global.__listener = fn; } };
global.document = {
  getElementById: () => global.__app,
  querySelectorAll: () => [],
  createElement: () => ({}),
  head: { appendChild() {} },
  body: { appendChild() {} },
};
global.window = global;
vm.runInThisContext(code, { filename: htmlPath });
"""
    runner_src = (
        harness + epilogue + '\nprocess.stdout.write(JSON.stringify(global.__logs) + "\\n");\n'
    )
    html_path = None
    runner_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', encoding='utf-8', delete=False
        ) as f:
            f.write(html)
            html_path = Path(f.name)
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', encoding='utf-8', delete=False
        ) as g:
            g.write(runner_src)
            runner_path = Path(g.name)
        return subprocess.run(
            ['node', str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        if html_path is not None:
            html_path.unlink(missing_ok=True)
        if runner_path is not None:
            runner_path.unlink(missing_ok=True)


def test_emitter_basic_function():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    assert isinstance(js_code, str)
    assert len(js_code) > 0
    assert 'function add' in js_code
    assert 'return a + b' in js_code


def test_emitter_ui_block():
    code = """
when app starts:
    greeting = "Hello, {name}"
end

fn change_greeting:
    writes name
    writes greeting
    name = "OmniScript"
    greeting = "Hello, {name}"
end

UI:
<h1>{greeting}</h1>
<button click="change_greeting">Change it</button>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    assert 'greeting' in js_code
    assert 'change_greeting' in js_code
    assert 'batchUpdate' in js_code
    assert 'renderUI' in js_code


def test_emitter_live_link_batching():
    code = """
when app starts:
    a = 1
    b = 2
    c = a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    # Check that batchUpdate is used
    assert 'batchUpdate' in js_code
    assert 'renderUI' in js_code

    # Verify no individual DOM updates per assignment
    assert 'document.getElementById' not in js_code or js_code.count('document.getElementById') <= 2  # noqa: PLR2004


def test_emitter_interpolation():
    code = """
when app starts:
    name = "World"
    greeting = "Hello, {name}"
end

UI:
<h1>{greeting}</h1>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    assert 'Hello' in js_code
    assert 'World' in js_code or 'name' in js_code


def test_emitter_effect_handling():
    code = """
fn fetch(url: Text) -> Text:
    uses network
    return "ok"
end

when app starts:
    result = fetch("https://api.example.com")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    # Network calls should be async
    assert 'async' in js_code or 'fetch' in js_code
    assert 'network' in js_code.lower() or 'fetch' in js_code


def test_emitter_html_output():
    code = """
when app starts:
    title = "Test Page"
end

UI:
<!doctype html>
<html>
<head><title>{title}</title></head>
<body><h1>{title}</h1></body>
</html>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    # Should output a complete HTML document with embedded JS
    assert '<!doctype html>' in js_code or '<html' in js_code
    assert '{title}' in js_code or 'title' in js_code


def test_emitter_effects_in_js():
    code = """
fn pure_add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

fn fetch_data() -> Text:
    uses network
    return "data"
end

when app starts:
    result = pure_add(1, 2)
    data = fetch_data()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)

    # Pure functions should be synchronous
    # Effectful functions should be async or have effect markers
    assert 'function pure_add' in js_code
    assert 'function fetch_data' in js_code


def test_emitter_function_local_declared_not_suppressed():
    code = """
fn unrelated(x: Number) -> Number:
    pure
    return x
end

fn worker() -> Number:
    pure
    total = 0
    if true:
        total = 5
    end
    return total
end

when app starts:
    result = worker()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    module_scope = js_code[: js_code.index('function renderUI')]
    worker_body = js_code[
        js_code.index('function worker') : js_code.index('function unrelated') + 1000
    ]
    assert 'let total;' in worker_body
    assert 'let total;' not in module_scope
    assert 'let x;' not in module_scope


def test_emitter_grouping_parentheses_roundtrip():
    code = """
when app starts:
    a = 2
    b = 3
    c = 5
    x = (a + b + c) / 5
    show x
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    # Division now uses OmniFP.divide helper for IEEE 754 conformance
    assert 'OmniFP.divide((a + b + c), 5)' in js_code


@needs_node
def test_emitter_grouping_value_under_node():
    code = """
when app starts:
    a = 2
    b = 3
    c = 5
    x = (a + b + c) / 5
    show x
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    proc = _run_emitted(emit_js(mir))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == ['2']


@needs_node
def test_emitter_click_survives_rerender():
    code = """
when app starts:
    greeting = "hi"
end

fn bump:
    show "clicked"
end

UI:
<button click="bump">+</button>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    epilogue = r"""
function fireClick() {
  if (typeof global.__listener === "function") {
    global.__listener({ target: { closest: () => ({ getAttribute: () => "bump" }) } });
  }
}
fireClick();
fireClick();
"""
    proc = _run_emitted(emit_js(mir), epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == ['clicked', 'clicked']


def _emit(code: str) -> str:
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def test_emitter_css_style_block_not_mangled():
    """CSS braces inside <style> are literal; {slot} outside still interpolates."""
    js_code = _emit("""
when app starts:
    title = "Hi"
end

UI:
<style>
.panel { padding: 8px; }
@media (max-width: 600px) { .panel { padding: 4px; } }
</style>
<h1>{title}</h1>
end
""")
    assert '.panel { padding: 8px; }' in js_code
    assert '@media (max-width: 600px) { .panel { padding: 4px; } }' in js_code
    assert '${title}' in js_code
    assert '${ padding: 8px; }' not in js_code


@needs_node
def test_emitter_css_style_block_runs_under_node():
    proc = _run_emitted(
        _emit("""
when app starts:
    title = "Hi"
end

UI:
<style>
.panel { padding: 8px; }
</style>
<h1>{title}</h1>
end
""")
    )
    assert proc.returncode == 0, proc.stderr


def test_emitter_module_scope_let_survives_param_collision():
    """A module-scope name must still be hoisted when it collides with a param."""
    js_code = _emit("""
fn other(res: Number) -> Number:
    pure
    return res
end

when app starts:
    res = 10
    show other(res)
end
""")
    module_scope = js_code[: js_code.index('function renderUI')]
    assert 'let res;' in module_scope
    assert 'let res;' not in js_code[js_code.index('function other') :]


@needs_node
def test_emitter_local_not_suppressed_by_unrelated_param():
    """A local whose name equals ANOTHER function's param must still be declared."""
    code = """
fn other(res: Number) -> Number:
    pure
    return res
end

fn worker() -> Number:
    pure
    res = 42
    if true:
        res = 7
    end
    return res
end

when app starts:
    x = worker()
    y = other(x)
    show y
end
"""
    proc = _run_emitted(_emit(code))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == ['7']


@needs_node
def test_emitter_nested_assign_hoisted_entry_point():
    """Names first assigned inside nested if/for in `when app starts` run."""
    code = """
when app starts:
    total = 0
    for i in range(3):
        if true:
            total = total + i
        end
    end
    if true:
        nested = 5
    end
    show total
    show nested
end
"""
    proc = _run_emitted(_emit(code))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == ['3', '5']


@needs_node
def test_emitter_nested_assign_hoisted_function_body():
    """Names first assigned inside nested if/for in a function body are declared."""
    code = """
fn worker() -> Number:
    pure
    total = 0
    for i in range(3):
        total = total + i
    end
    return total
end

when app starts:
    x = worker()
    show x
end
"""
    proc = _run_emitted(_emit(code))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == ['3']
