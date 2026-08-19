"""Automated test suite for the OmniScript inventory management system.

Verifies (against `source/inventory.omni` and the OMNISYS.db runtime):
  1. The program type-checks / effect-checks with the compiler (`check`, exit 0).
  2. The capability model enforces declared data access (database capability):
     functions that call OMNISYS.db.* must declare `uses database`; omitting
     the declaration fails check with E-EFFECT-003.
  3. CRUD, validation, transactions (atomic stock adjustment + matching
     movement record), rollback-on-failure, relationships, and low-stock /
     category / prefix queries by EXECUTING the compiled JS artifact (built
     with `--target js`) under Node and asserting on the machine-readable
     `KEY value` output emitted by the program's scenario runner.
  4. A pure-Python cross-check that replays the same transaction logic against
     the canonical Python mirror of OMNISYS.db (`omnisys_db`) and asserts the
     same invariants.

Run from the repo root:  python -m pytest tests/test_inventory.py -p no:cacheprovider
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import omnisys_db
import pytest

RUN_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = RUN_DIR / "source"
PROBES_DIR = RUN_DIR / "probes"
OMNI_FILE = SOURCE_DIR / "inventory.omni"
HARNESS_JS = PROBES_DIR / "harness.js"
BUILD_DIR = RUN_DIR / "tests" / "_build"

# Repo root = E:\\simualtion (5 levels above the run dir's tests/).
REPO_ROOT = Path(__file__).resolve().parents[5]
assert (REPO_ROOT / "omni_compiler" / "cli.py").exists(), f"unexpected repo root: {REPO_ROOT}"

EXPECTED_MOVEMENTS = "1|1|10|restock;2|2|-2|sale;"


def run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run `python -m omni_compiler.cli ...` from the repo root."""
    cmd = [sys.executable, "-m", "omni_compiler.cli", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        pytest.fail(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc


def build_js() -> Path:
    """Build source/inventory.omni to a JS/HTML artifact and return its path."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    out = BUILD_DIR / "inventory.html"
    run_cli("build", str(OMNI_FILE), "--target", "js", "-o", str(out))
    assert out.exists(), f"build did not produce {out}"
    return out


def run_js(html: Path) -> str:
    """Execute the built artifact under Node (with the harness shim) and return stdout."""
    if not HARNESS_JS.exists():
        pytest.fail(f"harness not found: {HARNESS_JS}")
    proc = subprocess.run(
        ["node", str(HARNESS_JS), str(html)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node failed ({proc.returncode}): {proc.stdout}\n{proc.stderr}"
    return proc.stdout


def scenario_output() -> dict[str, str]:
    """Build + run the program and parse `KEY value` output lines.

    A bare key line (`show "SCHEMA_PRODUCTS"`) followed by a non-key line
    (console.log of an object) is paired with that following line as its value.
    """
    out = run_js(build_js())
    lines = out.splitlines()
    parsed: dict[str, str] = {}
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z_][A-Z0-9_]*)(?: (.*))?$", line.strip())
        if m:
            key = m.group(1)
            value = (m.group(2) or "").strip()
            if not value and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if not re.match(r"^[A-Z_][A-Z0-9_]* ", nxt):
                    value = nxt
            parsed[key] = value
    return parsed


# ---------------------------------------------------------------------------
# 1. Compilation / effect-checking
# ---------------------------------------------------------------------------


def test_check_exits_zero() -> None:
    proc = run_cli("check", str(OMNI_FILE))
    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_run_command_executes_program() -> None:
    """`omni run` compiles and executes the program under Node, exit 0."""
    proc = run_cli("run", str(OMNI_FILE))
    assert proc.returncode == 0
    assert "done" in proc.stdout  # entry-point scenario ran to completion
    assert "COUNT_CATEGORIES 3" in proc.stdout


def test_inventory_functions_declare_database_capability() -> None:
    """Every function that calls OMNISYS.db.* declares `uses database`."""
    from omni_compiler.checker import analyze
    from omni_compiler.lexer import tokenize
    from omni_compiler.parser import FunctionCall, parse

    code = OMNI_FILE.read_text(encoding="utf-8")
    ast = parse(tokenize(code))
    analyze(ast)

    def walks_expr(expr, out: list[str]) -> None:
        from omni_compiler.parser import BinaryExpr, FieldAccess, ListLiteral, StructConstruct

        if isinstance(expr, FunctionCall):
            out.append(expr.name)
            for a in expr.args:
                walks_expr(a, out)
        elif isinstance(expr, (BinaryExpr, FieldAccess)):
            walks_expr(expr.left if isinstance(expr, BinaryExpr) else expr.object, out)
            if isinstance(expr, BinaryExpr):
                walks_expr(expr.right, out)
        elif isinstance(expr, StructConstruct):
            for v in expr.args.values():
                walks_expr(v, out)
        elif isinstance(expr, ListLiteral):
            for i in expr.items:
                walks_expr(i, out)

    for fn in ast.functions:
        calls: list[str] = []
        for stmt in fn.body:
            walks_expr(stmt, calls)
        uses_db = any(name.startswith("OMNISYS.db.") for name in calls)
        declares = "database" in fn.effects.get("uses", [])
        if uses_db:
            assert declares, (
                f"{fn.name} calls OMNISYS.db.* but does not declare `uses database` "
                f"(declared uses: {fn.effects.get('uses', [])})"
            )
        # reverse direction: declared `uses database` but no db call would be a
        # benign over-declaration; not asserted.


def test_capability_model_rejects_undeclared_database_access() -> None:
    """A db call without `uses database` must fail check with E-EFFECT-003."""
    probe = BUILD_DIR / "undeclared_db.omni"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import OMNISYS.db\n"
        "\n"
        "fn sneaky() -> None:\n"
        "    d = OMNISYS.db.create_db(\"x\")\n"
        "    show d\n"
        "end\n"
        "\n"
        "when app starts:\n"
        "    sneaky()\n"
        "end\n",
        encoding="utf-8",
    )
    proc = run_cli("check", str(probe), check=False)
    assert proc.returncode == 1
    assert "E-EFFECT-003" in proc.stdout
    assert "Capability database used without declaration" in proc.stdout


def test_capability_model_rejects_pure_with_database_effect() -> None:
    """A `pure` function performing db access must fail check with E-EFFECT-001."""
    probe = BUILD_DIR / "pure_db.omni"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import OMNISYS.db\n"
        "\n"
        "fn bad() -> None:\n"
        "    pure\n"
        "    d = OMNISYS.db.create_db(\"x\")\n"
        "    show d\n"
        "end\n"
        "\n"
        "when app starts:\n"
        "    bad()\n"
        "end\n",
        encoding="utf-8",
    )
    proc = run_cli("check", str(probe), check=False)
    assert proc.returncode == 1
    assert "E-EFFECT-001" in proc.stdout
    assert "declared 'pure' but uses" in proc.stdout


# ---------------------------------------------------------------------------
# 2. End-to-end execution of the compiled artifact (Node)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scenario() -> dict[str, str]:
    return scenario_output()


def test_scenario_crud_counts(scenario: dict[str, str]) -> None:
    assert scenario["COUNT_CATEGORIES"] == "3"
    assert scenario["COUNT_PRODUCTS"] == "5"


def test_scenario_validation_rejects_negative_values(scenario: dict[str, str]) -> None:
    assert scenario["REJECT_NEG_PRICE"] == "reject:negative-price"
    assert scenario["REJECT_NEG_STOCK"] == "reject:negative-stock"
    assert scenario["COUNT_PRODUCTS_AFTER_REJECT"] == "5"  # nothing was inserted


def test_scenario_crud_update_read_delete(scenario: dict[str, str]) -> None:
    assert scenario["UPDATED_PRICE"] == "ok"
    assert scenario["PAN_PRICE"] == "28"
    assert scenario["RENAMED_CATEGORY"] == "ok"
    assert scenario["DELETED_PRODUCT"] == "1"
    assert scenario["COUNT_PRODUCTS_AFTER_DELETE"] == "4"


def test_scenario_transactions_atomic_adjustment_and_movement(
    scenario: dict[str, str],
) -> None:
    """Every successful stock adjustment produced exactly one matching movement;
    failed adjustments changed nothing and produced no movement."""
    assert scenario["ADJUST_1"] == "ok"
    assert scenario["ADJUST_2"] == "ok"
    assert scenario["ADJUST_3"] == "reject:insufficient-stock"
    assert scenario["ADJUST_4"] == "reject:zero-delta"
    assert scenario["HAMMER_STOCK"] == "30"  # 20 + 10
    assert scenario["MOVEMENT_COUNT"] == "2"
    assert scenario["MOVEMENTS"] == EXPECTED_MOVEMENTS  # deltas match adjustments


def test_scenario_rollback_on_failure(scenario: dict[str, str]) -> None:
    """A late failure (invalid movement) rolls the stock change back and leaves
    no movement record behind."""
    assert scenario["ADJUST_ROLLBACK"] == "reject:rollback-done"
    assert scenario["PAN_STOCK_AFTER_ROLLBACK"] == "7"  # unchanged
    assert scenario["MOVEMENT_COUNT_AFTER_ROLLBACK"] == "2"  # unchanged


def test_scenario_queries_relationships(scenario: dict[str, str]) -> None:
    assert scenario["CATEGORY_QUERY"] == "3|pan|7;"  # kitchen
    assert scenario["LOW_STOCK"] == "2|drill|2;"  # threshold 5
    assert scenario["PREFIX_QUERY"] == "1|hammer|30;"  # prefix "ha"
    assert scenario["JOIN_VIEW"] == (
        "1|hammer|tools;2|drill|tools;3|pan|kitchen;4|shovel|outdoor;6|spade|outdoor;"
    )
    assert "Text" in scenario["SCHEMA_PRODUCTS"]  # schema introspection round-trip


# ---------------------------------------------------------------------------
# 3. Pure-Python cross-check of the transaction logic against OMNISYS.db's
#    canonical Python mirror (omnisys_db).
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> dict:
    import omnisys_db

    database = omnisys_db.create_db("inventory")
    categories = omnisys_db.create_table(
        database,
        "categories",
        {"name": "Text"},
    )
    products = omnisys_db.create_table(
        database,
        "products",
        {"name": "Text", "price": "Text", "stock": "Text", "category_id": "Text"},
    )
    movements = omnisys_db.create_table(
        database,
        "movements",
        {"product_id": "Text", "delta": "Text", "note": "Text", "ts": "Text"},
    )
    return {"database": database, "categories": categories, "products": products, "movements": movements}


def _insert(db_dict, name, price, stock, category_id) -> str:
    if price < 0:
        return "reject:negative-price"
    if stock < 0:
        return "reject:negative-stock"
    omnisys_db.insert(db_dict["products"], {"name": name, "price": price, "stock": stock, "category_id": category_id})
    return "ok"


def _adjust(db_dict, pid, delta, note) -> str:
    """Mirror of inventory.omni's adjust_stock (validate-before-mutate)."""
    rows = omnisys_db.select(db_dict["products"], lambda r: r["id"] == pid)
    assert len(rows) == 1
    current = rows[0]["stock"]
    if delta == 0:
        return "reject:zero-delta"
    if current + delta < 0:
        return "reject:insufficient-stock"
    omnisys_db.update(db_dict["products"], lambda r: r["id"] == pid, {"stock": current + delta})
    omnisys_db.insert(
        db_dict["movements"],
        {"product_id": pid, "delta": delta, "note": note, "ts": 0},
    )
    return "ok"


def test_python_mirror_atomic_adjustment(db) -> None:
    import omnisys_db

    _insert(db, "hammer", 12, 20, 1)
    _insert(db, "drill", 80, 4, 1)
    assert _adjust(db, 1, 10, "restock") == "ok"
    assert _adjust(db, 2, -2, "sale") == "ok"
    assert _adjust(db, 1, 0, "noop") == "reject:zero-delta"
    assert _adjust(db, 2, -50, "sale") == "reject:insufficient-stock"

    rows = {r["id"]: r for r in omnisys_db.select(db["products"], None)}
    assert rows[1]["stock"] == 30
    assert rows[2]["stock"] == 2

    moves = omnisys_db.select(db["movements"], None)
    assert len(moves) == 2
    assert moves[0]["product_id"] == 1 and moves[0]["delta"] == 10
    assert moves[1]["product_id"] == 2 and moves[1]["delta"] == -2


def test_python_mirror_rollback_via_compensation(db) -> None:
    """Simulates the compensation-based rollback path from inventory.omni."""
    import omnisys_db

    _insert(db, "pan", 25, 7, 2)
    pid = 1
    delta = 5
    note = ""
    current = omnisys_db.select(db["products"], lambda r: r["id"] == pid)[0]["stock"]

    # step 1: mutate stock
    omnisys_db.update(db["products"], lambda r: r["id"] == pid, {"stock": current + delta})
    # step 2: movement validation fails -> compensate
    if note == "":
        omnisys_db.update(db["products"], lambda r: r["id"] == pid, {"stock": current})
        status = "reject:rollback-done"
    else:  # pragma: no cover - mirror branch never taken with note=""
        omnisys_db.insert(db["movements"], {"product_id": pid, "delta": delta, "note": note, "ts": 0})
        status = "ok"

    assert status == "reject:rollback-done"
    stock_after = omnisys_db.select(db["products"], lambda r: r["id"] == pid)[0]["stock"]
    assert stock_after == current
    assert len(omnisys_db.select(db["movements"], None)) == 0


def test_python_mirror_queries_relationships(db) -> None:
    import omnisys_db

    for name in ("tools", "kitchen", "garden"):
        omnisys_db.insert(db["categories"], {"name": name})
    for name, price, stock, cid in (
        ("hammer", 12, 20, 1),
        ("drill", 80, 4, 1),
        ("pan", 25, 7, 2),
        ("shovel", 30, 12, 3),
    ):
        _insert(db, name, price, stock, cid)

    low = omnisys_db.select(db["products"], lambda r: r["stock"] < 5)
    assert [r["name"] for r in low] == ["drill"]

    kitchen_products = omnisys_db.select(db["products"], lambda r: r["category_id"] == 2)
    assert [r["name"] for r in kitchen_products] == ["pan"]

    joined = [
        (r["name"], c["name"])
        for r in omnisys_db.select(db["products"], None)
        for c in omnisys_db.select(db["categories"], None)
        if r["category_id"] == c["id"]
    ]
    assert ("hammer", "tools") in joined
    assert ("pan", "kitchen") in joined