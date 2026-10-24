"""Verify relational constraints, preservation, and the finance SQL lessons."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.database.load import ROOT, load_database
from src.database.query import run_query
from src.synthetic.generate import generate, load_config, write_tables


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name) / "source"
        cls.database = Path(cls.temp.name) / "test.sqlite"
        cfg = load_config(ROOT / "config/scenario.json")
        cls.tables = generate(cfg)
        write_tables(cls.tables, cls.source, cfg)
        cls.report = load_database(cls.source, cls.database)

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        original = sqlite3.connect(self.database)
        try:
            original.backup(self.conn)
        finally:
            original.close()
        self.conn.execute("PRAGMA foreign_keys = ON")

    def lesson(self, name):
        return self.conn.execute((ROOT / "sql/lessons" / name).read_text()).fetchall()

    def test_every_source_cell_survives_load(self):
        for name, rows in self.tables.items():
            expected = {tuple(None if value == "" else value for value in row.values()) for row in rows}
            actual = set(self.conn.execute('SELECT * FROM "' + name.replace("/", "_") + '"'))
            self.assertEqual(actual, expected, name)
        self.assertEqual(self.report["status"], "PASS")

    def test_database_rejects_duplicate_null_key_and_orphan(self):
        bad_statements = [
            "INSERT INTO shared_departments VALUES ('D01', 'Duplicate', 'Test')",
            "INSERT INTO shared_departments VALUES (NULL, 'Missing key', 'Test')",
            "UPDATE workday_employees SET department_id = 'MISSING' WHERE employee_id = 'E0001'",
        ]
        for sql in bad_statements:
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql)

    def test_database_rejects_bad_money_and_unbalanced_line(self):
        for sql in [
            "UPDATE workday_employee_monthly SET base_pay_cents = 'bad' WHERE employee_id = 'E0001'",
            "UPDATE netsuite_gl_lines SET debit_cents = 1, credit_cents = 1 WHERE line_id = 'L000001'",
            "UPDATE salesforce_customer_monthly SET arr_cents = arr_cents + 1 WHERE customer_id = 'C0001'",
        ]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql)

    def test_repeat_load_preserves_existing_database(self):
        before = self.database.read_bytes()
        with self.assertRaises(FileExistsError):
            load_database(self.source, self.database)
        self.assertEqual(self.database.read_bytes(), before)

    def test_failed_reconciliation_removes_new_database(self):
        destination = Path(self.temp.name) / "failed.sqlite"
        with patch("src.database.load.verify_database", side_effect=ValueError("Injected mismatch")):
            with self.assertRaisesRegex(ValueError, "Injected mismatch"):
                load_database(self.source, destination)
        self.assertFalse(destination.exists())
        self.assertTrue(self.database.exists())

    def test_query_runner_protects_data_and_reports_truncation(self):
        columns, rows, truncated = run_query(self.database, "SELECT * FROM shared_departments", 2)
        self.assertEqual(columns[0], "department_id")
        self.assertEqual(len(rows), 2)
        self.assertTrue(truncated)
        with self.assertRaises(sqlite3.OperationalError):
            run_query(self.database, "DELETE FROM shared_departments")
        missing = Path(self.temp.name) / "missing.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            run_query(missing, "SELECT 1")
        self.assertFalse(missing.exists())

    def test_lessons_reconcile_to_source(self):
        self.assertEqual(len(self.lesson("01_select.sql")), 6)
        self.assertEqual(len(self.lesson("02_filter.sql")), 5)
        expenses = {a["account_id"] for a in self.tables["netsuite/accounts"] if a["account_type"] == "Expense"}
        expected_spend = sum(g["debit_cents"] - g["credit_cents"] for g in self.tables["netsuite/gl_lines"] if g["month"] == "2026-09-01" and g["account_id"] in expenses)
        self.assertEqual(round(sum(r[2] for r in self.lesson("03_department_spend.sql")) * 100), expected_spend)
        pnl = self.lesson("04_monthly_pnl.sql")
        self.assertEqual(len(pnl), 24)
        self.assertEqual(round(sum(r[1] for r in pnl) * 100), self.report["control_totals"]["revenue_cents"])
        self.assertTrue(all(abs(r[1] - r[2] - r[3]) < 0.00001 for r in pnl))
        trend = self.lesson("08_arr_trend.sql")
        self.assertIsNone(trend[0][3])
        self.assertIsNone(trend[0][4])
        self.assertEqual(round(trend[-1][2] * 100), self.report["control_totals"]["ending_arr_cents"])
        self.assertEqual(trend[-1][1], self.report["control_totals"]["ending_paying_customers"])

    def test_join_trap_and_fix(self):
        correct, wrong, joined, employees = self.lesson("05_join_trap.sql")[0]
        self.assertGreater(wrong, correct)
        self.assertGreater(joined, employees)
        fixed = self.lesson("06_join_fix.sql")
        self.assertEqual(len(fixed), 144)
        self.assertTrue(all(r[4] == 0 for r in fixed))
        self.assertEqual(round(sum(r[2] for r in fixed) * 100), self.report["control_totals"]["personnel_cost_cents"])

    def test_budget_query_retains_one_sided_keys_and_zero_denominator(self):
        base = self.lesson("07_budget_variance.sql")
        self.assertEqual(len(base), 225)
        self.assertTrue(all(r[9] == "Both" for r in base))
        expected_plan = sum(p["amount_cents"] for p in self.tables["pigment/financial_plan"] if p["version_id"] == "BUD2026")
        self.assertEqual(round(sum(r[6] for r in base) * 100), expected_plan)
        # Changes stay in an in-memory test copy, never in the learning database.
        self.conn.execute("DELETE FROM pigment_financial_plan WHERE version_id = 'BUD2026' AND month = '2026-09-01' AND department_id = 'D02' AND account_id = '6000'")
        self.conn.execute("INSERT INTO pigment_financial_plan VALUES ('BUD2026', '2026-09-01', 'D06', '6400', 50000)")
        self.conn.execute("UPDATE pigment_financial_plan SET amount_cents = 0 WHERE version_id = 'BUD2026' AND month = '2026-09-01' AND department_id = 'D03' AND account_id = '4000'")
        rows = self.lesson("07_budget_variance.sql")
        self.assertEqual(len(rows), 226)
        actual_only = next(r for r in rows if r[:3] == ("2026-09-01", "D02", "6000"))
        self.assertEqual(actual_only[9], "Actual only")
        self.assertIsNone(actual_only[8])
        plan_only = next(r for r in rows if r[:3] == ("2026-09-01", "D06", "6400"))
        self.assertEqual(plan_only[9], "Plan only")
        self.assertEqual(plan_only[5:8], (0, 500, -500))
        zero_budget = next(r for r in rows if r[:3] == ("2026-09-01", "D03", "4000"))
        self.assertIsNone(zero_budget[8])


if __name__ == "__main__":
    unittest.main()
