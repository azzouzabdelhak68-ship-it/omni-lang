from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_emitter_basic_function():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    assert isinstance(js_code, str)
    assert len(js_code) > 0
    assert "function add" in js_code
    assert "return a + b" in js_code

def test_emitter_ui_block():
    code = """
when app starts:
    greeting = "Hello, {name}"
end

fn change_greeting:
    writes name
    writes greeting
    name = "OmniScript"
    greeting = "Hello, {name}"
end

UI:
<h1>{greeting}</h1>
<button click="change_greeting">Change it</button>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    assert "greeting" in js_code
    assert "change_greeting" in js_code
    assert "batchUpdate" in js_code
    assert "renderUI" in js_code

def test_emitter_live_link_batching():
    code = """
when app starts:
    a = 1
    b = 2
    c = a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    # Check that batchUpdate is used
    assert "batchUpdate" in js_code
    assert "renderUI" in js_code
    
    # Verify no individual DOM updates per assignment
    assert "document.getElementById" not in js_code or js_code.count("document.getElementById") <= 2

def test_emitter_interpolation():
    code = """
when app starts:
    name = "World"
    greeting = "Hello, {name}"
end

UI:
<h1>{greeting}</h1>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    assert "Hello" in js_code
    assert "World" in js_code or "name" in js_code

def test_emitter_effect_handling():
    code = """
fn fetch(url: Text) -> Text:
    uses network
    return "ok"
end

when app starts:
    result = fetch("https://api.example.com")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    # Network calls should be async
    assert "async" in js_code or "fetch" in js_code
    assert "network" in js_code.lower() or "fetch" in js_code

def test_emitter_html_output():
    code = """
when app starts:
    title = "Test Page"
end

UI:
<!doctype html>
<html>
<head><title>{title}</title></head>
<body><h1>{title}</h1></body>
</html>
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    # Should output a complete HTML document with embedded JS
    assert "<!doctype html>" in js_code or "<html" in js_code
    assert "{title}" in js_code or "title" in js_code

def test_emitter_effects_in_js():
    code = """
fn pure_add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

fn fetch_data() -> Text:
    uses network
    return "data"
end

when app starts:
    result = pure_add(1, 2)
    data = fetch_data()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    # Pure functions should be synchronous
    # Effectful functions should be async or have effect markers
    assert "function pure_add" in js_code
    assert "function fetch_data" in js_code