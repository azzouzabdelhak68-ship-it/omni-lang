import json
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES_DIR = Path('tests/fixtures')


def get_fixture_files():
    valid_files = list((Path('tests/fixtures/valid')).glob('*.omni'))
    invalid_files = list((Path('tests/fixtures/invalid')).glob('*.omni'))
    return valid_files, invalid_files


class TestValidFixtures:
    """All valid fixtures must parse, type-check, and compile without errors"""

    def test_all_valid_fixtures_parse(self):
        from omni_compiler.lexer import tokenize  # noqa: PLC0415
        from omni_compiler.parser import parse  # noqa: PLC0415

        valid_files, _ = get_fixture_files()
        for fixture in valid_files:
            code = fixture.read_text()
            tokens = tokenize(code)
            ast = parse(tokens)
            assert ast is not None, f'Failed to parse {fixture.name}'

    def test_all_valid_fixtures_type_check(self):
        from omni_compiler.checker import analyze  # noqa: PLC0415
        from omni_compiler.lexer import tokenize  # noqa: PLC0415
        from omni_compiler.parser import parse  # noqa: PLC0415

        valid_files, _ = get_fixture_files()
        for fixture in valid_files:
            code = fixture.read_text()
            tokens = tokenize(code)
            ast = parse(tokens)
            symbol_table = analyze(ast)
            assert symbol_table is not None, f'Type check failed for {fixture.name}'

    def test_all_valid_fixtures_emit_js(self):
        from omni_compiler.checker import analyze  # noqa: PLC0415
        from omni_compiler.emitter import emit_js  # noqa: PLC0415
        from omni_compiler.lexer import tokenize  # noqa: PLC0415
        from omni_compiler.mir import to_mir  # noqa: PLC0415
        from omni_compiler.parser import parse  # noqa: PLC0415

        valid_files, _ = get_fixture_files()
        for fixture in valid_files:
            code = fixture.read_text()
            tokens = tokenize(code)
            ast = parse(tokens)
            symbol_table = analyze(ast)
            mir = to_mir(ast, symbol_table)
            js_code = emit_js(mir)
            assert len(js_code) > 0, f'Empty JS output for {fixture.name}'

    def test_all_valid_fixtures_cli_check(self):
        valid_files, _ = get_fixture_files()
        for fixture in valid_files:
            result = subprocess.run(
                ['python', '-m', 'omni_compiler.cli', 'check', str(fixture)],
                capture_output=True,
                text=True,
                cwd='.',
            )
            assert result.returncode == 0, f'CLI check failed for {fixture.name}: {fixture.stderr}'


class TestInvalidFixtures:
    """All invalid fixtures must fail with proper diagnostics"""

    def test_all_invalid_fixtures_fail_parse_or_check(self):
        _, invalid_files = get_fixture_files()
        for fixture in invalid_files:
            result = subprocess.run(
                ['python', '-m', 'omni_compiler.cli', 'check', str(fixture)],
                capture_output=True,
                text=True,
                cwd='.',
            )
            assert result.returncode != 0, f'Expected failure for {fixture.name}, but got success'

    def test_all_invalid_fixtures_produce_diagnostic(self):
        _, invalid_files = get_fixture_files()
        for fixture in invalid_files:
            result = subprocess.run(
                ['python', '-m', 'omni_compiler.cli', 'check', str(fixture)],
                capture_output=True,
                text=True,
                cwd='.',
            )
            assert result.returncode != 0

            # Must produce valid omni.diagnostic JSON
            try:
                diagnostic = json.loads(result.stdout)
                assert diagnostic['schema'] == 'omni.diagnostic'
                assert diagnostic['version'] == '1.0'
                assert 'code' in diagnostic
                assert 'message' in diagnostic
                assert 'span' in diagnostic
                assert 'location' in diagnostic
                assert 'fixes' in diagnostic
                assert len(diagnostic['fixes']) >= 1
            except json.JSONDecodeError:
                pytest.fail(f'Invalid JSON output for {fixture.name}: {result.stdout}')

    def test_specific_errors(self):
        """Test specific known error patterns"""
        # Test missing network declaration
        fixture = Path('tests/fixtures/invalid/01_missing_network_declaration.omni')
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'check', str(fixture)],
            capture_output=True,
            text=True,
            cwd='.',
        )
        diagnostic = json.loads(result.stdout)
        assert 'network' in diagnostic['message'].lower()
        assert any(fix['kind'] == 'add_declaration' for fix in diagnostic['fixes'])

        # Test pure function with network
        fixture = Path('tests/fixtures/invalid/02_pure_function_with_effects.omni')
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'check', str(fixture)],
            capture_output=True,
            text=True,
            cwd='.',
        )
        diagnostic = json.loads(result.stdout)
        assert 'pure' in diagnostic['message'].lower() or 'effect' in diagnostic['message'].lower()


class TestCLICommands:
    """Test all CLI commands work correctly"""

    def test_check_command(self):
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'check', 'tests/fixtures/valid/01_basic.omni'],
            capture_output=True,
            text=True,
            cwd='.',
        )
        assert result.returncode == 0

    def test_run_command(self):
        result = subprocess.run(
            ['python', '-m', 'omni_compiler.cli', 'run', 'tests/fixtures/valid/01_basic.omni'],
            capture_output=True,
            text=True,
            cwd='.',
            timeout=30,
        )
        assert result.returncode == 0

    def test_inspect_command(self):
        result = subprocess.run(
            [
                'python',
                '-m',
                'omni_compiler.cli',
                'inspect',
                'add',
                'tests/fixtures/valid/02_function_with_effects.omni',
            ],
            capture_output=True,
            text=True,
            cwd='.',
        )
        assert result.returncode == 0
        symbol = json.loads(result.stdout)
        assert symbol['schema'] == 'omni.symbol'
        assert symbol['name'] == 'add'

    def test_explain_command(self):
        result = subprocess.run(
            [
                'python',
                '-m',
                'omni_compiler.cli',
                'explain',
                'tests/fixtures/invalid/01_missing_network_declaration.omni',
            ],
            capture_output=True,
            text=True,
            cwd='.',
        )
        assert result.returncode != 0
        diagnostic = json.loads(result.stdout)
        assert diagnostic['schema'] == 'omni.diagnostic'
        assert 'hint' in diagnostic
        assert 'fixes' in diagnostic


class TestDiagnosticsFormat:
    """Test that diagnostic output conforms to omni.diagnostic schema"""

    def test_diagnostic_schema_compliance(self):
        result = subprocess.run(
            [
                'python',
                '-m',
                'omni_compiler.cli',
                'check',
                'tests/fixtures/invalid/01_missing_network_declaration.omni',
            ],
            capture_output=True,
            text=True,
            cwd='.',
        )
        diagnostic = json.loads(result.stdout)

        # Required fields
        assert diagnostic['schema'] == 'omni.diagnostic'
        assert diagnostic['version'] == '1.0'
        assert 'code' in diagnostic
        assert 'category' in diagnostic
        assert 'severity' in diagnostic
        assert 'message' in diagnostic
        assert 'details' in diagnostic
        assert 'span' in diagnostic
        assert 'location' in diagnostic
        assert 'context' in diagnostic
        assert 'fixes' in diagnostic

        # Span must have start/end
        assert 'start' in diagnostic['span']
        assert 'end' in diagnostic['span']
        assert isinstance(diagnostic['span']['start'], int)
        assert isinstance(diagnostic['span']['end'], int)

        # Location must have line/column
        assert 'line' in diagnostic['location']
        assert 'column' in diagnostic['location']
        assert isinstance(diagnostic['location']['line'], int)
        assert isinstance(diagnostic['location']['column'], int)

        # Fixes must have proper structure
        assert len(diagnostic['fixes']) >= 1
        for fix in diagnostic['fixes']:
            assert 'id' in fix
            assert 'kind' in fix
            assert 'applicability' in fix
            assert fix['applicability'] in ['automatic', 'suggested']
            assert 'description' in fix
            assert 'edit' in fix
            assert 'operation' in fix['edit']
            assert fix['edit']['operation'] in ['insert', 'replace', 'delete']
            assert 'span' in fix['edit']
            assert 'text' in fix['edit']


def test_omnisys_capitalized_call_runs_under_node(tmp_path: Path) -> None:
    """HIGH-2: `OMNISYS.core.abs` normalizes to `omnisys.core.abs` and runs under Node."""
    if shutil.which('node') is None:
        pytest.skip('node not installed')
    from omni_compiler.checker import analyze  # noqa: PLC0415
    from omni_compiler.emitter import emit_js  # noqa: PLC0415
    from omni_compiler.lexer import tokenize  # noqa: PLC0415
    from omni_compiler.mir import to_mir  # noqa: PLC0415
    from omni_compiler.parser import parse  # noqa: PLC0415

    code = """
import OMNISYS.core
when app starts:
    show OMNISYS.core.abs(-5)
end
"""
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    html = emit_js(mir)
    assert 'OMNISYS.core.abs' not in html
    assert 'omnisys.core.abs(' in html

    out = tmp_path / 'normalized.html'
    out.write_text(html, encoding='utf-8')
    result = subprocess.run(
        ['node', 'scripts/run-omnisys.js', str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '5' in result.stdout
