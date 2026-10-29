"""Rebuild dashboard inputs and check finance calculations without cloud access.

All generated files live in a temporary directory. The user's dashboard, source
files and database are never overwritten. Requires Python 3.13 and Node.js.
"""

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.database.load import load_database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/generated")
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="finance-dashboard-check-") as directory:
        folder = Path(directory)
        database = folder / "finance.sqlite"
        load_database(args.source.resolve(), database)
        snapshot = folder / "snapshot.json"
        command = [sys.executable, str(ROOT / "scripts/build_dashboard_snapshot.py"),
                   str(snapshot), "--source", str(args.source.resolve()),
                   "--database", str(database), "--receipt", str(folder / "validation.json")]
        subprocess.run(command, cwd=ROOT, check=True)
        first = json.loads(snapshot.read_text())
        assert first["id"], "Fresh snapshots need a stable artifact identity"
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        assert json.loads(snapshot.read_text())["id"] == first["id"], "Rebuild must preserve identity"
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            # Independently aggregate the source GL; do not reuse dashboard output.
            pnl = [dict(row) for row in connection.execute("""
                SELECT month,
                  SUM(CASE WHEN a.account_type='Revenue' THEN credit_cents-debit_cents ELSE 0 END) revenue_cents,
                  SUM(CASE WHEN a.account_type='Expense' THEN debit_cents-credit_cents ELSE 0 END) expense_cents
                FROM netsuite_gl_lines JOIN netsuite_accounts a USING(account_id)
                GROUP BY month ORDER BY month
            """)]
        for row in pnl:
            row["operating_profit_cents"] = row["revenue_cents"] - row["expense_cents"]
        expected = folder / "pnl.json"
        expected.write_text(json.dumps(pnl))
        subprocess.run([args.node, str(ROOT / "tests/test_dashboard_model.mjs"),
                        str(snapshot), str(expected)], cwd=ROOT, check=True)
    print("PASS: regenerated dashboard inputs and stable identity; no cloud access or local dashboard changes.")


if __name__ == "__main__":
    main()
