#!/usr/bin/env python3
"""Performance gate checker for OmniScript v1.0 CI.

Reads benchmark_results.json (written by scripts/benchmark.py) and enforces
the budgets from Section 20.4 of the spec:
  - `omni check` average latency < 200ms
  - `omni run` cold-start average < 500ms
  - gzipped JS bundle size < 51200 bytes (50KB)

If the results file is missing, it re-runs the benchmark in-line so the job
still works when invoked directly.

Usage:
  python scripts/check_performance_gates.py
"""

import json
import sys
from pathlib import Path

CHECK_BUDGET_MS = 200.0
RUN_BUDGET_MS = 500.0
BUNDLE_BUDGET_BYTES = 51200
RESULTS_FILE = 'benchmark_results.json'
DEFAULT_FIXTURE = 'tests/fixtures/valid/01_basic.omni'


def run_benchmark_inline() -> dict:
    """Fall back to running the benchmark directly if the results file is stale."""
    import importlib.util
    import sys as _sys

    module_path = Path(__file__).resolve().parent / 'benchmark.py'
    spec = importlib.util.spec_from_file_location('_omni_benchmark', module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Could not load scripts/benchmark.py')
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    _sys.modules['_omni_benchmark'] = benchmark

    check_ms = benchmark.run_check_benchmark(DEFAULT_FIXTURE, iterations=5)
    run_ms = benchmark.run_startup_benchmark(DEFAULT_FIXTURE, iterations=3)
    bundle_bytes = benchmark.measure_bundle_size(DEFAULT_FIXTURE)
    return {
        'fixture': DEFAULT_FIXTURE,
        'check_ms': check_ms,
        'run_ms': run_ms,
        'bundle_bytes': bundle_bytes,
    }


def load_results() -> dict:
    path = Path(RESULTS_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            print('benchmark_results.json is malformed; re-running benchmark')
    return run_benchmark_inline()


def main() -> int:
    results = load_results()

    check_ms = float(results.get('check_ms', -1))
    run_ms = float(results.get('run_ms', -1))
    bundle_bytes = int(results.get('bundle_bytes', -1))

    print(f"Checking performance gates for {results.get('fixture', DEFAULT_FIXTURE)}")
    failed = False

    if check_ms < 0:
        print('  omni check: FAILED to benchmark')
        failed = True
    elif check_ms < CHECK_BUDGET_MS:
        print(f'  omni check: {check_ms:.1f}ms (budget: <{CHECK_BUDGET_MS:.0f}ms) PASSED')
    else:
        print(f'  omni check: {check_ms:.1f}ms (budget: <{CHECK_BUDGET_MS:.0f}ms) FAILED')
        failed = True

    if run_ms < 0:
        print('  omni run: FAILED to benchmark')
        failed = True
    elif run_ms < RUN_BUDGET_MS:
        print(f'  omni run: {run_ms:.1f}ms (budget: <{RUN_BUDGET_MS:.0f}ms) PASSED')
    else:
        print(f'  omni run: {run_ms:.1f}ms (budget: <{RUN_BUDGET_MS:.0f}ms) FAILED')
        failed = True

    if bundle_bytes < 0:
        print('  JS bundle: FAILED to measure')
        failed = True
    elif bundle_bytes < BUNDLE_BUDGET_BYTES:
        print(f'  JS bundle: {bundle_bytes} bytes (budget: <{BUNDLE_BUDGET_BYTES}) PASSED')
    else:
        print(f'  JS bundle: {bundle_bytes} bytes (budget: <{BUNDLE_BUDGET_BYTES}) FAILED')
        failed = True

    if failed:
        print('\nSome performance gates failed.')
        return 1
    print('\nAll performance gates passed!')
    return 0


if __name__ == '__main__':
    sys.exit(main())