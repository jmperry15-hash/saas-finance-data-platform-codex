"""Create a new local database from validated synthetic source files.

python -m src.database.load
Existing databases are never overwritten. Choose another --database for a rebuild.
"""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from src.synthetic.schema import SCHEMAS
from src.synthetic.validate import read_tables, validate

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT / "data/local/saas_finance.sqlite"
# Parents precede children, so foreign keys can be checked as each row is loaded.
LOAD_ORDER = [
    "shared/departments", "netsuite/accounts", "netsuite/vendors",
    "salesforce/customers", "salesforce/opportunities", "salesforce/contracts",
    "salesforce/bookings", "salesforce/customer_monthly", "workday/employees",
    "workday/employee_monthly", "pigment/versions", "pigment/headcount_plan",
    "pigment/financial_plan", "netsuite/gl_lines",
]


def table_name(source):
    return source.replace("/", "_")


def verify_database(conn, source_report):
    """Compare SQL results to controls independently recomputed from the CSVs."""
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Foreign key check failed")
    counts = {name: conn.execute(f'SELECT COUNT(*) FROM "{table_name(name)}"').fetchone()[0] for name in SCHEMAS}
    if counts != source_report["rows"]:
        raise ValueError("Database row counts differ from source files")
    last_month = source_report["period"][1]
    queries = {
        "gl_debits_cents": "SELECT SUM(debit_cents) FROM netsuite_gl_lines",
        "gl_credits_cents": "SELECT SUM(credit_cents) FROM netsuite_gl_lines",
        "revenue_cents": "SELECT SUM(credit_cents - debit_cents) FROM netsuite_gl_lines WHERE account_id = '4000'",
        "bookings_cents": "SELECT SUM(booked_value_cents) FROM salesforce_bookings",
        "personnel_cost_cents": "SELECT SUM(debit_cents - credit_cents) FROM netsuite_gl_lines WHERE account_id IN ('6000', '6010', '6020')",
        "ending_arr_cents": "SELECT SUM(arr_cents) FROM salesforce_customer_monthly WHERE month = ?",
        "ending_paying_customers": "SELECT COUNT(*) FROM salesforce_customer_monthly WHERE month = ? AND mrr_cents > 0",
        "ending_headcount": "SELECT COUNT(*) FROM workday_employee_monthly WHERE month = ?",
        "ending_deferred_revenue_cents": "SELECT SUM(credit_cents - debit_cents) FROM netsuite_gl_lines WHERE account_id = '2100'",
    }
    totals = {}
    for label, sql in queries.items():
        value = conn.execute(sql, (last_month,) if "?" in sql else ()).fetchone()[0]
        totals[label] = value
        if value != source_report["control_totals"][label]:
            raise ValueError("SQL/source reconciliation failed: " + label)
    return {"status": "PASS", "tables": len(counts), "rows_loaded": sum(counts.values()),
            "row_counts": counts, "control_totals": totals,
            "source_validation_checks": source_report["checks_passed"]}


def load_database(source, database):
    source, database = Path(source), Path(database)
    cfg = json.loads((source / "manifest.json").read_text())["config"]
    tables = read_tables(source)
    source_report = validate(tables, cfg)  # Never trust an old PASS report.
    database.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects both the user's database and simultaneous runs.
    with database.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "sql/schema.sql").read_text())
            with conn:  # All inserts succeed together or roll back together.
                for source_name in LOAD_ORDER:
                    columns = SCHEMAS[source_name]
                    sql = 'INSERT INTO "{}" ({}) VALUES ({})'.format(
                        table_name(source_name), ", ".join(columns), ", ".join("?" for _ in columns))
                    values = [tuple(None if row[c] == "" else row[c] for c in columns) for row in tables[source_name]]
                    conn.executemany(sql, values)  # Bind values; never build SQL from CSV text.
                report = verify_database(conn, source_report)
        return report
    except BaseException:
        database.unlink(missing_ok=True)  # Remove only the new failed database.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/generated")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    try:
        report = load_database(args.input, args.database)
        print(json.dumps(report, indent=2))
        print("Database ready: " + str(args.database.resolve()))
    except FileExistsError:
        parser.exit(1, "Database already exists. Query it, or choose a new --database path.\n")
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f"Database load failed: {exc}\n")


if __name__ == "__main__":
    main()
