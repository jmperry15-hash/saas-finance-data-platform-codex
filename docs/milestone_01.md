# Milestone 1: generate and reconcile synthetic source data

## Verified default run

Verified locally on October 24, 2026, using Python 3.9.6 and seed 42:

| Measure | Result |
| --- | --- |
| Source files / rows | 14 CSVs / 23,794 rows |
| Period | October 2024–September 2026 |
| GL lines | 16,648 |
| Customer/prospect master records | 130 |
| Employee master records | 96 |
| Ending paying customers / headcount | 100 / 88 |
| Ending ARR | $7,572,453.60 |
| Revenue over 24 months | $12,343,231.93 |
| Bookings over 24 months, including renewals | $13,760,862.00 |
| Personnel expense over 24 months | $26,104,366.47 |
| Ending deferred revenue | $3,167,384.07 |
| GL debits and credits, each | $77,741,040.10 |
| Validation | 764 checks passed, including repeated record-level checks |
| Automated tests | 10 passed, including corruption and reproducibility tests |

These are fictional financial results, not market benchmarks. The company is
deliberately loss-making as it invests in staffing ahead of revenue. The result
summary describes the default run; your experiments can change the totals.
Full controls and file hashes are in the generated JSON files.

## What you are learning

A **table** is a collection of records with the same columns. Its **grain** says
what one row means. A customer table has one row per customer; a customer-month
table has many rows per customer, but only one per customer and month.

A **primary key** uniquely identifies a row. A **foreign key** points to a row
in another table. Joining on customer ID alone between two monthly tables can
multiply values; customer ID plus month is the correct relationship there.

A **random seed** makes a fictional scenario repeatable. It lets you change code
and distinguish a logic change from newly randomized data. Integer cents avoid
binary floating-point differences when reconciling money. One dollar is 100 cents.

A **virtual environment** isolates this project's Python packages. This milestone
uses only built-in modules: `csv`, `json`, `random`, `datetime`, `pathlib`,
`argparse`, `hashlib`, and `unittest`. Pandas will be useful for inspecting and
reshaping incoming tables later; it is not required just to write these records.

## Scenario and deliberate simplifications

- Fictional Juniper Cloud; 24 completed months, October 2024–September 2026.
- 50 opening customers, 60 new customers during the modeled period, 20 prospects.
  Contracts renew annually, sometimes expand/contract, and sometimes churn.
- 72 opening employees, 24 hires over the window, and some departures; six
  departments. Employee names are obvious synthetic labels.
- Annual prepaid subscriptions; signing, activation and cash collection happen
  on the same first-of-month date. Each contract supplies 12 equal service months.
  End dates are exclusive. No usage revenue, services revenue, cancellations
  inside a term, reactivations, discounts, FX, refunds, bad debt, or AR timing.
- Existing contracts can predate October 2024. Their remaining prepaid service is
  brought in with an opening cash/deferred-revenue entry; historical profits and
  cash flows are not reconstructed. Opening contributed capital is $20 million,
  representing a venture-funded company investing ahead of revenue.
  The cash account is a balancing ledger for this exercise, not a cash forecast.
- Hires start on the first day, terminations occur on the last day, and both get
  a full month's pay. No transfers, promotions, overtime or midmonth proration.
  Salaries increase 4% each January after the reference year. Salaries are
  full-time equivalents; monthly base pay applies FTE and divides by 12.
  Sales variable compensation is 30% of base; others 10%; employer load is 25%.
  All compensation is paid monthly, including modeled variable compensation.
- Hosting scales with MRR; marketing events occur in March/September and audit
  fees in March. Other vendor costs have modest growth and variation.
- Annual budgets are set December 1 of the prior year. H2 forecast versions are
  dated June 30 and cover July onward. Files contain only months within the
  historical analysis window; these versions are historical synthetic estimates.
  Planning drivers are separate from actuals; they are illustrative assumptions,
  not trained forecasts. Plan headcount is a department-level seat count, not a
  list of employee assignments or recruiting requisitions.

## Read the code in this order

1. `config/scenario.json`: the seed, dates, population sizes, and company label.
2. `src/synthetic/schema.py`: the source tables, keys, departments and accounts.
3. `build_sales` in `src/synthetic/generate.py`: customers → opportunities →
   contracts → bookings → customer-month snapshots.
4. `build_people`: employees → payroll snapshots.
5. `build_gl`: double-entry postings derived from the operational records.
6. `build_plans`: independent financial and workforce planning assumptions.
7. `src/synthetic/validate.py`: recompute expectations and check saved CSVs.

The generator validates in memory, writes CSVs and a manifest, reads the CSVs
back, then validates again. A successful generation produces a validation report.
A failed run exits nonzero; inspect the error before proceeding. If a disk write
fails partway through, use a new output directory for the retry. Partial exports
without a successful report are not accepted batches.

## Trace one transaction

Find a row in `salesforce/bookings.csv` and its matching `contract_id` in
`salesforce/contracts.csv`. For a hypothetical $24,000 annual contract:

| Event | Debit | Credit | Amount |
| --- | --- | --- | --- |
| Upfront annual payment | Cash 1000 | Deferred revenue 2100 | $24,000 |
| Each month of service | Deferred revenue 2100 | Revenue 4000 | $2,000 |

The contract's `mrr_cents` is 200000 and ARR is 2400000 cents. The booking is
$24,000 once; recognized revenue is $2,000 each month. This example explains the
generator's mechanics; it is not an additional source record or accounting advice.

Trace an employee similarly: `employee_id` → `employee_monthly` → GL rows with
`source_type=Payroll`. Salaries, variable compensation and benefits post to three
different accounts. Never add employee payroll expense on top of the same GL expense.

## Your short hands-on session

From the repository directory, run:

```bash
source .venv/bin/activate
python -m src.synthetic.validate
python -m unittest discover -s tests -v
```

Then do three exercises before the SQL milestone:

1. Open the dictionary and identify the primary key for GL lines, customers,
   and customer-months. Explain why each grain differs.
2. Copy `config/scenario.json` to `config/practice.json`, change only `seed` to
   7, and run the commands below. Compare ending ARR and headcount. The seed
   changes results; the accounting and relationship checks should still pass.
3. Trace one booking and one payroll row to the GL. Explain why bookings, ARR,
   and revenue cannot be added together.

```bash
python -m src.synthetic.generate --config config/practice.json --output data/generated/seed7
python -m src.synthetic.validate --input data/generated/seed7
```

Do not rerun against an existing nonempty output folder. Use another folder name
to retain your experiment. Generated files are ignored by Git; your practice
configuration is an ordinary file you may choose to commit.

## What the checks prove

Validation checks unique keys, expected columns, types and dates, referential
integrity, population sizes, contract/opportunity/booking consistency, complete
customer-month and employee-month coverage, MRR movements, ARR, payroll amounts,
journal and monthly balance, revenue and payroll ties to the GL, the deferred
revenue rollforward, plan version horizons, and personnel-plan reconciliation.

Tests deliberately corrupt keys, remove a payroll month, change ARR, change plan
expense, and change revenue while keeping its journal balanced. These tests prove
that balancing the GL alone is insufficient. They also verify reproducibility,
saved-file round trips, alternate seed/horizon behavior, and overwrite protection.

This establishes controlled synthetic inputs, not production-ready financial
software. The next milestone is local SQL practice; BigQuery setup comes after it.
