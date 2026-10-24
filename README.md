# Miniature SaaS Finance Data Platform

**Current cloud status, October 24, 2026:** you disabled billing for
`saas-finance-learning-512616`; the screenshot and subsequent uploader run show
the billing gate passed. Continue without a billing override. The helper now
reuses the existing raw dataset location instead of requiring US; see the
[updated continuation command](docs/bigquery_bulk_upload.md).

A hands-on learning project for Jack: connect familiar FP&A concepts to Python,
relational data, BigQuery, dbt, automation, and Streamlit.

**Status: milestone 1 complete; milestone 2 SQL lab verified; milestone 3 setup started.** The
synthetic source generator, local SQLite database, SQL lessons, validation, tests,
and documentation are implemented. Cloud ingestion, dbt, APIs, Actions, and the
dashboard are planned. BigQuery's first-table schema and setup guide are prepared;
cloud execution remains unverified. A [Cloud Shell upload bundle](docs/bigquery_bulk_upload.md)
is available to avoid repeating manual forms for the remaining tables. All company and person records
are fictional. There are no source-system integrations or credentials.

## Proposed architecture

```mermaid
flowchart LR
    A[Mock NetSuite / Salesforce / Workday / Pigment] --> B[Python ingestion and validation]
    B --> C[BigQuery raw datasets]
    C --> D[dbt staging views]
    D --> E[dbt finance reporting models]
    E --> F[Streamlit dashboard]
    G[GitHub Actions: later] -. validate and refresh .-> B
    G -. build and test .-> D
```

Python extracts and loads source data; dbt applies business transformations in
the warehouse. That is **ELT**: extract, load, then transform. Small Python cleanup
steps before loading are still useful. We will learn joins and relational
constraints in SQLite before comparing them with an analytical warehouse.

| Layer | Tool | Why it belongs here | When |
| --- | --- | --- | --- |
| Local code and version history | Python, virtual environment, Git | Reproducible code and a safe place to experiment | Now |
| Source data | Python standard library and CSV | Readable exports with no packages or accounts required | Now |
| Relational SQL practice | SQLite via Python `sqlite3` | Primary/foreign keys, joins, aggregation, constraints | Milestone 2 |
| Warehouse | Google BigQuery Sandbox | Columnar analytical storage, datasets, query costs | Milestone 3 |
| Ingestion | Pandas, Google BigQuery Python client | Explicit schemas, batch loads, logging, retries | Milestone 4 |
| API practice | Local mock HTTP API | Pagination, request errors, extraction without paid vendor access | Milestone 4 |
| Transformation | dbt Core and `dbt-bigquery` | SQL models, dependency graph, tests, documentation | Milestone 5 |
| Automation | GitHub Actions, standard Linux runners | Repeat validated local commands remotely | Milestone 6 |
| Reporting | Streamlit, Pandas, charts | Finance dashboard with drilldowns and reconciled measures | Milestone 7 |

See [architecture and cost safeguards](docs/architecture.md) for dataset design,
metric definitions, refresh design, security, and free-tier limits.

## Milestones and acceptance gates

Finish and understand each gate before starting the next milestone.

| Milestone | What we implement | You practice | Gate |
| --- | --- | --- | --- |
| **1. Synthetic sources — complete** | Shared IDs, customer contracts, workforce, GL, budgets/forecasts; validation | Read a Python function, change a seed, trace a record | Reproducible exports, balanced journals, cross-system reconciliations and fault tests pass |
| **2. Relational SQL — lab ready** | CSVs loaded into local SQLite; eight SQL lessons | `SELECT`, `JOIN`, `GROUP BY`, keys, grain, window functions | Technical checks pass; complete the guided practice before moving on |
| **3. BigQuery Sandbox — setup started** | Unbilled project setup guide and first-table schema ready; cloud steps pending | Datasets, schemas, warehouse vs operational DB, dry runs | Sandbox visible, billing absent, row counts reconcile, query estimate understood |
| 4. Python ingestion and API practice | Explicit schema batch loader, Pandas cleanup, local paginated mock API | Types, API responses, retries, idempotency, logging | Repeat load gives same rows, malformed input and failed API pages stop the job |
| 5. dbt Core | Sources, staging views, finance models and tests | `ref`, `source`, SQL dependencies, tests, documentation | All tests pass; P&L, ARR and payroll reconcile to raw sources |
| 6. GitHub Actions | CI first; manual refresh next; schedule only if useful | YAML, permissions, logs, short-lived authentication | Deliberately bad input fails CI; good manual refresh succeeds within free allowances |
| 7. Streamlit | P&L/BvA, ARR/bookings/customers, workforce, spending, variance drivers | Query caching, filters, chart design, communicating definitions | Dashboard totals tie to tested marts; filters and zero-denominator cases verified |

The current step is [milestone 3 Sandbox setup](docs/milestone_03.md), following
your SQLite filtering and aggregation practice. The other SQL lessons remain
available for learning. Your screenshots show the Google project and `raw_shared`
dataset; this agent has not created cloud resources or verified the completed uploads.

## Folder structure

```text
saas-finance-data-platform/
├── README.md
├── .gitignore
├── config/scenario.json           # Small, editable synthetic scenario
├── src/synthetic/
│   ├── schema.py                  # Tables, columns, keys, accounts, departments
│   ├── generate.py                # Source generation and journal posting
│   └── validate.py                # Read and reconcile saved CSVs
├── src/database/                 # SQLite loader and read-only query runner
├── sql/
│   ├── schema.sql                # CREATE TABLE definitions and constraints
│   └── lessons/                  # Eight commented SQL examples
├── tests/test_synthetic.py        # Reproducibility and deliberate failure tests
├── tests/test_database.py         # Database constraints and finance SQL tests
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── milestone_01.md            # Source data walkthrough
│   └── milestone_02.md            # Guided SQL practice
├── data/local/                    # SQLite database; ignored by Git
├── data/generated/               # Local only; ignored by Git
│   ├── shared/
│   ├── netsuite/
│   ├── salesforce/
│   ├── workday/
│   ├── pigment/
│   ├── manifest.json             # Settings, row counts, SHA-256 file fingerprints
│   └── validation_report.json    # Controls from the saved-file validation
└── .venv/                        # Local Python environment; ignored by Git
```

Add these folders only in their respective milestones:
`src/ingestion/`, `src/mock_api/`, `dbt/` (models/staging,
models/intermediate, models/marts, tests), `.github/workflows/`, and `dashboard/`.
There are intentionally no empty cloud configurations that imply working services.

## Run milestone 1

The environment and initial dataset are already created on this machine. From
the repository folder:

```bash
source .venv/bin/activate
python -m src.synthetic.validate
python -m unittest discover -s tests -v
```

For a fresh clone, first run `python3 -m venv .venv`, activate it, then run:

```bash
python -m src.synthetic.generate
```

Python 3.9+ runs this dependency-free milestone. The installed system Python is
3.9.6; use a maintained Python version in a new environment before installing
cloud/dbt/Streamlit dependencies later. No packages need installing now.

The generator refuses to overwrite a nonempty output directory. For another run:

```bash
python -m src.synthetic.generate --output data/generated/practice_run
python -m src.synthetic.validate --input data/generated/practice_run
```

Choose a new output subdirectory for each experiment. `data/generated/` is
ignored recursively. Default seed 42 reproduces identical source files under
the same Python runtime and code. Hashes help compare runs; validation rechecks
the actual CSV contents rather than trusting an old report.

## Run milestone 2

The local database has already been built and verified. Start with:

```bash
source .venv/bin/activate
python -m src.database.query --file sql/lessons/01_select.sql
```

Follow [the SQL walkthrough](docs/milestone_02.md) one lesson at a time. It
explains the statements, gives expected results and small exercises, and shows
how to load a new database after cloning. No package installation is required.
The complete test suite now includes 30 tests, including eleven offline checks of
the bulk-upload helper. Offline checks do not establish successful cloud uploads.

## GitHub handoff

Local Git tracks the source generator and SQL lab. A remote GitHub repository
is **not created or connected**. The connected GitHub tools do not offer repository
creation, and the GitHub CLI is not installed here.

When ready, create an empty **private** repository named
`saas-finance-data-platform` in GitHub. Do not initialize it with another README
or `.gitignore`. Then use the repository URL GitHub gives you:

```bash
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

Use GitHub's supported browser/credential-manager sign-in flow if prompted; do
not paste a token into chat, a remote URL, or a source file. Public portfolio
sharing is a later choice. No Actions workflow exists yet, so pushing this
milestone does not trigger cloud refreshes or consume Actions minutes.

Continue with [milestone 3 Sandbox setup](docs/milestone_03.md).
