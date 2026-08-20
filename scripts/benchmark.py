#!/usr/bin/env python3
"""
Benchmark runner for OmniScript v1.0.

Measures `omni check` latency, `omni run` cold-start time, and JS bundle
size, then writes results to benchmark_results.json for the CI performance
gate job to enforce.

Usage:
  python scripts/benchmark.py [--iterations N]
"""

import argparse
import gzip
import json
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_FIXTURE = "tests/fixtures/valid/01_basic.omni"
RESULTS_FILE = "benchmark_results.json"


def run_check_benchmark(file_path: str, iterations: int = 10) -> float:
    """Run `omni check` multiple times and return average time in ms."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = subprocess.run(
            ["python", "-m", "omni_compiler.cli", "check", file_path],
            capture_output=True,
            text=True,
            cwd=".",
        )
        end = time.perf_counter()
        if result.returncode != 0:
            print(f"  omni check failed: {result.stderr.strip()}")
            return -1.0
        times.append((end - start) * 1000)
    return sum(times) / len(times) if times else -1.0


def run_startup_benchmark(file_path: str, iterations: int = 5) -> float:
    """Run `omni run` cold start multiple times and return average time in ms."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            result = subprocess.run(
                ["python", "-m", "omni_compiler.cli", "run", file_path],
                capture_output=True,
                text=True,
                cwd=".",
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            print("  omni run timed out")
            return -1.0
        end = time.perf_counter()
        if result.returncode != 0:
            print(f"  omni run failed: {result.stderr.strip()}")
            return -1.0
        times.append((end - start) * 1000)
    return sum(times) / len(times) if times else -1.0


def measure_bundle_size(file_path: str) -> int:
    """Return gzipped size of the emitted JS in bytes."""
    from omni_compiler.checker import analyze
    from omni_compiler.emitter import emit_js
    from omni_compiler.lexer import tokenize
    from omni_compiler.mir import to_mir
    from omni_compiler.parser import parse

    code = Path(file_path).read_text()
    ast = parse(tokenize(code))
    mir = to_mir(ast, analyze(ast))
    js_code = emit_js(mir)
    return len(gzip.compress(js_code.encode("utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description="OmniScript benchmark runner")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    if not Path(args.fixture).exists():
        print(f"Test fixture not found: {args.fixture}")
        return 1

    print("Running performance benchmarks...")

    check_ms = run_check_benchmark(args.fixture, iterations=args.iterations)
    if check_ms < 0:
        return 1
    print(f"  omni check: {check_ms:.1f}ms (avg of {args.iterations})")

    run_ms = run_startup_benchmark(args.fixture, iterations=max(1, args.iterations // 2))
    if run_ms < 0:
        return 1
    print(f"  omni run (cold): {run_ms:.1f}ms")

    bundle_bytes = measure_bundle_size(args.fixture)
    print(f"  JS bundle (gzipped): {bundle_bytes} bytes")

    results = {
        "fixture": args.fixture,
        "check_ms": round(check_ms, 1),
        "run_ms": round(run_ms, 1),
        "bundle_bytes": bundle_bytes,
    }
    Path(RESULTS_FILE).write_text(json.dumps(results, indent=2))
    print(f"Results written to {RESULTS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())