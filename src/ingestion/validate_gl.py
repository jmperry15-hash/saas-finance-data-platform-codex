"""Read a synthetic GL CSV with Pandas, validate it, and print monthly totals.

This exercise is read-only: no cloud calls and no output files.
"""

import argparse
from pathlib import Path

import pandas as pd

from src.synthetic.schema import SCHEMAS

ROOT = Path(__file__).resolve().parents[2]
MONEY_COLUMNS = ["debit_cents", "credit_cents"]
OPTIONAL_COLUMNS = {"customer_id", "employee_id", "vendor_id"}


def read_gl(path):
    # Start with text so numeric-looking IDs stay IDs and cents aren't rounded.
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    return validate_gl(frame)


def validate_gl(frame):
    """Return a typed copy only after every control passes; never repair bad data."""
    if list(frame.columns) != list(SCHEMAS["netsuite/gl_lines"]):
        raise ValueError("GL columns must match the source schema in order.")
    if frame.empty:
        raise ValueError("GL must contain at least one row.")
    frame = frame.copy()
    required = [c for c in frame.columns if c not in OPTIONAL_COLUMNS]
    if frame[required].isna().any().any() or frame[required].apply(lambda col: col.str.strip().eq("")).any().any():
        raise ValueError("Required GL fields cannot be blank.")
    if frame["line_id"].duplicated().any():
        raise ValueError("Duplicate line_id: each GL line must be unique.")

    if not frame["month"].str.fullmatch(r"\d{4}-\d{2}-01").all():
        raise ValueError("month must use YYYY-MM-01.")
    frame["month"] = pd.to_datetime(frame["month"], format="%Y-%m-%d", errors="raise")

    for column in MONEY_COLUMNS:
        if not frame[column].str.fullmatch(r"[0-9]+").all():
            raise ValueError(column + " must contain nonnegative integer cents.")
        # Check with Python integers before using fixed-width Pandas arithmetic.
        if sum(int(value) for value in frame[column]) > 2**63 - 1:
            raise ValueError(column + " exceeds this exercise's INT64 total limit.")
        frame[column] = frame[column].astype("int64")
    if ((frame["debit_cents"] > 0) & (frame["credit_cents"] > 0)).any():
        raise ValueError("A GL line cannot contain both a debit and a credit.")

    # A balanced grand total alone can hide two offsetting broken journals.
    journals = frame.groupby(["month", "journal_id"])[MONEY_COLUMNS].sum()
    if not journals["debit_cents"].eq(journals["credit_cents"]).all():
        raise ValueError("Unbalanced journal: debits must equal credits within each month/journal.")
    return frame


def monthly_totals(frame):
    """GROUP BY month in SQL is groupby('month') in Pandas."""
    monthly = frame.groupby("month")[MONEY_COLUMNS].sum()
    monthly["difference_cents"] = monthly["debit_cents"] - monthly["credit_cents"]
    return monthly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/generated/netsuite/gl_lines.csv")
    args = parser.parse_args()
    try:
        frame = read_gl(args.input)
        monthly = monthly_totals(frame)
    except (ValueError, OSError, OverflowError) as exc:
        parser.exit(1, f"Validation failed: {exc}\n")
    print(f"PASS: {len(frame):,} GL lines across {len(monthly)} months")
    print("Checks: columns, required fields, unique line IDs, dates, integer cents, journal balances")
    print(f"Total debits:  ${frame['debit_cents'].sum() / 100:,.2f}")
    print(f"Total credits: ${frame['credit_cents'].sum() / 100:,.2f}")
    print(f"Difference:    ${(frame['debit_cents'].sum() - frame['credit_cents'].sum()) / 100:,.2f}")
    print("\nFirst twelve months (USD; integer cents converted only for display):")
    display = monthly.head(12).div(100).rename(columns=lambda name: name.replace("_cents", "_usd"))
    print(display.to_string(float_format=lambda value: f"{value:,.2f}"))


if __name__ == "__main__":
    main()
