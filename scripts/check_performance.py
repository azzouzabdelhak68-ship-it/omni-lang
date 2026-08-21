#!/usr/bin/env python3
"""Performance gate checker for OmniScript v1.0

Enforces performance budgets per Section 20.4 of the spec.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_check_benchmark(file_path: str, iterations: int = 10) -> float:
    """Run `omni check` multiple times and return average time in ms"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'check', file_path],
            capture_output=True, text=True, cwd='.'
        )
        end = time.perf_counter()
        if result.returncode == 0:
            times.append((end - start) * 1000)  # Convert to ms
        else:
            return -1
    return sum(times) / len(times) if times else -1

def run_startup_benchmark(file_path: str, iterations: int = 5) -> float:
    """Run `omni run` cold start multiple times and return average time in ms"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'run', file_path],
            capture_output=True, text=True, cwd='.', timeout=10
        )
        end = time.perf_counter()
        if result.returncode == 0:
            times.append((end - start) * 1000)
        else:
            return -1
    return sum(times) / len(times) if times else -1

def check_bundle_size(js_output: str) -> int:
    """Return gzipped size of JS output in bytes"""
    import gzip
    return len(gzip.compress(js_output.encode('utf-8')))

def main():
    # Find a test file to benchmark
    test_file = 'tests/fixtures/valid/01_basic.omni'
    
    if not Path('tests/fixtures/valid/01_basic.omni').exists():
        print('Test fixture not found')
        return 1
    
    print('Running performance benchmarks...')
    
    # Check `omni check` latency
    check_time = run_check_benchmark('tests/fixtures/valid/01_basic.omni')
    if check_time < 0:
        print('❌ `omni check` failed')
        return 1
    print(f'  omni check: {check_time:.1f}ms (budget: <200ms)')
    if check_time >= 200:
        print(f'  ❌ FAILED: {check_time:.1f}ms >= 200ms budget')
        return 1
    print('  ✅ PASSED')
    
    # Check `omni run` cold start
    run_time = run_startup_benchmark('tests/fixtures/valid/01_basic.omni')
    if run_time < 0:
        print('❌ `omni run` failed')
        return 1
    print(f'  omni run (cold): {run_time:.1f}ms (budget: <500ms)')
    if run_time >= 500:
        print(f'  ❌ FAILED: {run_time:.1f}ms >= 500ms budget')
        return 1
    print('  ✅ PASSED')
    
    # Check bundle size (need to generate JS first)
    from omni_compiler.checker import analyze
    from omni_compiler.emitter import emit_js
    from omni_compiler.lexer import tokenize
    from omni_compiler.mir import to_mir
    from omni_compiler.parser import parse
    
    code = Path('tests/fixtures/valid/01_basic.omni').read_text()
    tokens = tokenize(code)
    
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, analyze(ast))
    js_code = emit_js(mir)
    
    bundle_size = len(gzip.compress(js_code.encode('utf-8')))
    print(f'  JS bundle size: {bundle_size} bytes (budget: <51200 bytes)')
    if bundle_size >= 51200:
        print(f'  ❌ FAILED: {bundle_size} bytes >= 51200 bytes budget')
        return 1
    print('  ✅ PASSED')
    
    print('\n✅ All performance gates passed!')
    return 0

if __name__ == '__main__':
    sys.exit(main())