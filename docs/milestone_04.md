# Milestone 4 — Python ingestion and API practice

## Step 1: understand a Pandas DataFrame

Pandas is a Python library for working with tables. A DataFrame holds rows and
columns, much like a worksheet. We use it between extraction and loading to check
types and reject bad inputs. SQL/dbt will handle warehouse reporting models later.

This first exercise reads just the synthetic NetSuite GL CSV. It does not connect
to Google Cloud, request credentials, upload records, or change source files.

The project now has a separate `.venv-ingestion` environment built with the
existing Python 3.13 on this Mac. A virtual environment keeps this project's
packages separate from other projects. The original `.venv` is preserved for
earlier lessons. Use the new environment for the complete test suite.

## Run it on your Mac

Open Terminal on your Mac (not Cloud Shell), then paste:

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-ingestion/bin/python -m src.ingestion.validate_gl
```

Already verified locally:

```text
PASS: 16,648 GL lines across 24 months
Total debits:  $77,741,040.10
Total credits: $77,741,040.10
Difference:    $0.00
```

It also displays five monthly totals. These are GL debit/credit activity, not
revenue or P&L measures: balance-sheet activity is included.

## Read these four operations

Open `src/ingestion/validate_gl.py` and find:

| Python operation | Meaning | Familiar equivalent |
| --- | --- | --- |
| `pd.read_csv(..., dtype="string")` | Read the CSV initially as text | Import a worksheet with explicit text IDs |
| `.duplicated()` | Detect repeated line IDs | Duplicate-key check |
| `.astype("int64")` | Convert validated cents to whole numbers | Enforce a numeric column type |
| `.groupby("month")[MONEY_COLUMNS].sum()` | Aggregate debits and credits by month | SQL `GROUP BY` or a pivot table |

`keep_default_na=False` preserves literal strings such as `NA` and leaves optional
blank IDs as empty text. We explicitly reject blank required fields. Dates must
be valid month-start dates. Money stays in integer cents until display; no float
rounding is used in the accounting controls.

The validator checks exact columns, required values, unique line IDs, dates,
nonnegative integer cents, and balance by month/journal. It rejects errors instead
of silently dropping rows. Cross-table foreign keys and complete source coverage
still rely on the broader `src.synthetic.validate` controls; this exercise alone
cannot detect removal of an entire balanced journal.

## Your small exercise

Run the command, then locate `monthly.head(5)` in the script. It limits the output
to five months; all 24 months are still validated. Change it to `monthly.head(12)`
and rerun to display twelve months. The grand totals should remain unchanged.

Stop here until this feels clear. Next we will discuss a reusable Python BigQuery
loader, rerun behavior, and authentication; then a local mock API and failure handling.
Those components are not implemented by this step.

## Recreate and test the environment

The initial setup is already done on this Mac. For a fresh checkout with Python
3.13 installed, run from the project root:

```bash
python3.13 -m venv .venv-ingestion
.venv-ingestion/bin/python -m pip install -r requirements-ingestion.txt
.venv-ingestion/bin/python -m unittest discover -s tests
```

All 42 tests passed locally, including six Pandas tests covering duplicate IDs,
invalid dates/amounts, missing fields, and offsetting unbalanced journals.
These offline tests do not establish a cloud refresh result.

Reference: [Pandas getting started](https://pandas.pydata.org/docs/getting_started/).
