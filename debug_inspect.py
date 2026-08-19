from omni_compiler.parser import parse
from omni_compiler.lexer import tokenize
from omni_compiler.checker import analyze
from pathlib import Path

code = Path(r'E:\simualtion\RUN_001_CLAUDE_3_5\source\system_utility.omni').read_text(encoding='utf-8')
tokens = tokenize(code)
ast = parse(tokens)
symbol_table = analyze(ast)

# Check if native_platform_execute is in the symbol table
print("Symbols in symbol table:")
for name, info in sorted(symbol_table.symbols.items(), key=lambda x: x[0]):
    kind = info.get("kind", "?")
    effects = info.get("declared_effects", {})
    uses = effects.get("uses", [])
    print(f"  {name}: kind={kind}, uses={uses}")

# Specifically check native_platform_execute
print()
rec = symbol_table.inspect_symbol("native_platform_execute")
print(f"inspect native_platform_execute: {rec}")

rec2 = symbol_table.inspect_symbol("system_info")
print(f"inspect system_info: {rec2}")