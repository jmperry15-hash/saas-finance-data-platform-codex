"""Fault tests for the first Pandas exercise; no cloud access."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.ingestion.validate_gl import monthly_totals, read_gl, validate_gl
from src.synthetic.schema import SCHEMAS


def sample():
    rows = []
    for line, journal, debit, credit in [("L1", "J1", "100", "0"), ("L2", "J1", "0", "100"), ("L3", "J2", "200", "0"), ("L4", "J2", "0", "200")]:
        rows.append([line, journal, "2026-01-01", "1000", "D01", "", "", "", "test", "S1", debit, credit, "Synthetic test"])
    return pd.DataFrame(rows, columns=SCHEMAS["netsuite/gl_lines"], dtype="string")


class IngestionGLTests(unittest.TestCase):
    def test_csv_round_trip_preserves_ids_and_exact_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gl.csv"
            sample().to_csv(path, index=False)
            frame = read_gl(path)
        self.assertEqual(frame.loc[0, "account_id"], "1000")
        self.assertEqual(frame.loc[0, "customer_id"], "")
        monthly = monthly_totals(frame)
        self.assertEqual(int(monthly.iloc[0]["debit_cents"]), 300)
        self.assertEqual(int(monthly.iloc[0]["difference_cents"]), 0)

    def test_duplicate_line_stops(self):
        frame = sample()
        frame.loc[1, "line_id"] = "L1"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_gl(frame)

    def test_invalid_dates_and_amounts_stop(self):
        for column, value in [("month", "2026-13-01"), ("month", "2026-01-02"), ("debit_cents", "1.5"), ("debit_cents", "-1"), ("debit_cents", str(2**63))]:
            with self.subTest(column=column, value=value):
                frame = sample()
                frame.loc[0, column] = value
                with self.assertRaises(ValueError):
                    validate_gl(frame)

    def test_offsetting_broken_journals_do_not_pass_grand_total(self):
        frame = sample()
        frame.loc[0, "debit_cents"] = "101"
        frame.loc[2, "debit_cents"] = "199"
        with self.assertRaisesRegex(ValueError, "Unbalanced journal"):
            validate_gl(frame)

    def test_missing_columns_blank_required_fields_and_empty_input_stop(self):
        blank = sample()
        blank.loc[0, "journal_id"] = " "
        for frame in [sample().drop(columns=["memo"]), blank, sample().iloc[:0]]:
            with self.assertRaises(ValueError):
                validate_gl(frame)

    def test_both_debit_and_credit_on_one_line_stop(self):
        frame = sample()
        frame.loc[0, "credit_cents"] = "10"
        with self.assertRaisesRegex(ValueError, "both"):
            validate_gl(frame)
