"""v4.2: AI tooling - suggest_fix, apply_fix, generate_test, trace_execution."""

import json
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

import pytest

from omni_compiler import ai_tools
from omni_compiler.ai_tools import (
    apply_automatic_fixes,
    apply_fix,
    generate_test,
    suggest_fix,
    trace_execution,
    trace_to_json,
)
from omni_compiler.checker import DiagnosticError, SymbolTable, analyze
from omni_compiler.lexer import tokenize
from omni_compiler.parser import parse

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'tests' / 'fixtures' / 'valid' / '02_function_with_effects.omni'
AUTOMATIC_CONFIDENCE = 0.95
SUGGESTED_CONFIDENCE = 0.7

MISSING_NETWORK = """
fn get_data(url: Text) -> Text:
    return fetch(url)
end

when app starts:
    result = get_data("http://example.com")
end
"""


def _compile_source(src: str):
    ast = parse(tokenize(src))
    table = analyze(ast)
    return ast, table


# ---- suggest_fix ----


def test_suggest_fix_effect_error_ranked():
    ast = parse(tokenize(MISSING_NETWORK))
    with suppress(Exception):
        analyze(ast)
    fixes = suggest_fix(ast, SymbolTable())
    assert fixes, 'expected at least one ranked fix'
    first = fixes[0]
    assert first['applicability'] == 'automatic'
    assert first['rank'] == 1
    assert first['confidence'] == AUTOMATIC_CONFIDENCE
    assert first['code'] == 'E-EFFECT-003'
    assert first['location'] == {'line': 1, 'column': 1}
    assert first['edit']['text'] == '    uses network\n'


def test_suggest_fix_ranks_automatic_before_suggested(monkeypatch):
    diag = DiagnosticError(
        'E-TEST-001',
        'test',
        'error',
        'boom',
        'boom',
        fixes=[
            {
                'id': 'suggested-fix',
                'kind': 'replace_span',
                'applicability': 'suggested',
                'description': 'd',
                'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
            },
            {
                'id': 'auto-fix',
                'kind': 'replace_span',
                'applicability': 'automatic',
                'description': 'd',
                'edit': {'operation': 'insert', 'span': {'start': 0, 'end': 0}, 'text': ''},
            },
        ],
    )

    def _boom(_prog):
        raise diag

    monkeypatch.setattr(ai_tools, 'analyze', _boom)
    ast = parse(tokenize('when app starts:\n    x = 1\nend\n'))
    fixes = suggest_fix(ast, SymbolTable())
    assert [f['id'] for f in fixes] == ['auto-fix', 'suggested-fix']
    assert [f['rank'] for f in fixes] == [1, 2]
    assert fixes[0]['confidence'] == AUTOMATIC_CONFIDENCE
    assert fixes[1]['confidence'] == SUGGESTED_CONFIDENCE
    assert fixes[0]['code'] == 'E-TEST-001'
    assert fixes[1]['message'] == 'boom'


def test_suggest_fix_clean_source_returns_empty():
    src = 'fn add(a: Number, b: Number) -> Number:\n    pure\n    return a + b\nend\n'
    ast, table = _compile_source(src)
    assert suggest_fix(ast, table) == []


# ---- apply_fix ----


def test_apply_fix_insert():
    fix = {'edit': {'operation': 'insert', 'span': {'start': 5, 'end': 5}, 'text': 'XX'}}
    assert apply_fix('abcdef', fix) == 'abcdeXXf'


def test_apply_fix_replace():
    fix = {'edit': {'operation': 'replace', 'span': {'start': 1, 'end': 4}, 'text': 'XYZ'}}
    assert apply_fix('abcdef', fix) == 'aXYZef'


def test_apply_fix_delete():
    fix = {'edit': {'operation': 'delete', 'span': {'start': 2, 'end': 5}, 'text': ''}}
    assert apply_fix('abcdef', fix) == 'abf'


def test_apply_fix_out_of_range_raises():
    fix = {'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 99}, 'text': 'x'}}
    with pytest.raises(ValueError):
        apply_fix('abc', fix)


def test_apply_fix_unknown_operation_raises():
    fix = {'edit': {'operation': 'nope', 'span': {'start': 0, 'end': 1}, 'text': 'x'}}
    with pytest.raises(ValueError):
        apply_fix('abc', fix)


def test_apply_automatic_fixes_applies_in_descending_span_order():
    source = 'abcdef'
    fixes = [
        {
            'applicability': 'suggested',
            'edit': {'operation': 'replace', 'span': {'start': 0, 'end': 1}, 'text': '!'},
        },
        {
            'applicability': 'automatic',
            'edit': {'operation': 'replace', 'span': {'start': 1, 'end': 3}, 'text': 'Q'},
        },
        {
            'applicability': 'automatic',
            'edit': {'operation': 'insert', 'span': {'start': 4, 'end': 4}, 'text': 'Z'},
        },
    ]
    assert apply_automatic_fixes(source, fixes) == 'aQdZef'


# ---- generate_test ----


def test_generate_test_is_valid_python_and_runs(tmp_path):
    ast, table = _compile_source(FIXTURE.read_text(encoding='utf-8'))
    test_code = generate_test(ast, table, 'pure_add', source_file=str(FIXTURE))
    assert isinstance(test_code, str)
    compile(test_code, '<generated>', 'exec')
    out = tmp_path / 'test_generated_pure_add.py'
    out.write_text(test_code, encoding='utf-8')
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', str(out), '-q', '-p', 'no:cacheprovider'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_generate_test_unknown_function_raises():
    ast, table = _compile_source(FIXTURE.read_text(encoding='utf-8'))
    with pytest.raises(ValueError):
        generate_test(ast, table, 'nope')


def test_generate_test_embeds_omni_file_and_contracts():
    ast, table = _compile_source(FIXTURE.read_text(encoding='utf-8'))
    test_code = generate_test(ast, table, 'add', source_file=str(FIXTURE))
    assert 'OMNI_FILE' in test_code
    assert 'pure' in test_code or 'add' in test_code
    assert 'test_add_compiles' in test_code
    assert 'test_add_contracts_present' in test_code
    assert '@given' in test_code


# ---- trace_execution ----


def test_trace_execution_simple_function():
    ast, table = _compile_source(
        'fn pure_add(a: Number, b: Number) -> Number:\n    pure\n    return a + b\nend\n'
    )
    trace = trace_execution(ast, table, 'pure_add')
    assert [e['kind'] for e in trace] == ['enter_fn', 'return']
    assert trace[0]['step'] == 1
    assert trace[0]['function'] == 'pure_add'
    assert trace[0]['env'] == {'a': '?', 'b': '?'}
    assert trace[1]['statement'] == 'return a + b'
    assert trace[1]['span'] == {'start': 0, 'end': 0}


def test_trace_execution_assignments_and_calls():
    ast, table = _compile_source(
        'fn label(items: List) -> Text:\n'
        '    pure\n'
        '    words = join(items, ", ")\n'
        '    return words\n'
        'end\n'
    )
    trace = trace_execution(ast, table, 'label')
    kinds = [e['kind'] for e in trace]
    assert 'assign' in kinds
    assign = next(e for e in trace if e['kind'] == 'assign')
    assert assign['statement'] == 'words = join(items, ", ")'
    assert assign['env']['words'] == ''


def test_trace_execution_loop_with_known_list():
    ast, table = _compile_source(
        'when app starts:\n    for n in [1, 2, 3]:\n        x = n\n    end\nend\n'
    )
    trace = trace_execution(ast, table)
    assert trace[0]['kind'] == 'for'
    assert trace[0]['statement'] == 'for n in [1, 2, 3]:'
    assigns = [e for e in trace if e['kind'] == 'assign']
    assert [e['env']['x'] for e in assigns] == [1, 2, 3]
    assert [e['env']['n'] for e in assigns] == [1, 2, 3]


def test_trace_execution_loop_with_unknown_iterable_stops():
    ast, table = _compile_source(
        'fn scan(items: List) -> Number:\n'
        '    total = 0\n'
        '    for n in items:\n'
        '        total = total + n\n'
        '    end\n'
        '    return total\n'
        'end\n'
    )
    trace = trace_execution(ast, table, 'scan')
    assert [e['kind'] for e in trace] == ['enter_fn', 'assign', 'for', 'return']


def test_trace_execution_if_branch_taken():
    ast, table = _compile_source(
        'when app starts:\n    if 1 greater than 0:\n        x = 1\n    end\nend\n'
    )
    trace = trace_execution(ast, table)
    if_ev = trace[0]
    assert if_ev['kind'] == 'if'
    assert if_ev['branch'] == 'taken'
    assert trace[1]['kind'] == 'assign'


def test_trace_execution_if_else_branch():
    ast, table = _compile_source(
        'when app starts:\n'
        '    if 0 greater than 1:\n'
        '        x = 1\n'
        '    else:\n'
        '        x = 2\n'
        '    end\n'
        'end\n'
    )
    trace = trace_execution(ast, table)
    if_ev = trace[0]
    assert if_ev['branch'] == 'else'
    assert trace[1]['kind'] == 'assign'
    assert trace[1]['env']['x'] == 2  # noqa: PLR2004


def test_trace_to_json():
    trace = [
        {
            'step': 1,
            'kind': 'enter_fn',
            'function': 'f',
            'statement': 'enter fn f',
            'env': {},
            'span': {'start': 0, 'end': 0},
        }
    ]
    payload = json.loads(trace_to_json(trace))
    assert payload[0]['step'] == 1
    assert payload[0]['kind'] == 'enter_fn'


def test_suggest_fix_syntax_error(monkeypatch):
    def _boom(_prog):
        raise SyntaxError('bad syntax here')

    monkeypatch.setattr(ai_tools, 'analyze', _boom)
    ast = parse(tokenize('when app starts:\n    x = 1\nend\n'))
    fixes = suggest_fix(ast, SymbolTable())
    assert fixes[0]['code'] == 'E-SYNTAX-001'
    assert fixes[0]['applicability'] == 'suggested'


def test_suggest_fix_name_error(monkeypatch):
    def _boom(_prog):
        raise NameError("Undefined variable or function 'zorp'")

    monkeypatch.setattr(ai_tools, 'analyze', _boom)
    ast = parse(tokenize('when app starts:\n    x = 1\nend\n'))
    fixes = suggest_fix(ast, SymbolTable())
    assert fixes[0]['code'] == 'E-NAME-001'


def test_suggest_fix_internal_error(monkeypatch):
    def _boom(_prog):
        raise RuntimeError('unexpected crash')

    monkeypatch.setattr(ai_tools, 'analyze', _boom)
    ast = parse(tokenize('when app starts:\n    x = 1\nend\n'))
    fixes = suggest_fix(ast, SymbolTable())
    assert fixes == []


def test_apply_fix_missing_edit_raises():
    with pytest.raises(ValueError):
        apply_fix('abc', {'id': 'x'})


def test_apply_fix_missing_span_raises():
    with pytest.raises(ValueError):
        apply_fix('abc', {'edit': {'operation': 'insert', 'text': 'x'}})


def test_apply_fix_non_integer_span_raises():
    bad_span = {'edit': {'operation': 'insert', 'span': {'start': 0.5, 'end': 1}, 'text': 'x'}}
    with pytest.raises(ValueError):
        apply_fix('abc', bad_span)


def test_apply_fix_negative_or_reversed_span_raises():
    negative = {'edit': {'operation': 'replace', 'span': {'start': -1, 'end': 2}, 'text': 'x'}}
    reversed_span = {'edit': {'operation': 'replace', 'span': {'start': 3, 'end': 1}, 'text': 'x'}}
    with pytest.raises(ValueError):
        apply_fix('abc', negative)
    with pytest.raises(ValueError):
        apply_fix('abc', reversed_span)


def test_trace_execution_show_and_return_and_call_statements():
    ast, table = _compile_source(
        'fn helper() -> Number:\n'
        '    pure\n'
        '    return 1\n'
        'end\n'
        'fn drive() -> Number:\n'
        '    pure\n'
        '    helper()\n'
        '    show 1\n'
        '    return 2\n'
        'end\n'
    )
    trace = trace_execution(ast, table, 'drive')
    kinds = [e['kind'] for e in trace]
    assert 'call' in kinds
    assert 'show' in kinds
    assert 'return' in kinds


def test_trace_execution_if_unknown_condition():
    ast, table = _compile_source(
        'fn helper() -> Number:\n'
        '    pure\n'
        '    return 1\n'
        'end\n'
        'fn choose(flag: Boolean) -> Number:\n'
        '    pure\n'
        '    if helper() greater than 5:\n'
        '        return 1\n'
        '    end\n'
        '    return 2\n'
        'end\n'
    )
    trace = trace_execution(ast, table, 'choose')
    if_ev = next(e for e in trace if e['kind'] == 'if')
    assert if_ev['branch'] == 'unknown'


def test_trace_execution_struct_field_access():
    ast, table = _compile_source(
        'type Person = { name: Text, age: Number }\n'
        'when app starts:\n'
        "    p = Person(name = 'Ada', age = 36)\n"
        '    n = p.name\n'
        'end\n'
    )
    trace = trace_execution(ast, table)
    assign_events = [e for e in trace if e['kind'] == 'assign']
    assert any(e['statement'].startswith('n = p.name') for e in assign_events)


def test_trace_execution_list_literal_iteration():
    ast, table = _compile_source(
        'when app starts:\n    for n in [1, 2]:\n        x = n\n    end\nend\n'
    )
    trace = trace_execution(ast, table)
    assert trace[0]['kind'] == 'for'
    assert len([e for e in trace if e['kind'] == 'assign']) == 2  # noqa: PLR2004


def test_generate_test_sample_with_text_param():
    ast, table = _compile_source('fn greet(name: Text) -> Text:\n    pure\n    return name\nend\n')
    test_code = generate_test(ast, table, 'greet')
    assert 'test_greet_sample_inputs' in test_code
    assert '@given' not in test_code


def test_generate_test_boolean_param_property():
    ast, table = _compile_source(
        'fn identity(flag: Boolean) -> Boolean:\n    pure\n    return flag\nend\n'
    )
    test_code = generate_test(ast, table, 'identity')
    assert 'st.booleans()' in test_code


def test_expr_to_string_unary_and_group():
    from omni_compiler.ai_tools import _expr_to_string  # noqa: PLC0415

    ast = parse(tokenize('when app starts:\n    x = 1\n    y = (x) is -1\nend\n'))
    stmt = ast.app_block.body[1]
    text = _expr_to_string(stmt.expr)
    assert '(' in text
    assert '-' in text
