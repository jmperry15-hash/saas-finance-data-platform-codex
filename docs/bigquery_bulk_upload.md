# Upload the source tables in one batch

This is a small manual upload helper for milestone 3, bringing forward the basic
batch-loading part of ingestion. It is not the full milestone 4 API/Pandas pipeline.
Cloud Shell includes Google's CLI tools; no installation is needed on your Mac.
The helper has been tested locally with simulated commands, not against your
Google account. Cloud authentication and successful jobs still need verification.

**Current status (October 24, 2026):** you disabled billing for
`saas-finance-learning-512616`. The latest uploader run passes the billing check
and stops on the original US-only location requirement. The updated helper now
reuses your existing raw dataset's location. Do not use the billing override.

## Continue from the location-check stop

The data ZIP has already been extracted in Cloud Shell. Upload just the revised
`scripts/cloud_shell_upload.py` from your Mac into the Cloud Shell home directory,
using the same Upload menu. Then run:

```bash
python3 cloud_shell_upload.py --bundle saas-finance-upload --project saas-finance-learning-512616 --upload
```

`--bundle` points the updated helper at your already-extracted CSVs and schemas.
There is no need to extract the old ZIP again. Earlier failed runs stopped before
creating datasets or loading tables. Successful cloud loading remains unverified.

## Your steps

1. In Google Cloud Console, click **Activate Cloud Shell** (the `>_` icon near the
   top right). Cloud Shell is Google's browser terminal. If prompted, authorize
   it to use your signed-in account yourself; never paste credentials into chat.
2. In the Cloud Shell terminal menu, choose **Upload file** and upload the local
   `data/local/saas-finance-upload.zip` from this project. Use the home directory
   as the destination. Do not upload your project folder or credential files.
3. In Cloud Shell, run these commands:

```bash
unzip -n saas-finance-upload.zip
python3 saas-finance-upload/cloud_shell_upload.py --project saas-finance-learning-512616 --upload
```

This project's default ZIP expands into `saas-finance-upload/`. If that folder
already exists from an earlier bundle, use a fresh directory for a new bundle;
`unzip -n` intentionally preserves existing files.

To inspect the upload list without Google access, omit `--upload`.
If the script cannot read billing status, report the error. The opt-in permits
the existing link; it does not bypass unknown status or authorize new upgrades.

## What the script does

- Verifies the packaged CSV/schema fingerprints and limits the synthetic batch
  to 14 tables and at most 25 MiB of CSV data (currently about 1.9 MB).
- Reads billing status. The default requires an unlinked project; the explicit
  `--allow-billing-linked` option is available only for a deliberately approved
  linked project; it is not needed now. Unknown status stops.
- Reads existing raw dataset locations and reuses their common location for new
  datasets and loads. If none exist it defaults to US. Missing metadata or
  conflicting existing locations stop the run. New datasets have a 60-day
  default table expiration; no existing dataset is moved or deleted.
- Checks any existing target table's column definitions and row count before
  any cloud writes. A correct departments table is skipped. An incorrect header
  import stops the batch so you can fix it first.
- Uploads missing tables with explicit STRING/DATE/INTEGER types and
  `skip_leading_rows=1`, with zero allowed bad records. It then checks row counts.
- Never deletes tables, upgrades accounts, enables services, or sends streaming
  inserts. Run only one copy at a time and do not edit destination tables during it.

An existing table with the same schema/count is preserved; matching counts alone
do not prove its contents match. SQL financial reconciliation is still required.
The batch is not atomic across tables: earlier successful loads remain if a later
one fails. A retry skips completed matching tables. A mismatch stops for review.
There is no automatic retry, scheduling, dbt build, dashboard, or API extraction.

The helper does not manage/reset quotas or guarantee zero charges for a linked
project. It performs metadata checks and batch loads, not analytical queries.
The size cap is a local input safeguard, not a spending cap. New datasets retain
the helper's 60-day default expiration; existing dataset settings are unchanged.

## Local packaging and validation

From the repository root, regenerate the bundle after source/helper changes:

```bash
.venv/bin/python -m scripts.prepare_bigquery_bundle
```

Only the 14 known source files, their schemas, the manifest, this guide, and the
uploader are included. The ZIP is ignored by Git. Source validation runs before
packaging; local CSVs, SQLite, and credentials are not modified.

## References

- [Cloud Shell](https://docs.cloud.google.com/shell/docs): browser terminal with CLI tools included.
- [Cloud Shell pricing](https://docs.cloud.google.com/shell/pricing): Cloud Shell itself is free; resources used through it have their own rules.
- [Local batch loads](https://docs.cloud.google.com/bigquery/docs/batch-loading-data): CSV uploads and explicit schemas through `bq load`.
- [Sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox): free-only limits and expiration.
