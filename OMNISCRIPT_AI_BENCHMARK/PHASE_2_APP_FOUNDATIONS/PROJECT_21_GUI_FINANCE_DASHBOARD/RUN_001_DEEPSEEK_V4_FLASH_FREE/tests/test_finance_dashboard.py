"""Automated test suite for the OmniScript finance dashboard (Project 2.1).

Strategy:
- Compile source/finance_dashboard.omni in-process (tokenize/parse/analyze/mir) and
  emit the JS/HTML artifact (same pipeline as `omni build --target js`).
- Drive the REAL compiled program in a headless Chromium (playwright) via
  `page.evaluate("batchUpdate(function(){ ... })")` — the exact runtime path a click
  action uses (fn() then renderUI()). Assert on both module state and the rendered DOM.
- One test does a REAL click to demonstrate live-link in the artifact without reload.
- One test pins the known compiler limitation: click handlers are not re-bound after a
  re-render (bindClicks runs once), so a second physical click is inert.

The suite is self-contained: it rebuilds the artifact under tests/_build/ in this run dir.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE = RUN_DIR / "source" / "finance_dashboard.omni"
BUILD_DIR = RUN_DIR / "tests" / "_build"
ARTIFACT = BUILD_DIR / "finance_dashboard.html"


# ---------------------------------------------------------------- helpers

def build_artifact() -> Path:
    """Compile + emit the dashboard artifact (mirrors `omni build --target js`)."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    code = SOURCE.read_text(encoding="utf-8")
    ast = parse(tokenize(code))
    analyze(ast)
    mir = to_mir(ast)
    html = emit_js(mir)
    ARTIFACT.write_text(html, encoding="utf-8")
    return ARTIFACT


def app_html(page) -> str:
    return page.evaluate("document.getElementById('app').innerHTML")


def state(page, name):
    """Read a module-scope variable from the compiled program (null-safe)."""
    return page.evaluate(
        "(typeof {name} === 'undefined') ? null : {name}".format(name=name)
    )


def act(page, js_expr):
    """Run an action exactly like a click action does: batchUpdate(fn) -> fn(); renderUI()."""
    page.evaluate("batchUpdate(function(){ " + js_expr + "; })")


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope="session")
def artifact():
    return build_artifact()


@pytest.fixture(scope="session")
def _browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture()
def page(_browser, artifact):
    page_obj = _browser.new_page()
    errors = []
    page_obj.on("pageerror", lambda e: errors.append(str(e)))
    page_obj.goto(artifact.as_uri())
    yield page_obj, errors
    page_obj.close()


# ---------------------------------------------------------------- source & build

def test_source_file_is_utf8_without_bom():
    raw = SOURCE.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "BOM present; lexer would reject it"


def test_omni_check_command_exits_zero():
    proc = subprocess.run(
        [sys.executable, "-m", "omni_compiler.cli", "check", str(SOURCE)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK" in proc.stdout


def test_build_target_js_exits_zero():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable, "-m", "omni_compiler.cli", "build",
            str(SOURCE), "--target", "js", "-o", str(ARTIFACT),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ARTIFACT.exists()
    html = ARTIFACT.read_text(encoding="utf-8")
    assert '<div id="app"></div>' in html
    assert "renderUI" in html and "bindClicks" in html


def test_source_declares_data_model_and_ui_block():
    code = SOURCE.read_text(encoding="utf-8")
    assert "type Transaction =" in code
    assert "UI:" in code
    for fn in (
        "validate_amount", "validate_category", "validate_date",
        "add_transaction", "recompute", "go_overview", "go_transactions",
        "go_breakdown", "apply_category_filter", "apply_date_filter", "clear_filters",
    ):
        assert f"fn {fn}" in code


# ---------------------------------------------------------------- initial state

def test_initial_state(page):
    pg, errors = page
    assert errors == []
    assert state(pg, "view") == "overview"
    assert state(pg, "total_count") == 5
    assert state(pg, "visible_count") == 5
    assert state(pg, "balance") == 3481.7
    assert state(pg, "render_count") == 1
    assert state(pg, "overview_display") == "block"
    assert state(pg, "transactions_display") == "none"
    assert state(pg, "breakdown_display") == "none"


def test_initial_table_and_breakdown(page):
    pg, _ = page
    assert state(pg, "r0_date") == "2025-11-01"
    assert state(pg, "r0_category") == "Food"
    assert state(pg, "r0_amount") == 12.5
    assert state(pg, "r5_date") == ""  # 6th row is empty with only 5 txns
    assert state(pg, "cat_name_0") == "Food" and state(pg, "cat_total_0") == 86.7
    assert state(pg, "cat_name_1") == "Rent" and state(pg, "cat_total_1") == 800
    assert state(pg, "cat_name_3") == "Income" and state(pg, "cat_total_3") == 2500


def test_initial_dom_shows_overview(page):
    pg, _ = page
    html = app_html(pg)
    assert "Personal Finance Dashboard" in html
    assert "$3481.7" in html
    assert "2025-11-01" in html and "Coffee" in html
    assert 'display:block' in html  # overview panel visible


# ---------------------------------------------------------------- live-link (state -> DOM)

def test_state_change_propagates_to_dom_without_reload(page):
    """Live-link: a state mutation + batch render updates the visible output."""
    pg, _ = page
    before = app_html(pg)
    act(pg, "add_transaction(99.5, 'Travel', '2025', '12', '01', 'Flight')")
    after = app_html(pg)
    assert before != after
    assert "Travel" in after and "2025-12-01" in after and "99.5" in after
    assert state(pg, "render_count") == 2


def test_real_click_updates_visible_output_without_reload(page):
    """Demonstrate live-link via the generated artifact: a physical click re-renders."""
    pg, _ = page
    pg.click("button[click='go_transactions']")
    html = app_html(pg)
    assert state(pg, "view") == "transactions"
    assert state(pg, "transactions_display") == "block"
    assert state(pg, "overview_display") == "none"
    assert 'display:block' in html  # transactions panel now visible in DOM
    assert state(pg, "render_count") == 2


def test_second_click_updates_visible_output_without_reload(page):
    """bindClicks() attaches ONE delegated listener on #app (emitter). Because the
    listener lives on the container, innerHTML replacement does not destroy it:
    a second physical click re-fires the action and live-links the visible output
    without a reload. (Originally misdiagnosed as a dead-second-click limitation
    caused by the module-scope shadowing emitter bug.)"""
    pg, _ = page
    pg.click("button[click='go_transactions']")
    assert state(pg, "view") == "transactions"
    pg.click("button[click='go_breakdown']")
    assert state(pg, "view") == "breakdown", (
        "Delegated #app listener must survive re-render; second click live-links"
    )


# ---------------------------------------------------------------- state transitions

def test_view_switch_transitions(page):
    pg, _ = page
    act(pg, "go_breakdown()")
    assert state(pg, "view") == "breakdown"
    assert state(pg, "breakdown_display") == "block"
    assert state(pg, "nav_breakdown_weight") == "bold"
    assert state(pg, "nav_overview_weight") == "normal"
    act(pg, "go_overview()")
    assert state(pg, "view") == "overview"
    assert state(pg, "overview_display") == "block"


def test_add_valid_transaction_updates_balance_and_list(page):
    pg, _ = page
    act(pg, "add_transaction(99.5, 'Travel', '2025', '12', '01', 'Flight')")
    txns = state(pg, "transactions")
    assert len(txns) == 6
    assert txns[-1]["category"] == "Travel"
    assert txns[-1]["date"] == "2025-12-01"
    assert state(pg, "balance") == 3581.2  # 3481.7 + 99.5
    assert state(pg, "total_count") == 6
    assert state(pg, "visible_count") == 6
    assert state(pg, "error_message") == ""
    assert state(pg, "notice") != ""


def test_breakdown_recomputes_after_add(page):
    pg, _ = page
    act(pg, "add_transaction(1500.0, 'Income', '2025', '11', '15', 'Paycheck')")
    assert state(pg, "cat_name_1") == "Rent"
    assert state(pg, "cat_total_3") == 4000.0  # Income: 2500 + 1500


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize(
    "expr,expected_err",
    [
        ("validate_amount(10)", ""),
        ("validate_amount(0)", "Amount must be a positive number."),
        ("validate_amount(-5)", "Amount must be a positive number."),
        ("validate_category('Food')", ""),
        ("validate_category('')", "Category must not be empty."),
        ("validate_date('2025','11','01')", ""),
        ("validate_date('25','11','01')", "Date year must be 4 digits."),
        ("validate_date('2025','1','01')", "Date month must be 2 digits."),
        ("validate_date('2025','13','01')", "Date month must be between 01 and 12."),
        ("validate_date('2025','ab','01')", "Date month must be numeric."),
        ("validate_date('2025','11','32')", "Date day must be between 01 and 31."),
        ("validate_date('2025','11','00')", "Date day must be numeric."),
        ("validate_date('1899','11','01')", "Date year must be at least 1900."),
        ("validate_date('2025','11','5')", "Date day must be 2 digits."),
    ],
)
def test_validators(page, expr, expected_err):
    pg, _ = page
    assert pg.evaluate(expr) == expected_err


def test_add_invalid_amount_rejected(page):
    pg, _ = page
    act(pg, "add_transaction(-5, 'Food', '2025', '11', '20', 'Bad')")
    assert len(state(pg, "transactions")) == 5
    assert state(pg, "balance") == 3481.7
    assert state(pg, "error_message") == "Amount must be a positive number."
    assert state(pg, "notice") == ""


def test_add_invalid_category_rejected(page):
    pg, _ = page
    act(pg, "add_transaction(10, '', '2025', '11', '20', 'Bad')")
    assert len(state(pg, "transactions")) == 5
    assert state(pg, "error_message") == "Category must not be empty."


def test_add_invalid_date_rejected(page):
    pg, _ = page
    act(pg, "add_transaction(10, 'Food', '2025', '13', '01', 'Bad')")
    assert len(state(pg, "transactions")) == 5
    assert state(pg, "error_message") == "Date month must be between 01 and 12."


def test_error_banner_appears_in_dom(page):
    pg, _ = page
    assert state(pg, "error_display") == "none"
    act(pg, "add_transaction(-1, 'Food', '2025', '11', '20', 'Bad')")
    html = app_html(pg)
    assert state(pg, "error_display") == "block"
    assert "Amount must be a positive number." in html
    assert "display:block" in html


# ---------------------------------------------------------------- filtering & empty state

def test_filter_by_category(page):
    pg, _ = page
    act(pg, "apply_category_filter('Food')")
    assert state(pg, "filter_category") == "Food"
    assert state(pg, "visible_count") == 2
    assert state(pg, "visible_total") == 86.7
    assert state(pg, "r0_category") == "Food"
    assert state(pg, "r1_category") == "Food"
    assert state(pg, "r2_date") == ""  # only 2 rows filled


def test_filter_by_date_range(page):
    pg, _ = page
    act(pg, "apply_date_filter('2025-11-01', '2025-11-05')")
    assert state(pg, "visible_count") == 3  # 01, 03, 05
    assert state(pg, "r0_date") == "2025-11-01"
    assert state(pg, "r2_date") == "2025-11-05"
    assert state(pg, "r3_date") == ""


def test_clear_filters(page):
    pg, _ = page
    act(pg, "apply_category_filter('Income')")
    assert state(pg, "visible_count") == 1
    act(pg, "clear_filters()")
    assert state(pg, "visible_count") == 5
    assert state(pg, "filter_category") == ""
    assert state(pg, "filter_from") == ""
    assert state(pg, "filter_to") == ""


def test_empty_state_when_nothing_matches(page):
    pg, _ = page
    act(pg, "apply_date_filter('2020-01-01', '2020-01-31')")
    assert state(pg, "visible_count") == 0
    assert state(pg, "empty_notice") != ""
    assert state(pg, "empty_notice_display") == "block"
    html = app_html(pg)
    assert "No transactions match the current filters" in html


def test_empty_state_clears_when_filter_matches(page):
    pg, _ = page
    act(pg, "apply_date_filter('2020-01-01', '2020-01-31')")
    assert state(pg, "empty_notice") != ""
    act(pg, "clear_filters()")
    assert state(pg, "empty_notice") == ""
    assert state(pg, "empty_notice_display") == "none"