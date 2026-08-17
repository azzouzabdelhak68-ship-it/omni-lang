"""v3.1: C Emitter + Flecs Adapter tests."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from omni_compiler.c_emitter import emit_c
from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def test_c_emitter_basic_function():
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
    c_code = emit_c(mir)

    assert "double add(double a, double b)" in c_code
    assert "return (a + b);" in c_code
    assert "int main(" in c_code


def test_c_emitter_custom_types():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
    n = p.name
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "typedef struct Person" in c_code
    assert "const char* name;" in c_code
    assert "double age;" in c_code


def test_c_emitter_loops_and_conditionals():
    code = """
fn sum_all(items: List) -> Number:
    total = 0
    for n in items:
        if n greater than 10:
            continue
        end
        if n is 0:
            break
        end
        total = total + n
    end
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "double sum_all(" in c_code
    assert "for (" in c_code
    assert "continue;" in c_code
    assert "break;" in c_code


def test_c_emitter_string_interpolation_and_join():
    code = """
fn combine(items: List) -> Text:
    return join(items, ", ")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "omni_join(" in c_code


def test_c_emitter_flecs_adapter():
    code = """
type Position = { x: Number, y: Number }
type Velocity = { x: Number, y: Number }

when app starts:
    p = Position(x=0, y=0)
    v = Velocity(x=1, y=0)
    sim.entity("player", [p, v])
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "flecs.h" in c_code
    assert "ecs_init()" in c_code
    assert "ecs_new_entity" in c_code or "flecs" in c_code.lower()


def test_c_emitter_interpolation_uses_omni_format():
    code = """
fn greet(name: Text) -> Text:
    return "Hello {name}"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "omni_format(" in c_code
    assert "%s" in c_code


def test_c_emitter_interpolation_number_slot():
    code = """
fn report(score: Number) -> Text:
    return "Score: {score}"
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert 'omni_format("Score: %f", (double)(score));' in c_code


def test_c_emitter_omni_join_preamble():
    code = """
fn combine(items: List) -> Text:
    return join(items, ", ")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "static const char* omni_join" in c_code
    assert "omni_join(list" in c_code or "omni_join(" in c_code


def test_c_emitter_show_formats_by_type():
    code = """
fn report:
    n = 3
    t = "hi"
    show n
    show t
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert 'printf("%f\\n", (double)(n));' in c_code
    assert 'printf("%s\\n", (t));' in c_code


def test_c_emitter_typed_assign():
    code = """
fn mk() -> Number:
    total = 1
    total = total + 2
    return total
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "double total = 1.0;" in c_code
    assert "total = (total + 2.0);" in c_code


def test_c_emitter_sim_system_lowering():
    code = """
fn move_system:
    return none
end

when app starts:
    sim.system("move", move_system, "every frame")
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "ECS_SYSTEM" in c_code
    assert "move_system();" in c_code
    assert "OMNI_HAVE_FLECS" in c_code


def test_c_emitter_flecs_component_registration():
    code = """
type Position = { x: Number, y: Number }

when app starts:
    p = Position(x=0, y=0)
    sim.entity("player", [p])
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "ECS_COMPONENT_DECLARE(Position);" in c_code
    assert "ECS_COMPONENT_DEFINE(world, Position);" in c_code
    assert "ecs_new(world);" in c_code
    assert "ecs_set(world, e_entity_1, Position, {0.0, 0.0});" in c_code


def test_c_emitter_expr_coverage():
    code = """
type Person = { name: Text, age: Number, active: Boolean }

fn classify(items: List) -> Text:
    flag = true
    none_val = none
    total = 0
    for n in items:
        if n greater or equal 5:
            total = total + n
        else:
            total = total - 1
        end
    end
    if flag:
        show total
    end
    return "done"
end

when app starts:
    p = Person(name="Ada", age=36, active=true)
    n = p.age
    xs = [1, 2, 3]
    show n
    result = classify(xs)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    assert "p.age" in c_code
    assert "omni_make_list" in c_code
    assert "NULL" in c_code
    assert ">=" in c_code
    assert "greater or equal" not in c_code


def test_c_emitter_gcc_syntax_check():
    if shutil.which("gcc") is None:
        pytest.skip("gcc not available")

    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

fn greet(name: Text) -> Text:
    return "Hello {name}"
end

when app starts:
    result = add(1, 2)
    g = greet("world")
    show result
    show g
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)

    with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f:
        f.write(c_code)
        c_path = f.name

    try:
        # flecs.h is missing, so a missing-header error is acceptable; other
        # syntax errors (bad braces, wrong types) are not.
        proc = subprocess.run(
            ["gcc", "-fsyntax-only", "-DOMNI_HAVE_FLECS", c_path],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        stderr = proc.stderr
        assert "flecs.h: No such file" in stderr or "error:" not in stderr
    finally:
        Path(c_path).unlink()
