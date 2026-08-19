from omni_compiler.parser import parse
from omni_compiler.lexer import tokenize
from pathlib import Path

code = Path(r'E:\simualtion\RUN_001_CLAUDE_3_5\source\system_utility.omni').read_text(encoding='utf-8')
tokens = tokenize(code)
ast = parse(tokens)

print("Functions in AST:")
for fn in ast.functions:
    print(f"  name={fn.name}, return_type={fn.return_type}, params={len(fn.params)}")
    print(f"    body has {len(fn.body)} statements")
    for i, stmt in enumerate(fn.body):
        print(f"      stmt[{i}]: {stmt.kind if hasattr(stmt, 'kind') else type(stmt).__name__}")

print(f"\nTotal functions: {len(ast.functions)}")
print(f"App block: {ast.app_block is not None}")
print(f"Types: {ast.types}")