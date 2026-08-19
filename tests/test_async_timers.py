"""Tests for OMNISYS.async timer operations: interval, timeout, tick, cancel, await."""

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
    """Run an emitted HTML document under Node with a DOM stub."""
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
// Polyfill requestAnimationFrame/cancelAnimationFrame for Node
global.requestAnimationFrame = function(fn) {
    return setTimeout(fn, 16);
};
global.cancelAnimationFrame = function(id) {
    clearTimeout(id);
};
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


def _compile_and_emit(code: str) -> str:
    """Helper to compile OmniScript code and emit JS."""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_js(mir)


def test_async_delay_compiles():
    """Test that omnisys.async.delay compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.delay' in js_code
    assert 'setTimeout' in js_code


def test_async_interval_compiles():
    """Test that omnisys.async.interval compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.interval(100, fn() -> None: end)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.interval' in js_code
    assert 'setInterval' in js_code


def test_async_timeout_compiles():
    """Test that omnisys.async.timeout compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.timeout(100, fn() -> None: end)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.timeout' in js_code
    assert 'setTimeout' in js_code


def test_async_tick_compiles():
    """Test that omnisys.async.tick compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.tick(fn() -> None: end)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.tick' in js_code
    assert 'requestAnimationFrame' in js_code


def test_async_cancel_compiles():
    """Test that omnisys.async.cancel compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
    omnisys.async.cancel(task)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.cancel' in js_code


def test_async_await_compiles():
    """Test that omnisys.async.await compiles without errors."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
    result = await omnisys.async.await(task)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.await' in js_code
    assert 'await' in js_code


@needs_node
def test_async_delay_runs():
    """Test that omnisys.async.delay executes and resolves."""
    code = """
import OMNISYS.async

when app starts:
    show "start"
    task = omnisys.async.delay(50)
    await omnisys.async.await(task)
    show "done"
end
"""
    js_code = _compile_and_emit(code)
    epilogue = r"""
// Wait a bit for the async delay to complete
setTimeout(function() {
    process.stdout.write(JSON.stringify(global.__logs) + "\n");
    process.exit(0);
}, 200);
"""
    proc = _run_emitted(js_code, epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    assert 'start' in logs
    assert 'done' in logs


@needs_node
def test_async_timeout_runs():
    """Test that omnisys.async.timeout executes the callback."""
    code = """
import OMNISYS.async

when app starts:
    show "before timeout"
    task = omnisys.async.timeout(50, fn() -> None:
        show "timeout fired"
    end)
    await omnisys.async.await(task)
    show "after await"
end
"""
    js_code = _compile_and_emit(code)
    epilogue = r"""
setTimeout(function() {
    process.stdout.write(JSON.stringify(global.__logs) + "\n");
    process.exit(0);
}, 200);
"""
    proc = _run_emitted(js_code, epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    assert 'before timeout' in logs
    assert 'timeout fired' in logs
    assert 'after await' in logs


@needs_node
def test_async_interval_runs():
    """Test that omnisys.async.interval fires repeatedly."""
    code = """
import OMNISYS.async

when app starts:
    show "before interval"
    count = 0
    task = omnisys.async.interval(30, fn() -> None:
        count = count + 1
        if count >= 3:
            omnisys.async.cancel(task)
            show "interval done: {count}"
        end
    end)
    await omnisys.async.await(task)
    show "after await"
end
"""
    js_code = _compile_and_emit(code)
    epilogue = r"""
setTimeout(function() {
    process.stdout.write(JSON.stringify(global.__logs) + "\n");
    process.exit(0);
}, 500);
"""
    proc = _run_emitted(js_code, epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    assert 'before interval' in logs
    assert any('interval done: 3' in log for log in logs)
    assert 'after await' in logs


@needs_node
def test_async_tick_runs():
    """Test that omnisys.async.tick fires on animation frame."""
    code = """
import OMNISYS.async

when app starts:
    show "before tick"
    fired = false
    task = omnisys.async.tick(fn() -> None:
        if not fired:
            fired = true
            show "tick fired"
            omnisys.async.cancel(task)
        end
    end)
    await omnisys.async.await(task)
    show "after await"
end
"""
    js_code = _compile_and_emit(code)
    epilogue = r"""
setTimeout(function() {
    process.stdout.write(JSON.stringify(global.__logs) + "\n");
    process.exit(0);
}, 200);
"""
    proc = _run_emitted(js_code, epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    assert 'before tick' in logs
    assert 'tick fired' in logs
    assert 'after await' in logs


@needs_node
def test_async_cancel_stops_interval():
    """Test that omnisys.async.cancel stops an interval."""
    code = """
import OMNISYS.async

when app starts:
    count = 0
    task = omnisys.async.interval(20, fn() -> None:
        count = count + 1
    end)
    // Cancel after a short delay
    cancel_task = omnisys.async.timeout(60, fn() -> None:
        omnisys.async.cancel(task)
        show "cancelled at {count}"
    end)
    await omnisys.async.await(cancel_task)
    show "done"
end
"""
    js_code = _compile_and_emit(code)
    epilogue = r"""
setTimeout(function() {
    process.stdout.write(JSON.stringify(global.__logs) + "\n");
    process.exit(0);
}, 300);
"""
    proc = _run_emitted(js_code, epilogue=epilogue)
    assert proc.returncode == 0, proc.stderr
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    assert any('cancelled at' in log for log in logs)
    assert 'done' in logs


def test_async_all_race_any_compile():
    """Test that omnisys.async.all, race, any compile."""
    code = """
import OMNISYS.async

when app starts:
    t1 = omnisys.async.delay(100)
    t2 = omnisys.async.delay(200)
    all_task = omnisys.async.all([t1, t2])
    race_task = omnisys.async.race([t1, t2])
    any_task = omnisys.async.any([t1, t2])
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.all' in js_code
    assert 'omnisys.async.race' in js_code
    assert 'omnisys.async.any' in js_code
    assert 'Promise.all' in js_code
    assert 'Promise.race' in js_code
    assert 'Promise.any' in js_code


def test_async_task_compiles():
    """Test that omnisys.async.task compiles."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.task(fn() -> None:
        show "in task"
    end)
    await omnisys.async.await(task)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.task' in js_code


def test_async_channel_compiles():
    """Test that omnisys.async.channel, send, recv compile."""
    code = """
import OMNISYS.async

when app starts:
    ch = omnisys.async.channel(10)
    send_task = omnisys.async.channel_send(ch, 42)
    recv_task = omnisys.async.channel_recv(ch)
    await omnisys.async.await(send_task)
    await omnisys.async.await(recv_task)
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.channel' in js_code
    assert 'omnisys.async.channel_send' in js_code
    assert 'omnisys.async.channel_recv' in js_code


def test_async_is_promise_compiles():
    """Test that omnisys.async.is_promise compiles."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
    is_p = omnisys.async.is_promise(task)
    show is_p
end
"""
    js_code = _compile_and_emit(code)
    assert 'omnisys.async.is_promise' in js_code


def test_c_emitter_includes_async_stubs():
    """Test that C emitter includes async stubs."""
    from omni_compiler.c_emitter import emit_c  # noqa: PLC0415
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
    omnisys.async.cancel(task)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert 'OmniTask' in c_code
    assert 'omnisys_async_task' in c_code
    assert 'omnisys_async_delay' in c_code
    assert 'omnisys_async_interval' in c_code
    assert 'omnisys_async_timeout' in c_code
    assert 'omnisys_async_tick' in c_code
    assert 'omnisys_async_cancel' in c_code
    assert 'omnisys_async_await' in c_code


def test_rust_emitter_includes_async_stubs():
    """Test that Rust emitter includes async stubs."""
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415
    from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415

    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.delay(100)
    omnisys.async.cancel(task)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    rust_code = emit_rust(mir)

    assert 'OmniTask' in rust_code
    assert 'omnisys_async_task' in rust_code
    assert 'omnisys_async_delay' in rust_code
    assert 'omnisys_async_interval' in rust_code
    assert 'omnisys_async_timeout' in rust_code
    assert 'omnisys_async_tick' in rust_code
    assert 'omnisys_async_cancel' in rust_code
    assert 'omnisys_async_await' in rust_code


def test_arity_checking_interval():
    """Test that interval requires 2 arguments."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.interval(100)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as exc_info:
        analyze(ast)
    assert 'expects 2 argument' in str(exc_info.value)


def test_arity_checking_timeout():
    """Test that timeout requires 2 arguments."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.timeout(100)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as exc_info:
        analyze(ast)
    assert 'expects 2 argument' in str(exc_info.value)


def test_arity_checking_tick():
    """Test that tick requires 1 argument."""
    code = """
import OMNISYS.async

when app starts:
    task = omnisys.async.tick()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as exc_info:
        analyze(ast)
    assert 'expects 1 argument' in str(exc_info.value)


def test_arity_checking_cancel():
    """Test that cancel requires 1 argument."""
    code = """
import OMNISYS.async

when app starts:
    omnisys.async.cancel()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as exc_info:
        analyze(ast)
    assert 'expects 1 argument' in str(exc_info.value)


def test_arity_checking_await():
    """Test that await requires 1 argument."""
    code = """
import OMNISYS.async

when app starts:
    result = await omnisys.async.await()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as exc_info:
        analyze(ast)
    assert 'expects 1 argument' in str(exc_info.value)
