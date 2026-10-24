# Milestone 3: BigQuery Sandbox, one step at a time

**Faster upload option:** after your first table, use the
[Cloud Shell bulk-upload guide](bigquery_bulk_upload.md) to load the remaining
tables in one batch. The local ZIP and helper are prepared; cloud execution and
financial reconciliation remain pending. The screenshots establish the project
ID `saas-finance-learning-512616` and the attempted departments upload, but do not
verify billing status or the corrected upload's final result.

**Status: local instructions and schemas prepared.** The project and `raw_shared`
dataset are visible in your screenshots. Corrected-table validation, unbilled
status, and full-source loading remain unverified. No credentials are needed in chat.

You practiced filtering and aggregation in SQLite and requested the next
milestone. The remaining SQL lessons are available as references; completing
those exercises has not been assumed.

## What changes from SQLite

SQLite stores your database in a local file. BigQuery stores analytical tables in
Google Cloud and runs queries there. We will reuse the CSV sources and familiar
SQL, then compare the results to our local control totals.

BigQuery names a table as `project_id.dataset.table`. A project is the Google
Cloud container, a dataset groups related tables and sets their location, and a
table holds records. Our first table will be `YOUR_PROJECT_ID.raw_shared.departments`.

## Step 1: create an unbilled Sandbox project

1. Open [BigQuery Studio](https://console.cloud.google.com/bigquery) and sign in
   yourself with your Google account.
2. Follow the welcome prompts if shown. Create a new project named
   **SaaS Finance Learning**. If the project picker is shown instead, use its
   **New project** action. A personal account can use **No organization**.
3. Keep billing unlinked. Do not activate a paid trial, upgrade, or enter a card.
   If account or organization policy forces billing, stop and report the prompt.
4. Select the new project in BigQuery. Confirm the Sandbox notice and check that
   the selected project's Billing page shows no linked billing account.
5. Share the **project ID** and whether the Sandbox/no-billing checks passed.
   Project ID is an identifier, not a secret. Never share a password, token,
   credential JSON file, or private key.

Pause here for our next guided step. The instructions below are ready for after
the project is confirmed. Google documents Sandbox setup without a credit card
or billing account: [official setup guide](https://docs.cloud.google.com/bigquery/docs/sandbox).

## Step 2: create one dataset and upload one small table

After confirming the unbilled project:

1. In BigQuery Explorer, use the project's **Create dataset** action. Name it
   `raw_shared`, choose the **US** multi-region, and retain Sandbox expiration.
   Use this same location for later datasets.
2. Select the dataset and click **Create table**. Choose **Upload**, file format
   **CSV**, and the local file:
   `data/generated/shared/departments.csv`.
3. Set the destination to your project, dataset `raw_shared`, table `departments`.
   Use a native table, with no partitioning or clustering for this tiny first table.
4. Turn off schema auto-detection. Under **Edit as text**, paste the JSON contents
   of [departments.schema.json](../config/bigquery/departments.schema.json).
5. Under Advanced options, set **Header rows to skip = 1** and delimiter to comma.
   Leave allowed bad records at 0. If a write disposition is shown, choose
   **Write if empty** to avoid appending duplicate records on a retry.
6. Create the table, wait for the load job to succeed, and inspect its schema and
   Preview. Expected: three STRING columns and six rows, D01 through D06.

This is a direct local batch upload; no Cloud Storage bucket or API key is needed.
[Google's console loading instructions](https://docs.cloud.google.com/bigquery/docs/batch-loading-data).

## Step 3: run a familiar query

Open [the first BigQuery query](../sql/bigquery/01_departments.sql), replace
`YOUR_PROJECT_ID` with your real project ID, and paste it into BigQuery's SQL
editor. The backticks enclose the complete table name, including any hyphens in
the project ID. Read the estimated bytes processed before clicking Run.

The expected output is the same six departments you queried in SQLite, sorted
alphabetically. Confirm the job succeeded and inspect its processing statistics.
The local query template has not yet been executed or dry-run in BigQuery.

## Remaining work in this milestone

The bulk-upload package contains explicit schemas for the remaining 13 tables
in `raw_netsuite`, `raw_salesforce`, `raw_workday`, and `raw_pigment`, all in US.
After the batch succeeds, we will compare row counts and finance controls
to SQLite, including the September Engineering personnel expense of $252,750.92.
Full-source cloud loading, reconciliation, and query-cost inspection remain to
be completed with your actual project. Full Python/API ingestion is milestone 4.

## Free-only boundaries

Google currently documents a 10 GiB lifetime storage allowance, 1 TiB monthly
query processing, and 60-day expiration for tables, views, and partitions.
Deletion does not restore the lifetime storage allowance. Sandbox excludes DML,
streaming, and Data Transfer Service. Keep the local files so expired tables can
be rebuilt; use small batch uploads and SELECT queries in this milestone.
[Sandbox limits](https://docs.cloud.google.com/bigquery/docs/sandbox).

No cloud connection is configured locally. Browser sign-in stays with you.
Later, Python ingestion will use a local authentication flow whose credentials
remain outside Git and chat. If any next step requires billing, stop there.
