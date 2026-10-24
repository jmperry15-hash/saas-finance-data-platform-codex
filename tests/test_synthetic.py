"""Behavioral and fault-injection tests for source contracts and controls."""

import copy
import tempfile
import unittest
from pathlib import Path

from src.synthetic.generate import ROOT, generate, load_config, write_tables
from src.synthetic.validate import read_tables, validate


class SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config(ROOT / "config/scenario.json")
        cls.tables = generate(cls.cfg)

    def test_saved_data_reconciles_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            write_tables(self.tables, a, self.cfg)
            write_tables(generate(self.cfg), b, self.cfg)
            self.assertEqual(validate(read_tables(a), self.cfg)["status"], "PASS")
            for file in a.rglob("*"):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (b / file.relative_to(a)).read_bytes())

    def test_cannot_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "keep.txt").write_text("preserve")
            with self.assertRaisesRegex(ValueError, "not empty"):
                write_tables(self.tables, path, self.cfg)
            self.assertEqual((path / "keep.txt").read_text(), "preserve")

    def test_broken_foreign_key_fails(self):
        tables = copy.deepcopy(self.tables)
        tables["workday/employees"][0]["department_id"] = "MISSING"
        with self.assertRaisesRegex(ValueError, "valid department_id"):
            validate(tables, self.cfg)

    def test_duplicate_primary_key_fails(self):
        tables = copy.deepcopy(self.tables)
        tables["salesforce/customers"].append(tables["salesforce/customers"][0].copy())
        with self.assertRaisesRegex(ValueError, "primary key"):
            validate(tables, self.cfg)

    def test_balanced_but_wrong_revenue_fails(self):
        tables = copy.deepcopy(self.tables)
        journal = next(g["journal_id"] for g in tables["netsuite/gl_lines"] if g["source_type"] == "Revenue")
        for g in tables["netsuite/gl_lines"]:
            if g["journal_id"] == journal:
                g["debit_cents"] += int(g["debit_cents"] > 0)
                g["credit_cents"] += int(g["credit_cents"] > 0)
        with self.assertRaisesRegex(ValueError, "GL revenue reconciles"):
            validate(tables, self.cfg)

    def test_missing_employee_month_fails(self):
        tables = copy.deepcopy(self.tables)
        tables["workday/employee_monthly"].pop()
        with self.assertRaisesRegex(ValueError, "exactly the active"):
            validate(tables, self.cfg)

    def test_plan_mismatch_fails(self):
        tables = copy.deepcopy(self.tables)
        tables["pigment/headcount_plan"][0]["planned_base_pay_cents"] += 100
        with self.assertRaisesRegex(ValueError, "Personnel plan reconciles"):
            validate(tables, self.cfg)

    def test_arr_mutation_fails(self):
        tables = copy.deepcopy(self.tables)
        tables["salesforce/customer_monthly"][0]["arr_cents"] += 100
        with self.assertRaisesRegex(ValueError, "MRR bridge"):
            validate(tables, self.cfg)

    def test_new_seed_and_shorter_horizon(self):
        cfg = dict(self.cfg, seed=123, months=12)
        tables = generate(cfg)
        self.assertEqual(validate(tables, cfg)["status"], "PASS")
        self.assertNotEqual(tables["salesforce/contracts"], self.tables["salesforce/contracts"])

    def test_saas_scenarios_present(self):
        movements = {r["movement"] for r in self.tables["salesforce/customer_monthly"]}
        self.assertTrue({"New", "Expansion", "Contraction", "Churn"} <= movements)
        stages = {r["stage"] for r in self.tables["salesforce/opportunities"]}
        self.assertEqual(stages, {"Closed Won", "Closed Lost", "Proposal"})


if __name__ == "__main__":
    unittest.main()
