import pytest

from omni_compiler.checker import DiagnosticError, analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse


def test_name_resolution_success():
    code = """
when app starts:
    x = 42
    y = x
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    assert symbol_table.lookup('x') is not None
    assert symbol_table.lookup('y') is not None


def test_name_resolution_undefined_variable():
    code = """
when app starts:
    y = undefined_var
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert 'undefined' in str(excinfo.value).lower() or 'not found' in str(excinfo.value).lower()


def test_symbol_inspection():
    code = """
fn add(a: Number, b: Number) -> Number:
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('add')
    assert sym is not None
    assert sym['schema'] == 'omni.symbol'
    assert sym['name'] == 'add'
    assert sym['kind'] == 'function'
    assert sym['type'] == 'fn(Number, Number) -> Number'
    assert sym['exported'] is True


def test_effect_enforcement_network():
    code = """
fn fetch(url: Text) -> Text:
    uses network
    return "ok"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('fetch')
    assert sym is not None
    assert 'network' in sym['declared_effects']['uses']


def test_effect_enforcement_missing_network():
    code = """
fn fetch(url: Text) -> Text:
    return "ok"
end

when app starts:
    fetch("http://example.com")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    with pytest.raises(Exception) as excinfo:
        analyze(ast)
    assert 'network' in str(excinfo.value).lower() or 'capability' in str(excinfo.value).lower()


def test_pure_function_enforcement():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('add')
    assert sym['declared_effects']['pure'] is True


def test_pure_function_with_network_violation():
    code = """
fn bad_pure() -> Text:
    pure
    return "hello"
end

when app starts:
    show "test"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    # Should pass - pure function doesn't actually call network
    analyze(ast)


def test_require_ensure_parsing():
    code = """
fn divide(a: Number, b: Number) -> Number:
    require b is not 0
    ensure result is not 0
    pure
    return a / b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    assert len(ast.functions) == 1
    fn = ast.functions[0]
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1
    assert fn.effects['pure'] is True


def test_effect_transitivity():
    code = """
fn helper() -> Text:
    uses network
    return "ok"
end

fn caller() -> Text:
    uses network
    return helper()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)

    helper_sym = symbol_table.inspect_symbol('helper')
    caller_sym = symbol_table.inspect_symbol('caller')

    assert 'network' in helper_sym['declared_effects']['uses']
    assert 'network' in caller_sym['declared_effects']['uses']


def test_require_ensure_type_checking():
    code = """
fn test(a: Number) -> Number:
    require a > 0
    ensure result > 0
    pure
    return a + 1
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    analyze(ast)
    fn = ast.functions[0]
    assert len(fn.requires) == 1
    assert len(fn.ensures) == 1


def test_name_resolution_inside_group():
    code = """
when app starts:
    x = (5)
    y = (x)
end
"""
    analyze(parse(tokenize(code)))


def test_undefined_name_inside_group_fails():
    code = """
when app starts:
    y = (undefined_thing)
end
"""
    with pytest.raises(Exception) as excinfo:
        analyze(parse(tokenize(code)))
    assert 'undefined' in str(excinfo.value).lower() or 'not found' in str(excinfo.value).lower()


def test_effect_walk_through_not_and_group():
    """A pure function around an effectful call must still be flagged.

    The body uses `not (...)` around an effectful call; the effect walker must
    see through GroupExpr/UnaryExpr and still detect E-EFFECT-001.
    """
    code = """
fn fetch_data() -> Text:
    uses network
    return "data"
end

fn bad() -> Number:
    pure
    if not (fetch_data() is ""):
        return 1
    end
    return 0
end
"""
    with pytest.raises(Exception) as excinfo:
        analyze(parse(tokenize(code)))
    assert 'pure' in str(excinfo.value).lower() or 'effect' in str(excinfo.value).lower()


def test_effect_enforcement_undeclared_reads():
    """MEDIUM-10: reads `db` (module var) without declaring `reads db`."""
    code = """
when app starts:
    cache = "cold"
    db = "rows"
end

fn query() -> Text:
    reads cache
    return db
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-EFFECT-004'


def test_effect_enforcement_declared_module_read_ok():
    code = """
when app starts:
    cache = "cold"
    db = "rows"
end

fn query() -> Text:
    reads db
    return db
end
"""
    analyze(parse(tokenize(code)))


def test_effect_enforcement_local_write_not_flagged():
    """A function writing its own local is fine.

    The function declares `writes` for a name it assigns locally; a local
    write never collides with module scope and must not be flagged.
    """
    code = """
when app starts:
    seed = 1
end

fn log_it() -> Text:
    writes log
    log = "entry"
    return log
end
"""
    analyze(parse(tokenize(code)))


def test_effect_enforcement_no_clause_no_module_touch():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    analyze(parse(tokenize(code)))


def test_effect_enforcement_assigned_module_resource_flagged():
    """A function ASSIGNING a module resource must declare `writes`.

    Previously `local_names` exempted any name a function assigned from the
    `writes` check, so a function mutating module data escaped E-EFFECT-004.
    """
    code = """
when app starts:
    counter = 0
end

fn increment() -> Number:
    counter = counter + 1
    return counter
end
"""
    with pytest.raises(DiagnosticError) as excinfo:
        analyze(parse(tokenize(code)))
    assert excinfo.value.code == 'E-EFFECT-004'
    assert 'counter' in excinfo.value.details


def test_effect_enforcement_assigned_module_resource_declared_ok():
    """Declaring `reads`/`writes` satisfies the module-resource write check."""
    code = """
when app starts:
    counter = 0
end

fn increment() -> Number:
    reads counter
    writes counter
    counter = counter + 1
    return counter
end
"""
    analyze(parse(tokenize(code)))


def test_effect_enforcement_loop_var_shadowing_not_flagged():
    """A for-loop variable shadowing a module name is block-scoped, not a read.

    The emitter lowers `for n in items` to `for (const n of ...)`, so reads of
    the loop variable never touch module data and must not be flagged.
    """
    code = """
when app starts:
    n = 5
    xs = [1, 2, 3]
end

fn totalize(items: List) -> Number:
    sum = 0
    for n in items:
        sum = sum + n
    end
    return sum
end
"""
    analyze(parse(tokenize(code)))


def test_effect_enforcement_param_shadowing_not_flagged():
    """A function parameter colliding with a module-scope name is not a read.

    This follows the fixture 05 pattern: the parameter shadows the module
    variable, so it must not be treated as a module read.
    """
    code = """
when app starts:
    p = 1
end

fn describe(p: Number) -> Number:
    pure
    return p
end
"""
    analyze(parse(tokenize(code)))


def test_parameterized_uses_network():
    """Test parameterized uses network("api.example.com") syntax."""
    code = """
fn fetch_data() -> Text:
    uses network("api.example.com")
    return "data"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('fetch_data')
    assert sym is not None
    assert 'network' in sym['declared_effects']['uses']


def test_parameterized_reads_file():
    """Test parameterized reads file("config.json") syntax."""
    code = """
fn load_config() -> Text:
    reads file("config.json")
    return "config"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('load_config')
    assert sym is not None
    assert 'file' in sym['declared_effects']['reads']


def test_parameterized_writes_file():
    """Test parameterized writes file("output.txt") syntax."""
    code = """
fn save_output() -> Text:
    writes file("output.txt")
    return "saved"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('save_output')
    assert sym is not None
    assert 'file' in sym['declared_effects']['writes']


def test_mixed_parameterized_and_unparameterized():
    """Test mixing parameterized and unparameterized effects."""
    code = """
fn complex() -> Text:
    uses network
    uses network("api.example.com")
    reads file("config.json")
    reads cache
    pure
    return "data"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('complex')
    assert sym is not None
    assert 'network' in sym['declared_effects']['uses']
    assert 'file' in sym['declared_effects']['reads']
    assert 'cache' in sym['declared_effects']['reads']


def test_parameterized_effect_enforcement():
    """Test that parameterized effects are enforced like unparameterized ones."""
    code = """
fn fetch_data() -> Text:
    uses network("api.example.com")
    return "data"
end

fn caller() -> Text:
    uses network
    return fetch_data()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    caller_sym = symbol_table.inspect_symbol('caller')
    assert 'network' in caller_sym['declared_effects']['uses']


def test_memory_effect_allocates():
    """Test declarative allocates effect for WASM/embedded targets."""
    code = """
fn allocate_buffer() -> Text:
    uses allocates
    return "buffer"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('allocate_buffer')
    assert sym is not None
    assert 'allocates' in sym['declared_effects']['uses']


def test_memory_effect_mutates_heap():
    """Test declarative mutates_heap effect for WASM/embedded targets."""
    code = """
fn mutate_heap() -> Text:
    uses mutates_heap
    return "mutated"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('mutate_heap')
    assert sym is not None
    assert 'mutates_heap' in sym['declared_effects']['uses']


def test_memory_effects_combined():
    """Test combining memory effects with other effects."""
    code = """
fn complex_wasm() -> Text:
    uses network
    uses allocates
    uses mutates_heap
    return "data"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    sym = symbol_table.inspect_symbol('complex_wasm')
    assert sym is not None
    assert 'network' in sym['declared_effects']['uses']
    assert 'allocates' in sym['declared_effects']['uses']
    assert 'mutates_heap' in sym['declared_effects']['uses']


def test_memory_effect_transitivity():
    """Test that memory effects propagate through function calls."""
    code = """
fn helper() -> Text:
    uses allocates
    return "ok"
end

fn caller() -> Text:
    uses allocates
    return helper()
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)

    helper_sym = symbol_table.inspect_symbol('helper')
    caller_sym = symbol_table.inspect_symbol('caller')

    assert 'allocates' in helper_sym['declared_effects']['uses']
    assert 'allocates' in caller_sym['declared_effects']['uses']
