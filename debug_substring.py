from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse
from omni_compiler.checker import analyze
from omni_compiler.smt import _FunctionVerifier, verify_contracts

code = """
fn sub(text: Text, start: Number, end_pos: Number) -> Text:
    pure
    ensure result is substring(text, start, end_pos)
    return substring(text, start, end_pos)
end
"""

tokens = tokenize(code)
ast = parse(tokens)
symbol_table = analyze(ast)

fn = ast.functions[0]
verifier = _FunctionVerifier(fn)

print("Params:", verifier.params)
print("Env:", verifier.env)

# Execute the body
returns, fallthroughs = verifier._exec(fn.body, verifier.env, [])
print("Returns:", len(returns))

for ret in returns:
    print("Return expr:", ret.expr)
    print("Return conds:", ret.conds)
    
    post_env = dict(ret.env)
    post_env['result'] = ret.expr
    post = []
    for ens in fn.ensures:
        guards = []
        post.append(verifier._translate_expr(ens, post_env, guards))
        post.extend(guards)
    print("Post:", post)
    
    import z3
    solver = z3.Solver()
    solver.add(*post)
    print("Solver check:", solver.check())
    if solver.check() == z3.sat:
        m = solver.model()
        print("Model:", m)