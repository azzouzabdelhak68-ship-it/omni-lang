"""v3.2: Rust Emitter + Bevy Adapter tests."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse
from omni_compiler.rust_emitter import emit_rust, emit_rust_with_runtime


def _emit(code: str) -> str:
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    return emit_rust(mir)


def test_rust_emitter_basic_function():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
end
"""
    rust = _emit(code)

    assert "fn add(a: f64, b: f64) -> f64 {" in rust
    assert "return a + b;" in rust
    assert "fn main() {" in rust


def test_rust_emitter_custom_types():
    code = """
type Person = { name: Text, age: Number }

when app starts:
    p = Person(name="Ada", age=36)
    n = p.name
end
"""
    rust = _emit(code)

    assert "struct Person {" in rust
    assert "name: String," in rust
    assert "age: f64," in rust
    assert "p.name" in rust


def test_rust_emitter_loops_and_conditionals():
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
    rust = _emit(code)

    assert "fn sum_all(items: Vec<f64>) -> f64 {" in rust
    assert "for x in &items {" in rust
    assert "continue;" in rust
    assert "break;" in rust


def test_rust_emitter_interpolation_and_join():
    code = """
fn combine(items: List) -> Text:
    return join(items, ", ")
end
"""
    rust = _emit(code)

    assert "fn omni_join(list: Vec<String>, sep: &str) -> String" in rust
    assert "omni_join(" in rust


def test_rust_emitter_interpolation_format():
    code = """
fn greet(name: Text) -> Text:
    return "Hello {name}"
end
"""
    rust = _emit(code)

    assert "format!" in rust
    assert "Hello {}" in rust
    assert "name" in rust


def test_rust_emitter_bevy_adapter():
    code = """
type Position = { x: Number, y: Number }
type Velocity = { x: Number, y: Number }

when app starts:
    sim.entity("player", [Position(x=0, y=0), Velocity(x=1, y=0)])
end
"""
    rust = _emit(code)

    assert "#[derive(Component, Clone, Debug)]" in rust
    assert "fn setup(mut commands: Commands)" in rust
    assert "commands.spawn((" in rust
    assert 'insert(Name::new("player"))' in rust


def test_rust_emitter_bevy_system():
    code = """
type Position = { x: Number, y: Number }

fn move_system:
    return none
end

when app starts:
    sim.system("move", move_system, "every frame")
end
"""
    rust = _emit(code)

    assert "// sim.system move_system -> Bevy Update system" in rust


def test_rust_emitter_for_each_query():
    code = """
type Position = { x: Number, y: Number }
type Velocity = { x: Number, y: Number }

when app starts:
    sim.for_each(Position, Velocity)
end
"""
    rust = _emit(code)

    assert "// sim.for_each -> Bevy Query" in rust


def test_rust_emitter_runtime_alias():
    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    assert emit_rust_with_runtime(mir) == emit_rust(mir)


def test_rust_emitter_cargo_check():
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")

    code = """
fn add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = add(1, 2)
    show result
end
"""
    rust = _emit(code)

    with tempfile.TemporaryDirectory() as tmp:
        cargo_toml = Path(tmp) / "Cargo.toml"
        cargo_toml.write_text(
            '[package]\nname = "omni_probe"\nversion = "0.1.0"\n'
            'edition = "2021"\n\n[dependencies]\n',
            encoding="utf-8",
        )
        src = Path(tmp) / "src"
        src.mkdir()
        (src / "main.rs").write_text(rust, encoding="utf-8")

        proc = subprocess.run(
            ["cargo", "check"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=tmp,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]