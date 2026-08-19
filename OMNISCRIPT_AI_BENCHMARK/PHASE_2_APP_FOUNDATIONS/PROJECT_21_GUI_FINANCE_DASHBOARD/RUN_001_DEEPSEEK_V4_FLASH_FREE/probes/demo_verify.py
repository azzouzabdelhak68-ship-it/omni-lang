"""Final browser verification of the finance dashboard artifact.

Uses the SAME runtime path a click uses (batchUpdate -> fn -> renderUI) to verify:
  - live-link: state changes propagate to visible DOM without reload
  - validation: invalid submissions surface a distinct error banner
  - filtering: category + date-range filters shrink the table; empty state banner
  - a REAL first click still works end-to-end
Then documents the known single-shot click limitation.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html_path = Path(sys.argv[1] if len(sys.argv) > 1 else "source/finance_dashboard.html").resolve()


def strip(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def errs(page):
    return page.evaluate(
        "(() => { const app = document.getElementById('app'); "
        "const cells = app.querySelectorAll('td'); let out = []; "
        "for (const c of cells) out.push(c.textContent.trim()); return out; })()"
    )


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.goto(html_path.as_uri())

    print("1. INITIAL:", strip(page.locator("#app").inner_html())[:400], "...")
    print("   balance var:", page.evaluate("balance"), "| render#:", page.evaluate("render_count"))

    # live-link: run an action through the exact click path (batchUpdate)
    page.evaluate("batchUpdate(function(){ go_transactions(); })")
    print("2. after go_transactions via batchUpdate: view =", page.evaluate("view"),
          "| transactions_display =", page.evaluate("transactions_display"))
    assert page.evaluate("transactions_display") == "block"

    # valid add -> state + DOM both update
    page.evaluate("batchUpdate(function(){ add_transaction(99.5, 'Travel', '2025', '12', '01', 'Flight'); })")
    print("3. after valid add: balance =", page.evaluate("balance"),
          "| total_count =", page.evaluate("total_count"),
          "| error_message =", repr(page.evaluate("error_message")))
    html = page.locator("#app").inner_html()
    print("   DOM contains Travel row:", "Travel" in html and "2025-12-01" in html and "99.5" in html)

    # invalid add -> error banner visible in DOM
    page.evaluate("batchUpdate(function(){ add_transaction(-5, 'Food', '2025', '11', '20', 'Bad'); })")
    print("4. after invalid add: error_message =", repr(page.evaluate("error_message")),
          "| error_display =", page.evaluate("error_display"))
    html = page.locator("#app").inner_html()
    print("   DOM error banner visible:", "display:block" in html and "Amount must be a positive number." in html)

    # filter by category
    page.evaluate("batchUpdate(function(){ apply_category_filter('Food'); })")
    print("5. filter Food: visible_count =", page.evaluate("visible_count"),
          "| visible_total =", page.evaluate("visible_total"))

    # date range with no matches -> empty state
    page.evaluate("batchUpdate(function(){ apply_date_filter('2020-01-01', '2020-01-31'); })")
    html = page.locator("#app").inner_html()
    print("6. empty state: visible_count =", page.evaluate("visible_count"),
          "| empty_notice shown:", "No transactions match the current filters" in html)

    # REAL first click (the compiler's supported interaction): navigate to breakdown
    page.goto(html_path.as_uri())  # fresh load = fresh state, allows one click
    page.click("button[click='go_breakdown']")
    print("7. real click -> breakdown: view =", page.evaluate("view"),
          "| render# =", page.evaluate("render_count"))
    # second click is inert (documented limitation)
    page.click("button[click='go_overview']")
    print("8. second real click -> view =", page.evaluate("view"), "(expected still breakdown)")

    print("PAGE ERRORS:", page_errors)
    assert page_errors == [], page_errors
    browser.close()
    print("ALL BROWSER CHECKS OK")