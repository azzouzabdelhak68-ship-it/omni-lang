#!/usr/bin/env python3
"""
Bundle size checker for OmniScript v1.0 JS emitter.
Enforces < 50KB gzipped bundle size.
"""

import gzip
import sys
from pathlib import Path
from typing import Tuple

def check_bundle_size(js_code: str, max_size: int = 51200) -> Tuple[int, bool]:
    """Return (size_in_bytes, passed)"""
    size = len(gzip.compress(js_code.encode('utf-8')))
    return size, size < max_size

def main():
    # Build a test fixture and check its bundle size
    from omni_compiler.lexer import tokenize
    from omni_compiler.parser import parse
    from omni_compiler.checker import analyze
    from omni_compiler.mir import to_mir
    from omni_compiler.emitter import emit_js
    
    # Use the basic fixture
    fixture_path = Path("tests/fixtures/valid/01_basic.omni")
    if not fixture_path.exists():
        print("❌ Test fixture not found")
        return 1
    
    code = fixture_path.read_text()
    tokens = tokenize(code)
    from omni_compiler.parser import parse
    from omni_compiler.checker import analyze
    from omni_compiler.mir import to_mir
    from omni_compiler.emitter import emit_js
    
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, analyze(ast))
    js_code = emit_js(mir)
    
    size, passed = check_bundle_size(js_code)
    print(f"JS Bundle size: {size} bytes (gzipped)")
    print(f"Limit: 51200 bytes (50KB)")
    
    if passed:
        print("✅ PASSED")
        return 0
    else:
        print("❌ FAILED: Bundle exceeds 50KB gzipped")
        return 1

if __name__ == "__main__":
    sys.exit(main())