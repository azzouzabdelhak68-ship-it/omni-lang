"""Browser smoke harness (playwright). Loads a built OmniScript HTML artifact and:
1. prints the rendered #app innerHTML,
2. clicks buttons and prints the updated innerHTML,
3. can evaluate arbitrary global functions and re-render.

Usage: python smoke2.py <artifact.html>
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html_path = Path(sys.argv[1]).resolve()
url = html_path.as_uri()


def strip_html(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", s).strip()


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(f"console:{m.type}: {m.text}") if m.type == "error" else None)
    page.goto(url)
    print("=== INITIAL ===")
    print(strip_html(page.locator("#app").inner_html()))
    buttons = page.locator("button")
    n = buttons.count()
    print(f"=== {n} buttons ===")
    for i in range(n):
        label = buttons.nth(i).inner_text()
        buttons.nth(i).click()
        print(f"--- after click[{i}] '{label}' ---")
        print(strip_html(page.locator("#app").inner_html()))
    print("=== page errors:", errors)
    browser.close()