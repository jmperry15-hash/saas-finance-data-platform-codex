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

The user completed this exercise on October 26, 2026 and displayed twelve months.
Local authentication and the single-table Python loader are now ready. The mock
API and a pipeline for refreshing all sources remain later exercises.

## Step 2: local Google Cloud CLI and sign-in

On October 26, Google Cloud CLI 590.0.1 was installed at
`/Users/jackperry/google-cloud-sdk` from Google's official Apple Silicon archive.
The archive SHA256 matched the published checksum. The installer added PATH and
completion entries to `~/.zshrc`, with its backup at `~/.zshrc.backup`.
A fresh zsh session successfully ran `gcloud --version` (including `bq 2.1.41`).
Usage reporting is disabled. No billing settings or cloud resources were changed.

Sign-in succeeded on October 26: the user's Terminal confirmed CLI login and ADC
were updated. For a future setup, open a **new Terminal window on your Mac** and run:

```bash
gcloud --version
gcloud auth login --update-adc --project=saas-finance-learning-512616
```

Complete the Google browser sign-in yourself with the account used for BigQuery.
`--update-adc` saves Application Default Credentials so Python's Google client
libraries can authenticate too. Credentials are stored outside this repository;
do not copy credential files or authorization codes into Git or chat.
The project flag selects context for this command; later cloud operations must
also explicitly target `saas-finance-learning-512616`.

Read-only checks from this Mac also succeeded on October 26: billing is disabled,
no billing account is linked, `raw_netsuite` is in `us-south1` with both defaults
at 59 days, and `raw_netsuite.gl_lines` contains 16,648 rows. These checks used
the CLI. Python ADC authentication and the read-only destination checks also
passed on October 26. The first actual refresh with the Python client is pending.

An already-open Terminal may not have the updated command path. Load it with:

```bash
source /Users/jackperry/google-cloud-sdk/path.zsh.inc
gcloud --version
```

`bq` also needs `gcloud` on PATH for authentication; using only the full path to
`bq` is insufficient. Local subprocesses must inherit the SDK's bin directory
on PATH. No queries or loads were run during these metadata checks.

Sources: [Google CLI installation](https://docs.cloud.google.com/sdk/docs/install-sdk),
[login and the update-adc flag](https://docs.cloud.google.com/sdk/gcloud/reference/auth/login).

## Step 3: refresh the GL with Python

`src/ingestion/load_gl.py` now uses Google's Python BigQuery client. Pandas validates
the GL; the client uploads the original validated CSV bytes with explicit types.
No Arrow/Parquet dependency or Cloud Storage bucket is needed for this CSV lesson.

From this project's folder in your Mac Terminal:

```bash
# Local validation and preview only:
.venv-ingestion/bin/python -m src.ingestion.load_gl

# Local validation plus live read-only billing/table checks:
.venv-ingestion/bin/python -m src.ingestion.load_gl --check

# Replace this project's existing GL table, then verify:
.venv-ingestion/bin/python -m src.ingestion.load_gl --upload
```

The destination is deliberately fixed to
`saas-finance-learning-512616.raw_netsuite.gl_lines` in `us-south1` for this lesson.
It must already exist with the expected schema and Sandbox expiration. The loader
checks billing with the same ADC identity as BigQuery and stops if billing is
enabled, linked, or unknown. It never enables services or changes billing.

The sequence is:

1. Compare the GL file hash with the synthetic generator's manifest, run Pandas
   validation and the full source reconciliation, and retain the exact bytes in memory.
2. Check billing and destination metadata before any load. Input is capped at 25 MiB.
3. Submit one batch job using `WRITE_TRUNCATE` and `CREATE_NEVER`. Successful loads
   replace rows rather than append them; no SQL DML is used. A new run gets a new
   job ID, but the same source should leave the same rows and totals.
4. Verify schema, row count, unchanged expiration, and exact debit/credit totals.
   The verification SELECT has a 10 MiB maximum-bytes-billed limit and bypasses
   query caching. It should return 16,648 rows and 7,774,104,010 cents on each side.

Only the GL is refreshed. A complete all-source refresh, cross-source cloud
reconciliation, ingestion timestamps, mock API, and scheduling are still unbuilt.
Run one loader at a time. Don't modify sources or the destination during a load.
This is a full-table learning refresh for a small synthetic table, not an
incremental production design. Hashes protect against accidental file edits;
they are not proof of provenance against a deliberately altered manifest.

If a request times out, a submitted job may still finish. The script prints its
job ID before submission and does not automatically submit a replacement job.
Inspect that job in BigQuery Job history before retrying. A verification failure
after a successful load does not roll the table back. Repeated uploads still
consume Sandbox quota, so do not loop or schedule this exercise yet.

Status: preview logic and ten new loader tests pass, including a simulated double
refresh, blocked billing states, invalid destination settings, and failed jobs.
The live `--check` succeeded; `--upload` and a repeated cloud refresh are not yet
verified. The earlier Cloud Shell uploads remain the currently verified data load.

Source: [Google's Python BigQuery client](https://docs.cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client).

## Recreate and test the environment

The initial setup is already done on this Mac. For a fresh checkout with Python
3.13 installed, run from the project root:

```bash
python3.13 -m venv .venv-ingestion
.venv-ingestion/bin/python -m pip install -r requirements-ingestion.txt
.venv-ingestion/bin/python -m unittest discover -s tests
```

All 52 tests passed locally, including six Pandas tests and ten Python loader tests.
The BigQuery client requires python-dateutil below 3, so the environment and
requirements now use the compatible 2.9.0.post0 version; `pip check` passes.
These offline tests do not establish a cloud refresh result.

Reference: [Pandas getting started](https://pandas.pydata.org/docs/getting_started/).
