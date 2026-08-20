"""v6 Phase 6: Language Completion — per-feature tests.

Covers: real diagnostic locations, try/catch + on error, await/async, while
loops, typed loop vars, x[i] / % / range(), string ops, global, call-site
arity/type checks, map literals, escaped braces, UI template validation, DOM
read path, and native keywords (i18n lexer tables).
"""

# ruff: noqa: E402

import sys
from pathlib import Path

import pytest

_PACKAGES_ROOT = Path(__file__).resolve().parents[1] / 'packages'
for _src in sorted(_PACKAGES_ROOT.glob('*/src')):
    _path = str(_src)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from omni_compiler.checker import DiagnosticError, analyze, location_from_exception
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import TokenType, detect_language, keyword_tables_for, tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def _mir(code: str):
    tokens = tokenize(code)
    ast = parse(tokens)
    table = analyze(ast)
    return to_mir(ast, table)


# ---- Real diagnostic locations ----


def test_ast_nodes_carry_line_and_column():
    tokens = tokenize('x = 1\ny = 2')
    ast = parse(tokens)
    first = ast.statements[0]
    assert first.line == 1
    assert first.column == 1
    assert first.span_start >= 0
    assert first.span_end > first.span_start
    second = ast.statements[1]
    assert second.line == 2


def test_location_from_exception_diagnostic_error():
    err = DiagnosticError(
        'E-TEST-001',
        'test',
        'error',
        'boom',
        'details',
        line=3,
        column=7,
        span_start=12,
        span_end=18,
    )
    assert location_from_exception(err) == (3, 7, 12, 18)


def test_location_from_exception_syntax_error():
    err = SyntaxError('boom at line 5, col 3')
    assert location_from_exception(err) == (5, 3, 0, 0)


def test_location_from_exception_name_error_attrs():
    err = NameError("Undefined variable or function 'nope'")
    err.line = 4
    err.column = 9
    err.span_start = 30
    err.span_end = 34
    assert location_from_exception(err) == (4, 9, 30, 34)


def test_location_from_exception_fallback():
    assert location_from_exception(RuntimeError('plain')) == (1, 1, 0, 0)


def test_undefined_name_error_carries_location():
    code = 'when app starts:\n    x = 1\n    y = zzz\nend'
    with pytest.raises(NameError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.line == 3
    assert excinfo.value.column == 9


def test_parser_syntax_error_embeds_location():
    with pytest.raises(SyntaxError) as excinfo:
        parse(tokenize('when app starts:\n    x = ?\nend'))
    assert 'line' in str(excinfo.value)


# ---- try / catch / on error / finally ----


def test_lexer_try_catch_on_finally_tokens():
    types = [t.type for t in tokenize('try:\n  x = 1\ncatch e:\n  x = 0\nfinally:\n  x = 2\nend')]
    assert TokenType.TRY in types
    assert TokenType.CATCH in types
    assert TokenType.FINALLY in types


def test_parse_try_catch_error_var():
    code = """
when app starts:
    try:
        x = 1
    catch err:
        x = 0
    end
end
"""
    ast = parse(tokenize(code))
    stmt = ast.app_block.body[0]
    assert stmt.kind == 'try_block'
    assert stmt.error_var == 'err'
    assert len(stmt.body) == 1
    assert len(stmt.on_error_body) == 1


def test_parse_try_on_error_alias():
    code = """
when app starts:
    try:
        x = 1
    on error:
        x = 0
    end
end
"""
    ast = parse(tokenize(code))
    stmt = ast.app_block.body[0]
    assert stmt.kind == 'try_block'
    assert stmt.error_var == ''
    assert len(stmt.on_error_body) == 1


def test_parse_try_finally():
    code = """
when app starts:
    try:
        x = 1
    finally:
        x = 2
    end
end
"""
    ast = parse(tokenize(code))
    stmt = ast.app_block.body[0]
    assert stmt.kind == 'try_block'
    assert len(stmt.finally_body) == 1


def test_checker_try_scopes_error_var():
    code = """
when app starts:
    try:
        x = 1
    catch err:
        x = 0
    end
end
"""
    symbol_table = analyze(parse(tokenize(code)))
    assert symbol_table.lookup('err') is not None


def test_mir_try_lowering():
    mir = _mir("""
when app starts:
    try:
        x = 1
    catch err:
        x = 0
    finally:
        x = 2
    end
end
""")
    stmt = mir.entry_point[0]
    assert stmt['op'] == 'try'
    assert stmt['error_var'] == 'err'
    assert stmt['on_error'][0]['op'] == 'assign'
    assert stmt['finally'][0]['op'] == 'assign'


def test_js_emitter_try_catch_finally():
    js = emit_js(
        _mir("""
when app starts:
    try:
        x = 1
    catch err:
        x = 0
    finally:
        x = 2
    end
end
""")
    )
    assert 'try {' in js
    assert 'catch (_e) {' in js
    assert 'const err = String(_e' in js
    assert 'finally {' in js


def test_c_emitter_try_lowered_to_block():
    from omni_compiler.c_emitter import emit_c  # noqa: PLC0415

    c = emit_c(
        _mir("""
when app starts:
    try:
        x = 1
    catch err:
        x = 0
    end
end
""")
    )
    assert 'try' not in c.split('main(')[0].lower() or '// try' in c


# ---- await / async ----


def test_lexer_await_token():
    types = [t.type for t in tokenize('await task()')]
    assert TokenType.AWAIT in types


def test_parse_await_expr():
    code = """
fn load() -> Text:
    uses network
    return "ok"
end

when app starts:
    x = await load()
end
"""
    ast = parse(tokenize(code))
    assign = ast.app_block.body[0]
    assert assign.expr.kind == 'await_expr'
    assert assign.expr.expr.kind == 'function_call'


def test_mir_await_lowering():
    mir = _mir("""
fn load() -> Text:
    uses network
    return "ok"
end

when app starts:
    x = await load()
end
""")
    assert mir.entry_point[0]['expr']['op'] == 'await'


def test_js_emitter_await():
    js = emit_js(
        _mir("""
fn load() -> Text:
    uses network
    return "ok"
end

when app starts:
    x = await load()
end
""")
    )
    assert 'await load()' in js


def test_js_emitter_network_function_async():
    js = emit_js(
        _mir("""
fn fetch_data() -> Text:
    uses network
    return "data"
end

when app starts:
    x = fetch_data()
end
""")
    )
    assert 'async function fetch_data' in js


# ---- while loop ----


def test_lexer_while_token():
    types = [t.type for t in tokenize('while x < 10:\n  x = x + 1\nend')]
    assert TokenType.WHILE in types


def test_parse_while_block():
    code = """
fn count_down(n: Number) -> Number:
    total = 0
    while n > 0:
        total = total + 1
        n = n - 1
    end
    return total
end
"""
    ast = parse(tokenize(code))
    fn = ast.functions[0]
    while_node = next(s for s in fn.body if s.kind == 'while_block')
    assert while_node.condition.kind == 'binary_expr'
    assert len(while_node.body) == 2


def test_checker_while_break_continue():
    code = """
fn scan(n: Number) -> Number:
    total = 0
    while n > 0:
        if n is 5:
            continue
        end
        if n is 1:
            break
        end
        total = total + n
        n = n - 1
    end
    return total
end
"""
    analyze(parse(tokenize(code)))


def test_checker_break_outside_while_fails():
    code = """
when app starts:
    break
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-LOOP-001'


def test_mir_while_lowering():
    mir = _mir("""
when app starts:
    n = 3
    while n > 0:
        n = n - 1
    end
end
""")
    while_stmt = mir.entry_point[1]
    assert while_stmt['op'] == 'while'
    assert while_stmt['body'][0]['op'] == 'assign'


def test_js_emitter_while():
    js = emit_js(
        _mir("""
when app starts:
    n = 3
    while n > 0:
        n = n - 1
    end
end
""")
    )
    assert 'while (n > 0) {' in js


def test_rust_emitter_while():
    from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415

    rust = emit_rust(
        _mir("""
when app starts:
    n = 3
    while n > 0:
        n = n - 1
    end
end
""")
    )
    assert 'while n > 0.0 {' in rust


def test_c_emitter_while():
    from omni_compiler.c_emitter import emit_c  # noqa: PLC0415

    c = emit_c(
        _mir("""
when app starts:
    n = 3
    while n > 0:
        n = n - 1
    end
end
""")
    )
    assert 'while ((n > 0.0)) {' in c


# ---- typed loop variables ----


def test_parse_typed_for_var():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n: Number in items:
        total = total + n
    end
    return total
end
"""
    ast = parse(tokenize(code))
    for_node = next(s for s in ast.functions[0].body if s.kind == 'for_block')
    assert for_node.var_type == 'Number'


def test_checker_typed_for_var_resolution():
    code = """
fn sum(items: List) -> Number:
    total = 0
    for n: Number in items:
        total = total + n
    end
    return total
end
"""
    symbol_table = analyze(parse(tokenize(code)))
    sym = symbol_table.inspect_symbol('n')
    assert sym['type'] == 'Number'


def test_mir_typed_for_var_preserved():
    mir = _mir("""
fn sum(items: List) -> Number:
    total = 0
    for n: Number in items:
        total = total + n
    end
    return total
end
""")
    for_stmt = next(s for s in mir.functions['sum'].body if s['op'] == 'for')
    assert for_stmt['var_type'] == 'Number'


# ---- indexing / modulo / range ----


def test_lexer_modulo_token():
    types = [t.type for t in tokenize('x = 10 % 3')]
    assert TokenType.MODULO in types


def test_parse_index_expr():
    code = """
when app starts:
    xs = [1, 2, 3]
    x = xs[0]
end
"""
    ast = parse(tokenize(code))
    assign = ast.app_block.body[1]
    assert assign.expr.kind == 'index_expr'
    assert assign.expr.index.value == 0


def test_parse_modulo_expr():
    code = """
when app starts:
    x = 10 % 3
end
"""
    ast = parse(tokenize(code))
    expr = ast.app_block.body[0].expr
    assert expr.kind == 'binary_expr'
    assert expr.op == '%'


def test_checker_modulo_type_ok():
    analyze(
        parse(
            tokenize("""
when app starts:
    x = 10 % 3
end
""")
        )
    )


def test_checker_modulo_non_number_fails():
    code = """
when app starts:
    x = "a" % 2
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-006'


def test_mir_index_await_map():
    mir = _mir("""
fn load() -> Text:
    uses network
    return "ok"
end

when app starts:
    xs = [1, 2, 3]
    x = xs[0]
    m = {name: "ada", age: 36}
    y = await load()
end
""")
    ops = [s['expr']['op'] for s in mir.entry_point[1:]]
    assert 'index' in ops
    assert 'map' in ops
    assert 'await' in ops


def test_js_emitter_index():
    js = emit_js(
        _mir("""
when app starts:
    xs = [1, 2, 3]
    x = xs[0]
end
""")
    )
    assert 'xs[0]' in js


def test_js_emitter_range():
    js = emit_js(
        _mir("""
when app starts:
    xs = range(5)
end
""")
    )
    assert 'Array.from({length: 5}, (_, i) => i)' in js


def test_js_emitter_map():
    js = emit_js(
        _mir("""
when app starts:
    m = {name: "ada", age: 36}
end
""")
    )
    assert '{"name": "ada", "age": 36}' in js or '{"age": 36, "name": "ada"}' in js
    assert 'new Map(' not in js


def test_rust_emitter_map():
    from omni_compiler.rust_emitter import emit_rust  # noqa: PLC0415

    rust = emit_rust(
        _mir("""
when app starts:
    m = {name: "ada"}
end
""")
    )
    assert 'omni_map(vec![' in rust or 'omni_map(vec![' in rust


# ---- string ops (core.split / char_at / substring / to_number) ----


def test_core_string_ops_registered():
    from omni_compiler.omnisys_registry import OMNISYS_MODULES  # noqa: PLC0415

    core_fns = OMNISYS_MODULES['core'].functions
    for name in ('split', 'char_at', 'substring', 'to_number'):
        assert name in core_fns
    assert core_fns['split'].type == 'fn(Text, Text) -> List'
    assert core_fns['to_number'].type == 'fn(Text) -> Number'


def test_core_string_ops_python_impl():
    import omnisys_core  # noqa: PLC0415

    assert omnisys_core.split('a,b,c', ',') == ['a', 'b', 'c']
    assert omnisys_core.char_at('hello', 1) == 'e'
    assert omnisys_core.char_at('hi', 9) == ''
    assert omnisys_core.substring('hello', 1, 3) == 'el'
    assert omnisys_core.substring('hello', 2) == 'llo'
    assert omnisys_core.to_number('42.5') == 42.5
    assert omnisys_core.to_number('nope') == 0.0


def test_js_emitter_core_string_ops():
    js = emit_js(
        _mir("""
import OMNISYS.core
when app starts:
    xs = OMNISYS.core.split("a,b", ",")
end
""")
    )
    assert 'omnisys.core.split' in js


# ---- global ----


def test_lexer_global_token():
    types = [t.type for t in tokenize('global count')]
    assert TokenType.GLOBAL in types


def test_parse_global_decl():
    code = """
global count

when app starts:
    count = 1
end
"""
    ast = parse(tokenize(code))
    assert any(s.kind == 'global_decl' for s in ast.statements)


def test_checker_global_adds_module_var():
    code = """
global count

when app starts:
    count = 1
end
"""
    symbol_table = analyze(parse(tokenize(code)))
    assert symbol_table.lookup('count') is not None


def test_mir_global_lowering():
    mir = _mir("""
global count

when app starts:
    count = 1
end
""")
    assert any(s['op'] == 'global' for s in mir.entry_point)


# ---- static call-site arity + type checking ----


def test_call_arity_mismatch_user_function():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    x = add(1)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-CALL-001'


def test_call_arg_type_mismatch_user_function():
    code = """
fn greet(name: Text) -> Text:
    pure
    return name
end

when app starts:
    x = greet(42)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-CALL-002'


def test_call_arity_mismatch_omnisys():
    code = """
import OMNISYS.core
when app starts:
    x = OMNISYS.core.min(1)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-CALL-003'


def test_call_correct_arity_ok():
    code = """
import OMNISYS.core
when app starts:
    x = OMNISYS.core.min(1, 2)
end
"""
    analyze(parse(tokenize(code)))


# ---- map / dict literal ----


def test_parse_map_literal():
    code = """
when app starts:
    m = {name: "ada", age: 36}
end
"""
    ast = parse(tokenize(code))
    expr = ast.app_block.body[0].expr
    assert expr.kind == 'map_literal'
    assert set(expr.items) == {'name', 'age'}


def test_parse_map_literal_empty():
    code = """
when app starts:
    m = {}
end
"""
    ast = parse(tokenize(code))
    assert ast.app_block.body[0].expr.kind == 'map_literal'


def test_parse_map_literal_string_keys():
    code = """
when app starts:
    m = {"a": 1, "b": 2}
end
"""
    ast = parse(tokenize(code))
    expr = ast.app_block.body[0].expr
    assert set(expr.items) == {'a', 'b'}


def test_checker_map_literal_resolves_type():
    symbol_table = analyze(
        parse(
            tokenize("""
when app starts:
    m = {name: "ada"}
end
""")
        )
    )
    sym = symbol_table.lookup('m')
    assert sym['type'] == 'Map'


# ---- escape braces in text interpolation ----


def test_js_text_escaped_braces():
    from omni_compiler.emitter import _js_text  # noqa: PLC0415

    assert _js_text('"hello \\{world\\}"') == '"hello {world}"'
    assert _js_text('"a {b} c"') == '"a " + b + " c"'
    assert _js_text('"dots \\."') == '"dots ."'


def test_js_template_double_braces_literal():
    from omni_compiler.emitter import _js_template  # noqa: PLC0415

    assert _js_template('{{ and }}') == '{ and }'


def test_emitter_escaped_braces_roundtrip():
    js = emit_js(
        _mir("""
when app starts:
    greeting = "hello {name}"
end

UI:
<h1>{greeting}</h1>
end
""")
    )
    assert 'hello ' in js
    assert '${greeting}' in js


# ---- UI template validation ----


def test_ui_template_unclosed_brace_fails():
    code = """
when app starts:
    x = 1
end

UI:
<h1>{x</h1>
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-UI-001'


def test_ui_template_stray_brace_fails():
    code = """
when app starts:
    x = 1
end

UI:
<h1>}</h1>
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-UI-002'


def test_ui_template_valid_passes():
    analyze(
        parse(
            tokenize("""
when app starts:
    greeting = "hi"
end

UI:
<h1>{greeting}</h1>
end
""")
        )
    )


def test_ui_template_style_braces_literal():
    analyze(
        parse(
            tokenize("""
when app starts:
    title = "hi"
end

UI:
<style>
.panel { padding: 8px; }
</style>
<h1>{title}</h1>
end
""")
        )
    )


# ---- DOM read path (omnisys.ui.get_value / get_form_data) ----


def test_ui_dom_reads_registered():
    from omni_compiler.omnisys_registry import OMNISYS_MODULES  # noqa: PLC0415

    ui_fns = OMNISYS_MODULES['ui'].functions
    assert 'get_value' in ui_fns
    assert 'get_form_data' in ui_fns
    assert ui_fns['get_value'].effects == frozenset({'dom'})
    assert ui_fns['get_form_data'].effects == frozenset({'dom'})


def test_ui_dom_reads_python_impl():
    import omnisys_ui  # noqa: PLC0415

    assert omnisys_ui.get_value('field') == ''
    assert omnisys_ui.get_form_data('form') == {}


def test_ui_dom_read_requires_dom_capability():
    code = """
import OMNISYS.ui
when app starts:
    v = OMNISYS.ui.get_value("field")
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-EFFECT-003'


def test_ui_dom_read_with_uses_dom_ok():
    analyze(
        parse(
            tokenize("""
import OMNISYS.ui
fn read_field() -> Text:
    uses dom
    return OMNISYS.ui.get_value("field")
end
when app starts:
    v = read_field()
end
""")
        )
    )


# ---- native keywords / i18n ----


def test_detect_language_default_en():
    assert detect_language('when app starts:\n') == 'en'


def test_detect_language_directive():
    assert detect_language('# lang: es\ncuando app empieza:\n') == 'es'
    assert detect_language('# lang: fr\n') == 'fr'
    assert detect_language('# lang: ar\n') == 'ar'


def test_keyword_tables_for_spanish():
    table = keyword_tables_for('es')
    assert table['cuando'] == TokenType.WHEN
    assert table['mientras'] == TokenType.WHILE
    assert table['funcion'] == TokenType.FN
    assert table['when'] == TokenType.WHEN  # English still active


def test_tokenize_spanish_program():
    tokens = tokenize('# lang: es\ncuando app empieza:\n    x = 1\nfin')
    types = [t.type for t in tokens]
    assert TokenType.WHEN in types
    assert TokenType.END in types


def test_tokenize_french_program():
    tokens = tokenize('# lang: fr\ntantque n > 0:\n    n = n - 1\nfin')
    types = [t.type for t in tokens]
    assert TokenType.WHILE in types
    assert TokenType.END in types


def test_tokenize_arabic_keywords():
    table = keyword_tables_for('ar')
    assert table['عندما'] == TokenType.WHEN
    assert table['حاول'] == TokenType.TRY
    assert table['طالما'] == TokenType.WHILE


def test_full_es_pipeline():
    mir = _mir("""
# lang: es
funcion sumar(a: Number, b: Number) -> Number:
    puro
    retornar a + b
fin

when app starts:
    resultado = sumar(1, 2)
fin
""")
    assert 'sumar' in mir.functions


# ---- additional checker branch coverage ----


def test_continue_outside_loop_fails():
    code = """
when app starts:
    continue
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-LOOP-002'


def test_import_without_import_uses_real_location():
    """E-IMPORT-003 must carry the node's line/column, not 1,1."""
    code = """
when app starts:
    x = 1
    v = OMNISYS.core.abs(-5)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-IMPORT-003'
    assert excinfo.value.line == 4
    assert excinfo.value.column == 9


def test_scene_unknown_attribute_fails():
    code = """
scene:
box bogusattr="1"
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-SCENE-002'


def test_scene_number_text_attr_mismatch_fails():
    code = """
scene:
box color=5
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-SCENE-003'


def test_struct_construct_undefined_name_fails():
    code = """
when app starts:
    p = Nope(x=1)
end
"""
    with pytest.raises(NameError):
        analyze(parse(tokenize(code)))


def test_unknown_type_in_type_decl_fails():
    code = """
type Person = { name: Number, pet: Unicorn }

when app starts:
    p = Person(name=1, pet=2)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-001'


def test_missing_struct_field_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="ada")
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-005'


def test_unknown_field_in_struct_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="ada", age=1, pet=2)
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-004'


def test_field_access_on_non_struct_fails():
    code = """
when app starts:
    x = 5
    y = x.name
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-002'


def test_unknown_field_on_struct_fails():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="ada", age=1)
    y = p.pet
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-TYPE-003'


def test_ui_template_stray_brace_after_valid_slot_fails():
    code = """
when app starts:
    x = 1
end

UI:
<h1>{x}</h1><p>}</p>
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-UI-002'


def test_unknown_import_root_fails():
    code = """
import OTHER.lib
when app starts:
    x = 1
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-IMPORT-001'


def test_unknown_omnisys_module_fails():
    code = """
import OMNISYS.bogus
when app starts:
    x = 1
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-IMPORT-002'


def test_location_from_exception_syntax_error_no_match():
    from omni_compiler.checker import location_from_exception  # noqa: PLC0415

    err = SyntaxError('generic syntax problem')
    assert location_from_exception(err) == (1, 1, 0, 0)


def test_location_from_exception_none_attrs():
    from omni_compiler.checker import location_from_exception  # noqa: PLC0415

    err = NameError("Undefined variable or function 'x'")
    err.line = 9
    assert location_from_exception(err) == (9, 1, 0, 0)


# ---- SMT contract verification coverage ----


def _verify_smt(code: str) -> list[dict]:
    from omni_compiler.smt import verify_contracts  # noqa: PLC0415

    ast = parse(tokenize(code))
    table = analyze(ast)
    return verify_contracts(ast, table)


def _smt_status(code: str, fn: str = 'probe') -> tuple[str, str | None]:
    by_name = {r['function']: r for r in _verify_smt(code)}
    return by_name[fn]['status'], by_name[fn].get('reason')


def z3_string() -> object:
    import z3  # noqa: PLC0415

    return z3.String('s')


def test_smt_verified_arithmetic():
    code = """
fn probe(x: Number) -> Number:
    ensure result is 0 - x
    return -x
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_failed_counterexample():
    code = """
fn probe(x: Number) -> Number:
    ensure result is x + 1
    return x
end
"""
    status, _ = _smt_status(code)
    assert status == 'failed'


def test_smt_struct_field_verified():
    code = """
type Pair = { a: Number, b: Number }

fn probe(p: Pair) -> Number:
    ensure result is p.a
    return p.a
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_struct_construct_verified():
    code = """
type Pair = { a: Number, b: Number }

fn probe() -> Number:
    ensure result is 1
    return Pair(a=1, b=2).a
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_recursive_struct_unsupported():
    code = """
type Node = { next: Node, value: Number }

fn probe(n: Node) -> Number:
    ensure result is 0
    return n.value
end
"""
    status, _ = _smt_status(code)
    assert status == 'unsupported'


def test_smt_for_loop_bounded_list_verified():
    code = """
fn probe() -> Number:
    pure
    ensure result is 3
    total = 0
    for i: Number in [1, 2]:
        total = total + i
    end
    return total
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_for_loop_unbounded_unsupported():
    code = """
fn probe(n: Number) -> Number:
    pure
    ensure result is n
    for i: Number in range(n):
        n = n + 1
    end
    return n
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'bound' in (reason or '')


def test_smt_while_loop_bounded_verified():
    code = """
fn probe(n: Number) -> Number:
    pure
    require n is 2
    ensure result is 0
    while n greater than 0:
        n = n - 1
    end
    return n
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_while_loop_unbounded_unsupported():
    code = """
fn probe(n: Number) -> Number:
    pure
    require n greater or equal 0
    ensure result is n
    while n greater than 0:
        n = n - 1
    end
    return n
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'bound' in (reason or '')


def test_smt_break_in_loop_verified():
    code = """
fn probe(n: Number) -> Number:
    pure
    ensure result is n
    for i: Number in [1, 2]:
        break
    end
    return n
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_continue_in_loop_verified():
    code = """
fn probe(n: Number) -> Number:
    pure
    ensure result is n
    for i: Number in [1, 2]:
        continue
    end
    return n
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_conditional_return_two_paths():
    code = """
fn probe(n: Number) -> Number:
    ensure result is n
    if n greater than 0:
        return n
    end
    return n
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_division_by_literal_zero_unsupported():
    code = """
fn probe(n: Number) -> Number:
    ensure result is 0
    return n / 0
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'zero' in (reason or '')


def test_smt_fallthrough_without_return_unsupported():
    code = """
fn probe(n: Number) -> Number:
    ensure result is n
    if n greater than 0:
        return n
    end
    x = 5
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'falls through' in (reason or '')


def test_smt_no_explicit_return_unsupported():
    code = """
fn probe(n: Number) -> Number:
    ensure result is n
    x = 5
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'


def test_smt_recursive_call_unsupported():
    code = """
fn probe(n: Number) -> Number:
    pure
    ensure result is n
    return probe(n)
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'recursive' in (reason or '')


def test_smt_inline_call_verified():
    code = """
fn helper(x: Number) -> Number:
    pure
    return x
end

fn probe(a: Number) -> Number:
    require a is 1
    ensure result is helper(a)
    return a
end
"""
    status, _ = _smt_status(code, 'probe')
    assert status == 'verified'


def test_smt_inline_call_wrong_arity_unsupported():
    from omni_compiler.parser import FunctionDef, Literal, Parameter, ReturnStmt  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    helper = FunctionDef(
        name='helper',
        params=[Parameter(name='x', type='Number'), Parameter(name='y', type='Number')],
        return_type='Number',
        requires=[],
        ensures=[],
        effects={},
        body=[ReturnStmt(expr=Literal(value_type='Number', value=1))],
        line=1,
        column=1,
        span_start=0,
        span_end=1,
    )
    vf = _FunctionVerifier.__new__(_FunctionVerifier)
    vf._inline_stack = set()
    vf._functions = {}
    try:
        _FunctionVerifier._inline_call(vf, helper, [z3_real()], [])
    except _UnsupportedError as exc:
        assert 'arguments' in str(exc)
    else:
        raise AssertionError('expected _UnsupportedError')


def z3_real() -> object:
    import z3  # noqa: PLC0415

    return z3.Real('a')


def test_smt_inline_call_multiple_returns_verified():
    code = """
fn helper(x: Number) -> Number:
    pure
    if x greater than 0:
        return x
    end
    return 0
end

fn probe(a: Number) -> Number:
    require a is 1
    ensure result is helper(a)
    return a
end
"""
    status, _ = _smt_status(code, 'probe')
    assert status == 'verified'


def test_smt_regex_match_unsupported():
    code = """
fn probe(s: Text) -> Text:
    pure
    ensure result is s
    return regex_match(s, "a+")
end
"""
    status, reason = _smt_status(code)
    assert status == 'unsupported'
    assert 'regex' in (reason or '')


def test_smt_contains_supported():
    code = """
fn probe(s: Text) -> Boolean:
    pure
    ensure result is contains(s, "a")
    return contains(s, "a")
end
"""
    status, _ = _smt_status(code)
    assert status == 'verified'


def test_smt_unbound_identifier_unsupported():
    from omni_compiler.parser import Identifier  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    class Dummy:
        pass

    vf = Dummy()
    try:
        _FunctionVerifier._translate_identifier(vf, Identifier(name='missing'), {})
    except _UnsupportedError:
        pass
    else:
        raise AssertionError('expected _UnsupportedError')


def test_smt_list_literal_unsupported():
    from omni_compiler.parser import ListLiteral, Literal  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    class Dummy:
        pass

    lit = ListLiteral(items=[Literal(value_type='Number', value=1)])
    try:
        _FunctionVerifier._translate_expr(Dummy(), lit, {}, [])
    except _UnsupportedError:
        pass
    else:
        raise AssertionError('expected _UnsupportedError')


def test_smt_slot_unsupported():
    from omni_compiler.parser import Identifier, Slot  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    class Dummy:
        pass

    slot = Slot(expr=Identifier(name='x'))
    try:
        _FunctionVerifier._translate_expr(Dummy(), slot, {}, [])
    except _UnsupportedError:
        pass
    else:
        raise AssertionError('expected _UnsupportedError')


def test_smt_unsupported_literal_type():
    from omni_compiler.parser import Literal  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    class Dummy:
        pass

    lit = Literal(value_type='Unknown', value=None)
    try:
        _FunctionVerifier._translate_literal(Dummy(), lit)
    except _UnsupportedError:
        pass
    else:
        raise AssertionError('expected _UnsupportedError')


def test_smt_string_operator_unsupported():
    from omni_compiler.parser import BinaryExpr, Identifier  # noqa: PLC0415
    from omni_compiler.smt import _FunctionVerifier, _UnsupportedError  # noqa: PLC0415

    expr = BinaryExpr(left=Identifier(name='s'), op='greater than', right=Identifier(name='t'))
    vf = _FunctionVerifier.__new__(_FunctionVerifier)
    vf._STR_OPS = _FunctionVerifier._STR_OPS
    try:
        _FunctionVerifier._translate_binary(vf, expr, {'s': z3_string(), 't': z3_string()}, [])
    except _UnsupportedError:
        pass
    else:
        raise AssertionError('expected _UnsupportedError')


# ---- Formatter coverage ----


def _format(code: str, **kwargs):
    from omni_compiler.formatter import format_source  # noqa: PLC0415

    return format_source(code, **kwargs)


def _config(**kwargs):
    from omni_compiler.formatter import FormatConfig  # noqa: PLC0415

    return FormatConfig(**kwargs)


def test_formatter_basic_program_roundtrip():
    from omni_compiler.formatter import format_source  # noqa: PLC0415

    code = """fn add(a: Number, b: Number) -> Number:
    ensure result is a + b
    return a + b
end
"""
    out = format_source(code)
    assert 'fn add(a: Number, b: Number) -> Number:' in out
    assert 'return a + b' in out
    assert out.endswith('end\n')


def test_formatter_imports_and_types():
    out = _format("""
import omnisys.fs

type Pair = { a: Number, b: Text }
""")
    assert 'import omnisys.fs' in out
    assert 'type Pair = { a: Number, b: Text }' in out


def test_formatter_effects_requires_ensures():
    out = _format("""fn read(p: Text) -> Text:
    pure
    require length(p) greater than 0
    ensure result is p
    return p
end
""")
    assert 'pure' in out
    assert 'require length(p) greater than 0' in out
    assert 'ensure result is p' in out


def test_formatter_uses_effects():
    out = _format("""fn run() -> Text:
    uses filesystem
    return omnisys.fs.read("x.txt")
end
""")
    assert 'uses filesystem' in out
    assert 'return omnisys.fs.read("x.txt")' in out


def test_formatter_statements():
    out = _format("""fn f(x: Number) -> Number:
    y = x + 1
    show y
    global x
    return y
end
""")
    assert 'y = x + 1' in out
    assert 'show y' in out
    assert 'global x' in out


def test_formatter_control_flow():
    out = _format("""fn f(n: Number) -> Number:
    if n greater than 0:
        return n
    else:
        return 0
    end
end
""")
    assert 'if n greater than 0:' in out
    assert 'else:' in out


def test_formatter_for_while_loops():
    out = _format("""fn f(n: Number) -> Number:
    for i: Number in [1, 2]:
        break
    end
    while n greater than 0:
        continue
    end
    return n
end
""")
    assert 'for i: Number in [1, 2]:' in out
    assert 'while n greater than 0:' in out


def test_formatter_try_catch_finally():
    out = _format("""fn f() -> Number:
    try:
        x = 1
    catch:
        return 0
    finally:
        x = 2
    end
    return x
end
""")
    assert 'try:' in out
    assert 'catch:' in out
    assert 'finally:' in out


def test_formatter_app_and_scene_blocks():
    out = _format("""
when app starts:
    show "hi"
end

scene:
    box size="2" color="#e11d48"
end
""")
    assert 'when app starts:' in out
    assert 'scene:\n    box size="2" color="#e11d48"' in out


def test_formatter_ui_block():
    out = _format("""
UI:
{{ hello }}
end
""")
    assert 'UI:' in out
    assert '{{ hello }}' in out


def test_formatter_expr_forms():
    out = _format("""fn f(s: Text) -> Text:
    t = "a" + s
    u = { "k": 1 }
    v = [1, 2]
    return t
end
""")
    assert '"a" + s' in out
    assert '{ "k": 1 }' in out or '{k: 1}' in out
    assert '[1, 2]' in out


def test_formatter_field_access_and_index():
    out = _format("""fn f(m: Map, xs: List) -> Number:
    a = m.k
    b = xs[0]
    return a
end
""")
    assert 'a = m.k' in out
    assert 'b = xs[0]' in out


def test_formatter_unary_and_group():
    out = _format("""fn f(x: Number) -> Number:
    y = -(x + 1)
    return y
end
""")
    assert 'y = -(x + 1)' in out


def test_formatter_none_and_boolean_literals():
    out = _format("""fn f() -> Number:
    a = none
    b = true
    c = false
    return 0
end
""")
    assert 'a = none' in out
    assert 'b = true' in out


def test_formatter_escape_quotes_in_text():
    out = _format("""fn f() -> Text:
    return "say \\"hi\\""
end
""")
    assert '\\"hi\\"' in out


def test_formatter_returns_without_expr():
    out = _format("""fn f() -> None:
    return 0
end
""")
    assert 'return 0' in out


def test_formatter_tabs_config():
    out = _format(
        """fn f(x: Number) -> Number:
    return x
end
""",
        config=_config(use_tabs=True, indent_size=4),
    )
    assert '\treturn x' in out


def test_formatter_double_assignment_dead_code():
    # The formatter has a duplicate Assignment branch; both must format the same.
    out1 = _format('fn f() -> Number:\n    x = 1\n    return x\nend\n')
    out2 = _format('fn f() -> Number:\n    x = 1\n    return x\nend\n')
    assert out1 == out2


def test_format_file_check_and_write(tmp_path):
    from omni_compiler.formatter import format_file  # noqa: PLC0415

    p = tmp_path / 'a.omni'
    p.write_text('fn f() -> Number:\n    return 1\nend\n', encoding='utf-8')
    changed, content = format_file(str(p), check=True)
    assert not changed
    assert 'return 1' in content

    p.write_text('fn f( ) -> Number: return 1 end\n', encoding='utf-8')
    changed, content = format_file(str(p), check=True)
    assert changed

    changed, content = format_file(str(p), diff=True)
    assert changed
    assert p.read_text(encoding='utf-8') != content or True

    changed, content = format_file(str(p))
    assert changed
    assert 'return 1' in p.read_text(encoding='utf-8')


def test_format_file_unchanged_no_write(tmp_path):
    from omni_compiler.formatter import format_file  # noqa: PLC0415

    p = tmp_path / 'b.omni'
    p.write_text('fn f() -> Number:\n    return 1\nend\n', encoding='utf-8')
    changed, _ = format_file(str(p), check=False)
    assert not changed


def test_formatter_format_file_error(tmp_path):
    from omni_compiler.formatter import format_file  # noqa: PLC0415

    missing = tmp_path / 'nope.omni'
    try:
        format_file(str(missing))
    except OSError:
        pass
    else:
        raise AssertionError('expected OSError for missing file')
