# Milestone 2: learn relational SQL with your finance data

**Status: database and exercises are built and verified; your learning walkthrough
starts here.** We will work through one lesson at a time before moving to BigQuery.

## What changed

Your 14 CSVs now also exist as 14 relational tables in
`data/local/saas_finance.sqlite`. SQLite stores the entire database in one local
file. Python connects directly to it, so there is no server, account, paid tool,
or extra package to install. Your original CSVs remain unchanged.

Think of a table as a structured worksheet: each column has a defined meaning and
each row has a declared grain. SQL asks questions across these tables. Unlike a
spreadsheet lookup, a join can match multiple rows; learning to control those
matches is essential to trustworthy finance reporting.

The source paths become table names by replacing `/` with `_`:
`netsuite/gl_lines.csv` → `netsuite_gl_lines`.
The source [data dictionary](data_dictionary.md) still defines their columns.

## Start here: your first query

In the project terminal:

```bash
source .venv/bin/activate
python -m src.database.query --file sql/lessons/01_select.sql
```

The file contains this query:

```sql
SELECT department_id, department_name, function
FROM shared_departments
ORDER BY department_id;
```

- `SELECT` chooses the columns to show.
- `FROM` chooses the table to read.
- `ORDER BY` sorts the results; it does not change stored records.
- The semicolon ends the statement.

You should see six rows, D01 through D06, starting with Customer Success.
**Try it yourself:** change the last line to `ORDER BY department_name;`, save the
SQL file, and rerun the command. The rows should appear alphabetically. This is
an intentional Git-tracked learning edit; keep it or restore the original order.
Stop here if these three clauses are new. You do not need to read all eight
lessons in one sitting.

## Your finance question: monthly department spending

Once comfortable with lesson 1, run:

```bash
python -m src.database.query --file sql/lessons/03_department_spend.sql
```

```sql
SELECT g.month,
       d.department_name,
       SUM(g.debit_cents - g.credit_cents) / 100.0 AS expense_usd
FROM netsuite_gl_lines AS g
JOIN shared_departments AS d ON g.department_id = d.department_id
JOIN netsuite_accounts AS a ON g.account_id = a.account_id
WHERE a.account_type = 'Expense'
  AND g.month = '2026-09-01'
GROUP BY g.month, d.department_id, d.department_name
ORDER BY expense_usd DESC;
```

Read this in business terms: take September GL entries, attach department and
account labels, keep expense accounts, total expense per department, and show
the largest first. `g`, `d`, and `a` are short table aliases.

`JOIN ... ON` matches records on a shared key. `WHERE` filters individual rows.
`SUM` adds the selected amounts. `GROUP BY` defines one output row per
month/department. `AS` names the output column; `DESC` sorts high to low.
`100.0` converts integer cents to dollars without integer division.

Expected default-scenario result:

| Department | September 2026 expense |
| --- | ---: |
| Engineering | $273,549.92 |
| Finance | $259,404.05 |
| Sales | $251,183.57 |
| Marketing | $220,683.91 |
| Customer Success | $202,170.54 |
| People | $190,315.61 |

Exercise: filter to Engineering, then change the month to August. Before running,
predict how many rows the result will contain. Removing the expense-account
filter is incorrect: cash and other balancing lines are not additional spend.

## Lesson sequence

All lessons are executable, commented examples. Read the SQL before running it,
then make the suggested change yourself. Files later in the sequence are ready
for when you reach them, not required reading today.

| SQL file under `sql/lessons/` | Concept | Your practice |
| --- | --- | --- |
| `01_select.sql` | SELECT, FROM, ORDER BY | Sort department names alphabetically |
| `02_filter.sql` | WHERE, NULL, LIMIT | Find the five largest Sales reference salaries; understand these are roster salaries, not monthly pay |
| `03_department_spend.sql` | JOIN, SUM, GROUP BY | Compare Engineering expense across two months |
| `04_monthly_pnl.sql` | CASE and conditional aggregation | Filter to 2026; explain why revenue and expenses use different signs |
| `05_join_trap.sql` | Many-to-many row multiplication | Explain why $252,750.92 payroll becomes $12,384,795.08 in the deliberately wrong result |
| `06_join_fix.sql` | CTEs, consistent grain, LEFT JOIN | Both sides aggregate to month/department; verify all 144 differences are zero |
| `07_budget_variance.sql` | Plan selection, missing keys, NULLIF | Filter September Engineering; interpret expense and revenue variance direction |
| `08_arr_trend.sql` | LAG and window functions | Compare ending ARR with prior month; explain the first row's NULL change |

Example for viewing all rows of a longer result:

```bash
python -m src.database.query --file sql/lessons/06_join_fix.sql --limit 200
```

The runner displays 50 rows by default and tells you when more exist. It runs
one statement per call. `--limit` changes displayed rows, not the SQL aggregation.
You can also write a short query directly:

```bash
python -m src.database.query --sql "SELECT COUNT(*) AS gl_lines FROM netsuite_gl_lines;"
```

Expected: 16648. The runner opens the database read-only to protect your practice
data. It is a local learning utility, not a security sandbox for untrusted SQL.

## How the database is built

Read `sql/schema.sql` to see the `CREATE TABLE` statements. A **primary key**
prevents duplicate row identities. A **foreign key** requires a referenced parent
record to exist. `NOT NULL` requires a value, while `CHECK` enforces a condition.
For example, customer-month uses `(customer_id, month)` as its primary key.

The loader uses these steps:

1. Read the source manifest configuration and validate the current CSV contents.
2. Exclusively create a new database file; refuse to overwrite an existing one.
3. Enable foreign-key enforcement and execute the table definitions.
4. Load parents before children, turning empty CSV fields into SQL NULL.
5. Insert values through placeholders (`?`) inside one transaction.
6. Check integrity, foreign keys, every table's row count, and nine financial
   control totals. Commit only if these checks pass.

The script removes a newly created failed database if it catches a failure.
An abrupt process termination can still leave an incomplete file; do not assume
that a file's existence means loading succeeded. A successful load prints PASS.
For a fresh clone, generate the CSVs first, then run:

```bash
python -m src.database.load
```

This has already been run locally. To load a new scenario later, retain the
existing practice database and choose a new destination:

```bash
python -m src.database.load --input data/generated/seed7 --database data/local/seed7.sqlite
python -m src.database.query --database data/local/seed7.sqlite --file sql/lessons/01_select.sql
```

That example requires the milestone 1 seed7 exports to exist first. Lesson
filters intentionally use the default scenario's months/version. If you change
the scenario horizon, adjust those SQL filters too.

SQLite dates here are ISO-formatted TEXT; source validation checks dates before
loading. Money is INTEGER cents, with checks that reject non-integer stored
values. Constraints enforce useful rules but do not replace reconciliations:
valid employee and department IDs alone cannot prove correct payroll accounting.
The polymorphic GL `source_id` has different meanings by source type, so it is
not a single foreign key. Its financial relationships are checked upstream.

SQLite requires foreign-key enforcement to be enabled on each writing connection.
[SQLite foreign-key documentation](https://www.sqlite.org/foreignkeys.html).
`LAG` reads a preceding row within the order specified by `OVER`.
[SQLite window-function documentation](https://www.sqlite.org/windowfunctions.html).

## Verified results and milestone gate

The database contains **14 tables and 23,794 source records**. Every table's row
count and all nine financial controls reconcile, including $12,343,231.93 revenue,
$26,104,366.47 personnel expense, $7,572,453.60 ending ARR, and 88 ending employees.
All 19 automated tests pass: the original 10 plus 9 database/SQL tests.
Tests check every loaded cell, rejected duplicate/orphan records, money rules,
safe repeat loads, failed-load cleanup, read-only queries, query reconciliations,
join multiplication, and budget-only/actual-only/zero-budget cases.

Before milestone 3, you should be able to explain a table's grain, write a simple
filtered total, join dimensions without multiplying amounts, demonstrate why
the bad payroll join fails, and interpret missing/zero plan values. The technical
lab is ready; your practice is the remaining gate. BigQuery is not configured.
