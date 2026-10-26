# Milestone 4: extract customers through a local API

An API gives a program a defined way to request data from another program.
Here the server reads our synthetic customer file and responds to HTTP GET
requests with JSON. The extractor requests every page and saves a validated CSV.
It models a common SaaS extraction pattern, not Salesforce's actual API format.

This lesson runs entirely on your Mac at `127.0.0.1` (localhost). No Google Cloud
jobs, vendor accounts, credentials, or paid services are involved. The server
binds only to loopback and exposes one read-only route; it is a learning server,
not a production deployment. See [Python's HTTP server documentation](https://docs.python.org/3/library/http.server.html).

## 1. Start the API in Terminal window A

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-ingestion/bin/python -m src.ingestion.mock_api
```

Leave this window running. It is normal not to get the command prompt back:
the program is waiting for requests. It prints the local address and request logs.
If port 8765 is already in use, stop your earlier copy with Ctrl+C; don't start
several copies. Alternatively use matching `--port 8766` flags on both programs.

Optional: open [the first page](http://127.0.0.1:8765/customers?page=1&page_size=25)
in a browser while the server runs. Look for `data` (25 customer records), `total`
(130), and `next_page` (2). Replace `page=1` with `page=2` to see the next batch.

## 2. Extract in a second Terminal window B

Open a new window with Command+N in Terminal, then run:

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-ingestion/bin/python -m src.ingestion.extract_customers
```

Expected output:

```text
PAGE 1: 25 customers (25/130)
PAGE 2: 25 customers (50/130)
PAGE 3: 25 customers (75/130)
PAGE 4: 25 customers (100/130)
PAGE 5: 25 customers (125/130)
PAGE 6: 5 customers (130/130)
PASS: 130 unique customers across 6 pages; snapshot matches source.
```

The CSV is saved at `data/local/api/customers.csv` and is ignored by Git. It contains
all 130 customer/prospect master records, not 130 paying customers. The extractor
publishes the complete file only after all checks pass; it does not append rows.
Its SHA256 matches the API's original source snapshot. That byte-for-byte control
is possible because this teaching API defines a canonical CSV representation.

## 3. Understand the three moving parts

| Concept | In this exercise |
| --- | --- |
| Endpoint | `/customers`: the address of a collection |
| Pagination | `page=1&page_size=25`: request one batch at a time |
| Response | JSON with records, total count, next page and snapshot ID |

Read `fetch_page()` in `src/ingestion/extract_customers.py`. `session.get()` sends
the request, `raise_for_status()` catches HTTP errors, and `.json()` decodes the
response into Python dictionaries/lists. A response that parses as JSON is not
necessarily a successful request. [Requests documentation](https://requests.readthedocs.io/en/latest/user/quickstart/).

Each read-only request has connection/read timeouts and at most three attempts.
Timeouts, connection failures and selected temporary HTTP errors retry after
0.25 and 0.5 seconds. Invalid inputs (HTTP 400), bad JSON, schema errors, and
pagination errors fail immediately. Snapshot changes, duplicate IDs, missing
records and altered contents prevent a new CSV from being published.

## 4. Failure practice, after the normal extraction works

In window A, press Ctrl+C to stop the API. Restart it with a deliberate failure:

```bash
.venv-ingestion/bin/python -m src.ingestion.mock_api --fail-page 3
```

In window B, run the extractor again. Pages 1 and 2 should succeed, page 3 should
receive HTTP 503 three times, and extraction should stop. The previously saved
130-row CSV remains unchanged; pages 1 and 2 are never published as a partial file.
Stop the failing server with Ctrl+C and restart normally for later exercises.

## Status and boundaries

On October 26, both CLI programs were run together locally: six pages extracted
130 records and the output matched the source byte for byte. The test server was
stopped afterward. Eight new tests cover real loopback HTTP, repeat extraction,
failed-page preservation, invalid parameters, bounded retries, malformed responses,
mixed snapshots, duplicate IDs and invalid records. All 60 project tests pass.

User walkthrough and manual failure exercise are pending. This is an extraction
exercise only: the API extract is not connected to the BigQuery loader yet.
Real vendor authentication, all-source refresh orchestration, dbt, scheduling,
and dashboard work remain later steps.
