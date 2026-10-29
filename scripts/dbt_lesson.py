"""Build a selected dbt lesson after checking the unbilled project."""

import argparse
import os
from pathlib import Path
import subprocess

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "saas-finance-learning-512616"
LOCATION = "us-south1"
EXPIRATION_MS = 59 * 86400000


def unbilled_credentials():
    """Return ADC only after confirming this project's no-billing constraint."""
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    with AuthorizedSession(credentials) as session:
        response = session.get(
            f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT}/billingInfo", timeout=30
        )
        response.raise_for_status()
        billing = response.json()
    if billing.get("billingEnabled") is not False or billing.get("billingAccountName"):
        raise ValueError("Billing must be disabled with no linked account for this lesson.")
    return credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lesson", choices=("departments", "pnl", "budget", "arr", "bookings", "workforce", "all"), default="departments")
    args = parser.parse_args()
    profile_dir = ROOT / "config/dbt"
    profile = profile_dir / "profiles.yml"
    if not profile.exists():
        profile.write_bytes((profile_dir / "profiles.example.yml").read_bytes())
    settings = yaml.safe_load(profile.read_text())["saas_finance_learning"]
    expected = {
        "type": "bigquery", "method": "oauth", "project": PROJECT,
        "dataset": "staging", "location": LOCATION, "threads": 1,
        "maximum_bytes_billed": 52428800, "job_execution_timeout_seconds": 120,
        "job_retries": 0, "priority": "interactive",
    }
    if settings != {"target": "dev", "outputs": {"dev": expected}}:
        raise ValueError("Profile differs from this lesson's fixed destination and query limits.")

    credentials = unbilled_credentials()

    with bigquery.Client(project=PROJECT, credentials=credentials, location=LOCATION) as client:
        source = client.get_table(f"{PROJECT}.raw_shared.departments", timeout=30)
        if source.location != LOCATION or source.num_rows != 6:
            raise ValueError("Expected the six source departments in us-south1.")
        datasets = ["staging"]
        if args.lesson != "departments":
            sources = (["raw_salesforce.customers", "raw_salesforce.customer_monthly"]
                       if args.lesson in ("arr", "bookings") else ["raw_netsuite.accounts", "raw_netsuite.gl_lines"])
            if args.lesson == "budget":
                sources += ["raw_pigment.versions", "raw_pigment.financial_plan"]
            if args.lesson == "bookings":
                sources += ["raw_salesforce.bookings", "raw_salesforce.contracts", "raw_salesforce.opportunities"]
            if args.lesson == "workforce":
                sources = ["raw_workday.employees", "raw_workday.employee_monthly", "raw_netsuite.gl_lines"]
            if args.lesson == "all":
                definitions = yaml.safe_load((ROOT / "dbt/models/staging/sources.yml").read_text())
                sources = [f"{s['schema']}.{t['name']}" for s in definitions["sources"] for t in s["tables"]]
            for table_name in sources:
                table = client.get_table(f"{PROJECT}.{table_name}", timeout=30)
                if table.location != LOCATION or not table.num_rows:
                    raise ValueError(f"Expected nonempty {table_name} in {LOCATION}.")
            datasets.append("finance")
        for name in datasets:
            try:
                dataset = client.get_dataset(f"{PROJECT}.{name}", timeout=30)
            except NotFound:
                dataset = bigquery.Dataset(f"{PROJECT}.{name}")
                dataset.location = LOCATION
                dataset.default_table_expiration_ms = EXPIRATION_MS
                dataset.default_partition_expiration_ms = EXPIRATION_MS
                dataset = client.create_dataset(dataset, timeout=30)
                print(f"Created {name} dataset with 59-day expiration defaults.", flush=True)
            if dataset.location != LOCATION or any(
                value is None or not 0 < value < 60 * 86400000
                for value in (dataset.default_table_expiration_ms, dataset.default_partition_expiration_ms)
            ):
                raise ValueError(f"Review {name} location/expiration before proceeding.")

    selection = {"departments": "+stg_departments", "pnl": "+rpt_pnl_monthly",
                 "budget": "+fct_budget_vs_actual",
                 "arr": "+rpt_arr_monthly source:salesforce.customers",
                 "bookings": "+rpt_bookings_monthly source:salesforce.customers source:salesforce.contracts source:salesforce.opportunities",
                 "workforce": "+rpt_workforce_monthly source:workday.employees",
                 "all": "*"}[args.lesson]
    print(f"Billing disabled; sources and datasets checked. Building {args.lesson} lesson.", flush=True)
    subprocess.run([
        str(ROOT / ".venv-dbt/bin/dbt"), "build",
        "--project-dir", str(ROOT / "dbt"),
        "--profiles-dir", str(profile_dir), "--target", "dev",
        "--select", selection, "--indirect-selection", "cautious",
    ], cwd=ROOT, env={**os.environ, "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
                     "GOOGLE_CLOUD_PROJECT": PROJECT}, check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Stopped: {error}") from error
