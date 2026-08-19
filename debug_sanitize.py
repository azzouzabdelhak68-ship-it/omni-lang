from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse
from omni_compiler.checker import analyze
from omni_compiler.smt import _FunctionVerifier, verify_contracts

code = """
fn sanitize(input: Text) -> Text:
    require length(input) greater than 0
    require not contains(input, "<script>")
    ensure not contains(result, "<script>")
    ensure length(result) less or equal length(input)
    return substring(input, 0, length(input))
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
print("Fallthroughs:", len(fallthroughs))

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
    
    pre = []
    for req in fn.requires:
        guards = []
        pre.append(verifier._translate_expr(req, verifier.env, guards))
        pre.extend(guards)
    print("Pre:", pre)
    
    import z3
    solver = z3.Solver()
    solver.add(*pre, *ret.conds)
    solver.add(z3.Not(z3.And(*post)))
    print("Solver check:", solver.check())
    if solver.check() == z3.sat:
        m = solver.model()
        print("Model:", m)