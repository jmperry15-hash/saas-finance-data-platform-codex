"""Offline negative controls for the exact dashboard/warehouse comparison."""

from datetime import date
from decimal import Decimal
import unittest

from scripts.reconcile_dashboard import compare_rows


class DashboardReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.local = [{"month": "2025-01-01", "id": "D01", "cents": 123,
                       "budget": None}]
        self.keys = ("month", "id")

    def test_bigquery_dates_and_integer_decimals_compare_exactly(self):
        cloud = [{**self.local[0], "month": date(2025, 1, 1), "cents": Decimal(123)}]
        self.assertEqual(compare_rows(self.local, cloud, self.keys), 1)

    def test_one_cent_error_null_zero_and_fractional_values_fail(self):
        for change in ({"cents": 124}, {"budget": 0}, {"cents": Decimal("123.01")}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare_rows(self.local, [{**self.local[0], **change}], self.keys)

    def test_duplicate_keys_cannot_hide_behind_matching_counts(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_rows(self.local * 2, self.local * 2, self.keys)

    def test_different_keys_missing_columns_and_empty_data_fail(self):
        for rows in ([{**self.local[0], "id": "D02"}],
                     [{k: v for k, v in self.local[0].items() if k != "budget"}], []):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                compare_rows(self.local, rows, self.keys)


if __name__ == "__main__":
    unittest.main()
