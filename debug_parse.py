from omni_compiler.parser import parse
from omni_compiler.lexer import tokenize
from omni_compiler.checker import analyze
from pathlib import Path

code = Path(r'E:\simualtion\test_type.omni').read_text(encoding='utf-8')
tokens = tokenize(code)
print(f"Total tokens: {len(tokens)}")
print("First 15 tokens:")
for i, t in enumerate(tokens[:15]):
    print(f"  {i}: {t}")

# Try parsing
try:
    ast = parse(tokens)
    print("Parse OK")
    try:
        symbol_table = analyze(ast)
        print("Analyze OK")
    except Exception as e:
        print(f"Analyze error: {e}")
except Exception as e:
    print(f"Parse error: {e}")