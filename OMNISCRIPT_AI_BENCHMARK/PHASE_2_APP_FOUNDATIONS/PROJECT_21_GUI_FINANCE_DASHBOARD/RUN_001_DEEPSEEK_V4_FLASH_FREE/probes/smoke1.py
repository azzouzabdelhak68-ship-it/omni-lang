"""Playwright smoke test for probe1: live-link behavior of the emitted HTML."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html_path = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/probe1_counter.html").resolve()
url = html_path.as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
    page.goto(url)
    h1 = page.locator("h1")
    print("initial h1:", h1.inner_text())
    btn = page.locator("button")
    print("initial button count:", btn.count())
    btn.click()
    print("after 1st click h1:", h1.inner_text())
    btn.click()
    print("after 2nd click h1:", h1.inner_text())
    btn.click()
    print("after 3rd click h1:", h1.inner_text())
    print("page errors:", errors)
    browser.close()