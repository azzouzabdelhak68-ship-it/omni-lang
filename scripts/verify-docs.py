#!/usr/bin/env python3
"""Verify the docs/ tree.

Rules:
  1. No broken internal links in docs/
  2. No orphaned files (every .md under docs/ referenced by INDEX.md)
  3. All 18 OMNISYS modules have a README
  4. Every module README has the six-field header set
  5. Status field is one of: stable, experimental, planned
  6. CAPABILITY_MATRIX.md exists and is in sync

Exit code 0 on success, 1 on any violation.
"""

import importlib.util
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

_cm_spec = importlib.util.spec_from_file_location(
    "gen_capability_matrix", SCRIPT_DIR / "gen-capability-matrix.py"
)
gen_capability_matrix = importlib.util.module_from_spec(_cm_spec)
_cm_spec.loader.exec_module(gen_capability_matrix)

ROOT = SCRIPT_DIR.parent
DOCS = ROOT / "docs"
INDEX = DOCS / "INDEX.md"

MODULES = [
    "core", "ui", "db", "graphics", "gpu", "net", "http", "audio", "video",
    "fs", "crypto", "auth", "sim", "ai", "test", "async", "platform", "scene",
]

REQUIRED_HEADERS = [
    "## Purpose",
    "## Public API surface",
    "## Dependencies",
    "## Effects/capabilities used",
    "## Status",
    "## Open Questions",
]

STATUS_VALUES = {"stable", "experimental", "planned"}

LINK_RE = re.compile(r"\]\(([^)]+)\)")
ANCHOR_OR_EXTERNAL = re.compile(r"^(#|https?://|mailto:|/)")


def violations() -> list[str]:
    issues: list[str] = []

    all_md = sorted(p for p in DOCS.rglob("*.md") if p.is_file())
    all_md_rel = {p.relative_to(DOCS).as_posix(): p for p in all_md}

    index_text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""

    for file in all_md:
        rel = file.relative_to(DOCS).as_posix()
        text = file.read_text(encoding="utf-8")

        for match in LINK_RE.finditer(text):
            target = match.group(1)
            if ANCHOR_OR_EXTERNAL.match(target):
                continue
            if "#" in target:
                target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (file.parent / target).resolve()
            if not resolved.exists():
                issues.append(f"broken link in {rel}: -> {match.group(1)}")

        if rel != "INDEX.md" and (not index_text or f"({rel})" not in index_text):
            issues.append(f"orphan: {rel} not referenced in INDEX.md")

    missing = [m for m in MODULES if not (DOCS / "omnisys" / m / "README.md").exists()]
    for module in missing:
        issues.append(f"missing module README: omnisys/{module}/README.md")

    for module in MODULES:
        path = DOCS / "omnisys" / module / "README.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for header in REQUIRED_HEADERS:
            if header not in text:
                issues.append(f"{module}: missing header {header!r}")
        status_match = re.search(r"## Status\s*\n+\s*([a-z]+)", text)
        if not status_match:
            issues.append(f"{module}: missing Status value")
        elif status_match.group(1) not in STATUS_VALUES:
            issues.append(f"{module}: invalid Status {status_match.group(1)!r}")

    matrix = DOCS / "CAPABILITY_MATRIX.md"
    if not matrix.exists():
        issues.append("CAPABILITY_MATRIX.md does not exist")
    else:
        expected = gen_capability_matrix.generate()
        if matrix.read_text(encoding="utf-8") != expected:
            issues.append(
                "CAPABILITY_MATRIX.md is out of sync - run python scripts/gen-capability-matrix.py"
            )

    return issues


def main() -> int:
    problems = violations()
    if problems:
        print("docs verification FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("docs verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())