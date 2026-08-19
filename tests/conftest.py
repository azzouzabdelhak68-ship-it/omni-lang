"""pytest configuration and shared fixtures for OmniScript tests"""

from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def valid_fixtures():
    """Return list of valid fixture file paths"""
    return list(Path('tests/fixtures/valid').glob('*.omni'))


@pytest.fixture(scope='session')
def invalid_fixtures():
    """Return list of invalid fixture file paths"""
    return list(Path('tests/fixtures/invalid').glob('*.omni'))


@pytest.fixture
def basic_omni_code():
    """Basic valid OmniScript program"""
    return """
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


@pytest.fixture
def function_with_effects():
    """Function with network and file capabilities"""
    return """
fn fetch_data(url: Text) -> Text:
    uses network
    reads cache
    writes cache
    return "data from " + url
end

fn pure_add(a: Number, b: Number) -> Number:
    pure
    return a + b
end

when app starts:
    result = fetch_data("https://api.example.com")
    sum = pure_add(1, 2)
end
"""


@pytest.fixture
def invalid_network_omni():
    """Invalid OmniScript: missing network capability"""
    return """
fn fetch_data(url: Text) -> Text:
    return "data from " + url
end

when app starts:
    fetch_data("https://api.example.com")
end
"""


@pytest.fixture
def pure_with_effects():
    """Invalid: pure function with side effects"""
    return """
fn bad_pure() -> Text:
    pure
    return "hello"
end

when app starts:
    show "test"
end
"""


@pytest.fixture
def sample_tokens():
    """Pre-tokenized basic program"""
    from omni_compiler.lexer import tokenize  # noqa: PLC0415

    return tokenize('x = 42')


@pytest.fixture
def sample_ast():
    """Pre-parsed AST"""
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    return parse(tokenize('x = 42'))


@pytest.fixture
def sample_symbol_table():
    """Pre-analyzed symbol table"""
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    return analyze(parse(tokenize('x = 42')))


@pytest.fixture
def sample_mir():
    """Pre-built MIR"""
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    return to_mir(parse(tokenize('x = 42')), analyze(parse(tokenize('x = 42'))))


# Custom pytest markers
def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'slow: marks tests as slow (deselect with \'-m "not slow"\')'
    )
    config.addinivalue_line('markers', 'integration: marks tests as integration tests')
    config.addinivalue_line('markers', 'unit: marks tests as unit tests')
    config.addinivalue_line('markers', 'property: marks tests as property-based tests')
    config.addinivalue_line('markers', 'mutation: marks tests as mutation tests')
