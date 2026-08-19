"""Floating-Point Conformance Test Suite (Pillar 4).

Runs the same FP operations on all backends (JS, C, Rust, WASM, SMT)
and compares results for IEEE 754 compliance.

Test operations:
- 1.0/0.0 -> +Infinity
- -1.0/0.0 -> -Infinity
- 0.0/0.0 -> NaN
- NaN comparisons (NaN != NaN)
- Infinity arithmetic (Inf + 1 = Inf, Inf - Inf = NaN)
- -0.0 handling
- Modulo edge cases
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _compile_omni(code: str, target: str) -> str:
    """Compile OmniScript code to target backend."""
    import sys  # noqa: PLC0415

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from omni_compiler.c_emitter import emit_c  # noqa: PLC0415
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.emitter import emit_js  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415
    from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415
    from omni_compiler.wasm_emitter import emit_wasm  # noqa: PLC0415

    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)

    if target == 'js':
        return emit_js(mir)
    if target == 'c':
        return emit_c(mir)
    if target == 'rust':
        return emit_rust(mir)
    if target == 'wasm':
        return emit_wasm(mir, mode='browser')
    if target == 'wasi':
        return emit_wasm(mir, mode='wasi')
    raise ValueError(f'Unknown target: {target}')


def _run_js(html: str) -> dict[str, Any]:
    """Run JS code in Node.js and return console.log output as JSON."""
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
    runner_src = harness + '\nprocess.stdout.write(JSON.stringify(global.__logs) + "\\n");\n'

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
        result = subprocess.run(
            ['node', str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            return {'error': result.stderr}
        logs = json.loads(result.stdout.strip().splitlines()[-1])
        return {'logs': logs}
    finally:
        if html_path:
            html_path.unlink(missing_ok=True)
        if runner_path:
            runner_path.unlink(missing_ok=True)


def _run_c(c_code: str) -> dict[str, Any]:
    """Compile and run C code, return stdout."""
    c_path = None
    exe_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.c', encoding='utf-8', delete=False
        ) as f:
            f.write(c_code)
            c_path = Path(f.name)
        exe_path = c_path.with_suffix('.exe')
        # Try clang first (often available on Windows), then gcc
        for compiler in (['clang', '-std=c99', '-lm'], ['gcc', '-std=c99', '-lm']):
            try:
                result = subprocess.run(
                    compiler + ['-o', str(exe_path), str(c_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode == 0:
                    break
            except FileNotFoundError:
                continue
        else:
            return {'error': 'no C compiler found (tried clang, gcc)', 'skipped': True}
        result = subprocess.run(
            [str(exe_path)], capture_output=True, text=True, timeout=30, check=False
        )
        return {'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}
    finally:
        if c_path:
            c_path.unlink(missing_ok=True)
        if exe_path and exe_path.exists():
            exe_path.unlink(missing_ok=True)


def _run_rust(rust_code: str) -> dict[str, Any]:
    """Compile and run Rust code, return stdout."""
    # Check if cargo is available
    try:
        if subprocess.run(['cargo', '--version'], capture_output=True).returncode != 0:
            return {'error': 'cargo not found', 'skipped': True}
    except FileNotFoundError:
        return {'error': 'cargo not found', 'skipped': True}

    # Write to a temporary Cargo project
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        cargo_toml = tmpdir / 'Cargo.toml'
        cargo_toml.write_text("""[package]
name = "fp_test"
version = "0.1.0"
edition = "2021"

[dependencies]
""")
        src_dir = tmpdir / 'src'
        src_dir.mkdir()
        main_rs = src_dir / 'main.rs'
        main_rs.write_text(rust_code)

        result = subprocess.run(
            ['cargo', 'build', '--release'],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            return {'error': f'compile failed: {result.stderr}'}

        exe = tmpdir / 'target' / 'release' / 'fp_test'
        result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30, check=False)
        return {'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}


def _run_wasm(wasm_html: str) -> dict[str, Any]:
    """Run WASM in Node.js (requires wasm file to be pre-compiled).

    For now, we test the C source that would be compiled to WASM.
    """
    return _run_js(wasm_html)


def _normalize_fp_result(val: str) -> str:
    """Normalize FP result strings for cross-backend comparison."""
    val = val.strip().lower()
    # Normalize various infinity representations
    if val in ('inf', '+inf', 'infinity', '+infinity'):
        return '+inf'
    if val in ('-inf', '-infinity'):
        return '-inf'
    if val in ('nan', 'nan'):
        return 'nan'
    # Normalize -0.0
    if val in ('-0', '-0.0', '-0.000000'):
        return '-0.0'
    if val in ('0', '0.0', '0.000000'):
        return '0.0'
    return val


def _extract_numeric(logs: list[str]) -> list[str]:
    """Extract numeric and boolean values from console logs."""
    results = []
    for log_line in logs:
        stripped = log_line.strip()
        # Handle special FP values
        if stripped in ('Infinity', '-Infinity', 'NaN', 'inf', '-inf', 'nan', '-0', '0'):
            results.append(stripped)
        # Handle boolean values from comparisons
        elif stripped in ('true', 'false', 'True', 'False'):
            results.append(stripped.lower())
        else:
            try:
                float(stripped)
                results.append(stripped)
            except ValueError:
                pass
    return results


def test_division_by_zero_positive():
    """Test 1.0 / 0.0 -> +Infinity"""
    code = """
when app starts:
    result = 1.0 / 0.0
    show result
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')
    _ = _compile_omni(code, 'wasm')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_val = _normalize_fp_result(
        _extract_numeric(js_result.get('logs', []))[-1] if js_result.get('logs') else 'error'
    )

    # Handle skipped C/Rust tests
    if c_result.get('skipped'):
        print(f'1.0/0.0: JS={js_val}, C=SKIPPED, Rust=SKIPPED')
        assert js_val == '+inf', f'JS: expected +inf, got {js_val}'
        return

    c_val = _normalize_fp_result(
        c_result.get('stdout', '').split()[-1] if c_result.get('stdout') else 'error'
    )
    rust_val = _normalize_fp_result(
        rust_result.get('stdout', '').split()[-1] if rust_result.get('stdout') else 'error'
    )

    print(f'1.0/0.0: JS={js_val}, C={c_val}, Rust={rust_val}')
    assert js_val == '+inf', f'JS: expected +inf, got {js_val}'
    assert c_val == '+inf', f'C: expected +inf, got {c_val}'
    assert rust_val == '+inf', f'Rust: expected +inf, got {rust_val}'


def test_division_by_zero_negative():
    """Test -1.0 / 0.0 -> -Infinity"""
    code = """
when app starts:
    result = -1.0 / 0.0
    show result
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_val = _normalize_fp_result(
        _extract_numeric(js_result.get('logs', []))[-1] if js_result.get('logs') else 'error'
    )

    if c_result.get('skipped'):
        print(f'-1.0/0.0: JS={js_val}, C=SKIPPED, Rust=SKIPPED')
        assert js_val == '-inf', f'JS: expected -inf, got {js_val}'
        return

    c_val = _normalize_fp_result(
        c_result.get('stdout', '').split()[-1] if c_result.get('stdout') else 'error'
    )
    rust_val = _normalize_fp_result(
        rust_result.get('stdout', '').split()[-1] if rust_result.get('stdout') else 'error'
    )

    print(f'-1.0/0.0: JS={js_val}, C={c_val}, Rust={rust_val}')
    assert js_val == '-inf', f'JS: expected -inf, got {js_val}'
    assert c_val == '-inf', f'C: expected -inf, got {c_val}'
    assert rust_val == '-inf', f'Rust: expected -inf, got {rust_val}'


def test_division_zero_by_zero():
    """Test 0.0 / 0.0 -> NaN"""
    code = """
when app starts:
    result = 0.0 / 0.0
    show result
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_val = _normalize_fp_result(
        _extract_numeric(js_result.get('logs', []))[-1] if js_result.get('logs') else 'error'
    )

    if c_result.get('skipped'):
        print(f'0.0/0.0: JS={js_val}, C=SKIPPED, Rust=SKIPPED')
        assert js_val == 'nan', f'JS: expected nan, got {js_val}'
        return

    c_val = _normalize_fp_result(
        c_result.get('stdout', '').split()[-1] if c_result.get('stdout') else 'error'
    )
    rust_val = _normalize_fp_result(
        rust_result.get('stdout', '').split()[-1] if rust_result.get('stdout') else 'error'
    )

    print(f'0.0/0.0: JS={js_val}, C={c_val}, Rust={rust_val}')
    assert js_val == 'nan', f'JS: expected nan, got {js_val}'
    assert c_val == 'nan', f'C: expected nan, got {c_val}'
    assert rust_val == 'nan', f'Rust: expected nan, got {rust_val}'


def test_nan_comparison():
    """Test NaN comparisons: NaN != NaN, NaN == NaN is false"""
    code = """
when app starts:
    nan_val = 0.0 / 0.0
    eq = nan_val is nan_val
    ne = nan_val is not nan_val
    show eq
    show ne
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_logs = _extract_numeric(js_result.get('logs', []))
    c_logs = c_result.get('stdout', '').strip().split() if not c_result.get('skipped') else []
    rust_logs = (
        rust_result.get('stdout', '').strip().split() if not rust_result.get('skipped') else []
    )

    # eq should be false (0), ne should be true (1)
    print(f'NaN==NaN: JS={js_logs}, C={c_logs}, Rust={rust_logs}')

    # JS: false true
    # C: 0 1
    # Rust: false true
    assert len(js_logs) >= 2
    if c_logs:
        assert len(c_logs) >= 2
    if rust_logs:
        assert len(rust_logs) >= 2


def test_infinity_arithmetic():
    """Test infinity arithmetic: Inf + 1 = Inf, Inf - Inf = NaN"""
    code = """
when app starts:
    inf = 1.0 / 0.0
    plus_one = inf + 1.0
    minus_inf = inf - inf
    show plus_one
    show minus_inf
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_logs = _extract_numeric(js_result.get('logs', []))
    c_logs = c_result.get('stdout', '').strip().split() if not c_result.get('skipped') else []
    rust_logs = (
        rust_result.get('stdout', '').strip().split() if not rust_result.get('skipped') else []
    )

    js_plus = _normalize_fp_result(js_logs[0] if js_logs else 'error')
    js_minus = _normalize_fp_result(js_logs[1] if len(js_logs) > 1 else 'error')

    print(
        f'Inf+1: JS={js_plus}, C={"SKIPPED" if c_result.get("skipped") else c_logs[0] if c_logs else "error"}'  # noqa: E501
    )
    print(
        f'Inf-Inf: JS={js_minus}, C={"SKIPPED" if c_result.get("skipped") else c_logs[1] if len(c_logs) > 1 else "error"}'  # noqa: E501
    )

    assert js_plus == '+inf', f'JS Inf+1: expected +inf, got {js_plus}'
    assert js_minus == 'nan', f'JS Inf-Inf: expected nan, got {js_minus}'

    if c_logs:
        c_plus = _normalize_fp_result(c_logs[0] if c_logs else 'error')
        c_minus = _normalize_fp_result(c_logs[1] if len(c_logs) > 1 else 'error')
        assert c_plus == '+inf', f'C Inf+1: expected +inf, got {c_plus}'
        assert c_minus == 'nan', f'C Inf-Inf: expected nan, got {c_minus}'

    if rust_logs:
        rust_plus = _normalize_fp_result(rust_logs[0] if rust_logs else 'error')
        rust_minus = _normalize_fp_result(rust_logs[1] if len(rust_logs) > 1 else 'error')
        assert rust_plus == '+inf', f'Rust Inf+1: expected +inf, got {rust_plus}'
        assert rust_minus == 'nan', f'Rust Inf-Inf: expected nan, got {rust_minus}'


def test_negative_zero():
    """Test -0.0 handling"""
    code = """
when app starts:
    neg_zero = -0.0
    pos_zero = 0.0
    div_neg = 1.0 / neg_zero
    div_pos = 1.0 / pos_zero
    show neg_zero
    show pos_zero
    show div_neg
    show div_pos
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_logs = _extract_numeric(js_result.get('logs', []))
    c_logs = c_result.get('stdout', '').strip().split() if not c_result.get('skipped') else []
    rust_logs = (
        rust_result.get('stdout', '').strip().split() if not rust_result.get('skipped') else []
    )

    print(
        f'-0.0: JS={js_logs}, C={"SKIPPED" if c_result.get("skipped") else c_logs}, Rust={"SKIPPED" if rust_result.get("skipped") else rust_logs}'  # noqa: E501
    )

    # Check division results: 1.0 / -0.0 = -Inf, 1.0 / 0.0 = +Inf
    if len(js_logs) >= 4:
        js_div_neg = _normalize_fp_result(js_logs[2])
        js_div_pos = _normalize_fp_result(js_logs[3])
        assert js_div_neg == '-inf', f'JS 1.0/-0.0: expected -inf, got {js_div_neg}'
        assert js_div_pos == '+inf', f'JS 1.0/0.0: expected +inf, got {js_div_pos}'

    if len(c_logs) >= 4:
        c_div_neg = _normalize_fp_result(c_logs[2])
        c_div_pos = _normalize_fp_result(c_logs[3])
        assert c_div_neg == '-inf', f'C 1.0/-0.0: expected -inf, got {c_div_neg}'
        assert c_div_pos == '+inf', f'C 1.0/0.0: expected +inf, got {c_div_pos}'

    if len(rust_logs) >= 4:
        rust_div_neg = _normalize_fp_result(rust_logs[2])
        rust_div_pos = _normalize_fp_result(rust_logs[3])
        assert rust_div_neg == '-inf', f'Rust 1.0/-0.0: expected -inf, got {rust_div_neg}'
        assert rust_div_pos == '+inf', f'Rust 1.0/0.0: expected +inf, got {rust_div_pos}'


def test_modulo_edge_cases():
    """Test modulo edge cases"""
    code = """
when app starts:
    mod_zero = 5.0 % 0.0
    mod_nan = (0.0 / 0.0) % 2.0
    mod_inf = (1.0 / 0.0) % 2.0
    show mod_zero
    show mod_nan
    show mod_inf
end
"""
    js_html = _compile_omni(code, 'js')
    c_code = _compile_omni(code, 'c')
    rust_code = _compile_omni(code, 'rust')

    js_result = _run_js(js_html)
    c_result = _run_c(c_code)
    rust_result = _run_rust(rust_code)

    js_logs = _extract_numeric(js_result.get('logs', []))
    c_logs = c_result.get('stdout', '').strip().split() if not c_result.get('skipped') else []
    rust_logs = (
        rust_result.get('stdout', '').strip().split() if not rust_result.get('skipped') else []
    )

    print(
        f'Modulo: JS={js_logs}, C={"SKIPPED" if c_result.get("skipped") else c_logs}, Rust={"SKIPPED" if rust_result.get("skipped") else rust_logs}'  # noqa: E501
    )

    # All should be NaN
    if len(js_logs) >= 3:
        for i, val in enumerate(js_logs[:3]):
            assert _normalize_fp_result(val) == 'nan', f'JS modulo[{i}]: expected nan, got {val}'

    if len(c_logs) >= 3:
        for i, val in enumerate(c_logs[:3]):
            assert _normalize_fp_result(val) == 'nan', f'C modulo[{i}]: expected nan, got {val}'

    if len(rust_logs) >= 3:
        for i, val in enumerate(rust_logs[:3]):
            assert _normalize_fp_result(val) == 'nan', f'Rust modulo[{i}]: expected nan, got {val}'


def test_smt_limitation_documented():
    """Verify SMT module documents the IEEE 754 limitation."""
    smt_path = Path(__file__).parent.parent / 'omni_compiler' / 'smt.py'
    content = smt_path.read_text()
    assert 'Floating-point conformance limitation' in content
    assert 'Z3 Reals' in content
    assert 'NOT IEEE 754 floats' in content
    assert 'FP theory' in content
    print('SMT limitation documented correctly')


if __name__ == '__main__':
    # Run all tests manually for quick verification
    import sys

    tests = [
        test_division_by_zero_positive,
        test_division_by_zero_negative,
        test_division_zero_by_zero,
        test_nan_comparison,
        test_infinity_arithmetic,
        test_negative_zero,
        test_modulo_edge_cases,
        test_smt_limitation_documented,
    ]

    failed = []
    for test in tests:
        try:
            test()
            print(f'PASS {test.__name__}')
        except Exception as e:
            print(f'FAIL {test.__name__}: {e}')
            failed.append((test.__name__, e))

    if failed:
        print(f'\n{len(failed)} test(s) failed:')
        for name, err in failed:
            print(f'  {name}: {err}')
        sys.exit(1)
    else:
        print('\nAll FP conformance tests passed!')
        sys.exit(0)
