from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse

# Test simple assignment
code = 'x = 1'
tokens = tokenize(code)
ast = parse(tokens)
print('Simple assignment:', ast)

# Test field access
code = 'x.y'
tokens = tokenize(code)
ast = parse(tokens)
print('Field access:', ast)