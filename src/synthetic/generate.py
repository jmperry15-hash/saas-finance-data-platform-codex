"""Generate linked fictional operational records, then post their accounting.

Run from the repository root: python -m src.synthetic.generate
Follow build_sales -> build_people -> build_gl -> build_plans to trace lineage.
"""

import argparse
import calendar
import csv
import hashlib
import json
import random
from datetime import date
from pathlib import Path

from .schema import ACCOUNTS, DEPARTMENTS, SCHEMAS, add, empty_tables

ROOT = Path(__file__).resolve().parents[2]


def month_add(value, offset):
    d = date.fromisoformat(value)
    n = d.year * 12 + d.month - 1 + offset
    return date(n // 12, n % 12 + 1, 1).isoformat()


def month_end(value):
    d = date.fromisoformat(value)
    return d.replace(day=calendar.monthrange(d.year, d.month)[1]).isoformat()


def scaled(value, numerator, denominator=10000):
    """Round positive money half up using integer arithmetic, never float."""
    return (value * numerator + denominator // 2) // denominator


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    date.fromisoformat(cfg["start_month"])
    if not cfg["start_month"].endswith("-01") or cfg["currency"] != "USD":
        raise ValueError("Use a first-of-month start date and USD currency")
    for field in ("seed", "months", "opening_customers", "new_customers", "prospects", "opening_employees", "new_employees"):
        if type(cfg[field]) is not int or cfg[field] < 0:
            raise ValueError(field + " must be a nonnegative integer")
    if not 12 <= cfg["months"] <= 36 or cfg["opening_customers"] < 1 or cfg["opening_employees"] < 6:
        raise ValueError("Use 12-36 months, at least one opening customer and six opening employees")
    if month_add(cfg["start_month"], cfg["months"] - 1) > "2026-09-01":
        raise ValueError("Keep synthetic actual periods at or before September 2026")
    return cfg


def build_sales(t, cfg, months, rng):
    opening = cfg["opening_customers"]
    paying = opening + cfg["new_customers"]
    for i in range(paying + cfg["prospects"]):
        cid = f"C{i + 1:04}"
        segment = rng.choice(["SMB", "Mid-market", "Enterprise"])
        acquired = month_add(months[0], -rng.randint(1, 11) if i < opening else rng.randint(0, len(months) - 2)) if i < paying else ""
        add(t, "salesforce/customers", cid, f"Synthetic Customer {i + 1:03}", segment, rng.choice(["North America", "EMEA", "APAC"]), acquired)
        if not acquired:
            stage = "Closed Lost" if i % 2 == 0 else "Proposal"
            add(t, "salesforce/opportunities", f"O{len(t['salesforce/opportunities']) + 1:05}", cid, months[-1], stage, "New business", rng.randint(15000, 90000) * 100)
            continue
        mrr = rng.randint(*{"SMB": (500, 1800), "Mid-market": (2500, 6500), "Enterprise": (8000, 15000)}[segment]) * 100
        start, term = acquired, 0
        while start <= months[-1]:
            if term:
                # Only renewal boundaries change price; churn is a non-renewal.
                if rng.random() < 0.12:
                    break
                mrr = scaled(mrr, rng.choice([8500, 10000, 10000, 11000, 12500]))
            oid = f"O{len(t['salesforce/opportunities']) + 1:05}"
            contract_id = f"K{len(t['salesforce/contracts']) + 1:05}"
            kind = "New business" if term == 0 else "Renewal"
            add(t, "salesforce/opportunities", oid, cid, start, "Closed Won", kind, mrr * 12)
            # End date is exclusive: a contract ending October 1 stops in September.
            add(t, "salesforce/contracts", contract_id, oid, cid, start, month_add(start, 12), mrr, mrr * 12)
            if start >= months[0]:
                add(t, "salesforce/bookings", f"B{len(t['salesforce/bookings']) + 1:05}", oid, contract_id, cid, start, kind, mrr * 12)
            start, term = month_add(start, 12), term + 1
    by_customer = {}
    for c in t["salesforce/contracts"]:
        by_customer.setdefault(c["customer_id"], []).append(c)
    for customer in t["salesforce/customers"]:
        contracts = by_customer.get(customer["customer_id"], [])
        prior_month = month_add(months[0], -1)
        previous = sum(c["mrr_cents"] for c in contracts if c["start_date"] <= prior_month < c["end_date"])
        for month in months:
            active = next((c for c in contracts if c["start_date"] <= month < c["end_date"]), None)
            mrr = active["mrr_cents"] if active else 0
            movement = ("New" if mrr and not previous else "Churn" if previous and not mrr else "Expansion" if mrr > previous else "Contraction" if mrr < previous else "Unchanged")
            add(t, "salesforce/customer_monthly", customer["customer_id"], month, active["contract_id"] if active else "", mrr, mrr * 12, movement, mrr - previous)
            previous = mrr


def build_people(t, cfg, months, rng):
    salary_ranges = [(70000, 110000), (110000, 180000), (80000, 130000), (80000, 140000), (90000, 150000), (75000, 125000)]
    for i in range(cfg["opening_employees"] + cfg["new_employees"]):
        dep = i % len(DEPARTMENTS)
        hire = month_add(months[0], -rng.randint(1, 24) if i < cfg["opening_employees"] else rng.randint(0, len(months) - 1))
        exit_month = rng.randint(4, len(months) - 1)
        termination = month_end(months[exit_month]) if i % 9 == 0 and hire < months[exit_month] else ""
        eid, fte = f"E{i + 1:04}", 8000 if i % 17 == 0 else 10000
        annual = rng.randrange(salary_ranges[dep][0], salary_ranges[dep][1], 1000) * 100
        bonus_rate = 3000 if dep == 2 else 1000
        add(t, "workday/employees", eid, f"Synthetic Employee {i + 1:03}", DEPARTMENTS[dep][0], hire, termination, fte, annual, bonus_rate)
        for month in months:
            if month < hire or (termination and month > termination):
                continue
            # annual_base is full-time reference salary at entry into the modeled window.
            raises = int(month[:4]) - max(int(hire[:4]), int(months[0][:4]))
            salary = annual
            for _ in range(raises):
                salary = scaled(salary, 10400)
            base = scaled(scaled(salary, fte), 1, 12)
            bonus, benefits = scaled(base, bonus_rate), scaled(base, 2500)
            add(t, "workday/employee_monthly", eid, month, DEPARTMENTS[dep][0], fte, base, bonus, benefits, base + bonus + benefits)


def build_gl(t, cfg, months, rng):
    def post(month, debit_account, credit_account, amount, dep, source, source_id, memo, customer="", employee="", vendor=""):
        jid = f"J{len(t['netsuite/gl_lines']) // 2 + 1:06}"
        for account, debit, credit in [(debit_account, amount, 0), (credit_account, 0, amount)]:
            add(t, "netsuite/gl_lines", f"L{len(t['netsuite/gl_lines']) + 1:06}", jid, month, account, dep, customer, employee, vendor, source, source_id, debit, credit, memo)

    post(months[0], "1000", "3000", 2000000000, "D05", "Funding", "INITIAL", "Synthetic opening capital")
    for c in t["salesforce/contracts"]:
        if c["start_date"] < months[0] < c["end_date"]:
            remaining = sum(c["mrr_cents"] for j in range(12) if month_add(c["start_date"], j) >= months[0])
            post(months[0], "1000", "2100", remaining, "D03", "Opening deferred", c["contract_id"], "Remaining prepaid service at opening", customer=c["customer_id"])
    for b in t["salesforce/bookings"]:
        post(b["month"], "1000", "2100", b["booked_value_cents"], "D03", "Booking", b["booking_id"], "Annual subscription paid upfront", customer=b["customer_id"])
    for s in t["salesforce/customer_monthly"]:
        if s["mrr_cents"]:
            post(s["month"], "2100", "4000", s["mrr_cents"], "D03", "Revenue", s["contract_id"], "One month of subscription service", customer=s["customer_id"])
    for p in t["workday/employee_monthly"]:
        for account, field in [("6000", "base_pay_cents"), ("6010", "bonus_cents"), ("6020", "benefits_cents")]:
            post(p["month"], account, "1000", p[field], p["department_id"], "Payroll", p["employee_id"], "Monthly " + field, employee=p["employee_id"])
    for i, (account, dep, name) in enumerate([
        ("5000", "D01", "Nimbus Hosting"), ("6100", "D04", "Signal Campaigns"),
        ("6200", "D02", "Builder Tools"), ("6200", "D03", "Pipeline Tools"),
        ("6300", "D05", "Fictional Workspace"), ("6400", "D05", "Ledger Advisors"),
    ]):
        vid = f"V{i + 1:03}"
        add(t, "netsuite/vendors", vid, "Synthetic " + name, account, dep)
        for idx, month in enumerate(months):
            revenue = sum(s["mrr_cents"] for s in t["salesforce/customer_monthly"] if s["month"] == month)
            base = scaled(revenue, 1200) if account == "5000" else [0, 3000000, 1800000, 1200000, 1500000, 850000][i]
            # Annual marketing events and March audit fees create explainable variances.
            event = 2000000 if account == "6100" and month[5:7] in ("03", "09") else 1000000 if account == "6400" and month[5:7] == "03" else 0
            amount = scaled(base, rng.randint(9300, 10800) + idx * 40) + event
            post(month, account, "1000", amount, dep, "Vendor", f"{vid}-{month}", "Vendor service" + (" plus seasonal event" if event else ""), vendor=vid)


def build_plans(t, cfg, months):
    # Separate driver assumptions: plans never look at realized customer/payroll/GL rows.
    versions = []
    for year in sorted({int(m[:4]) for m in months}):
        versions.append((f"BUD{year}", "Budget", f"{year - 1}-12-01", f"{year}-01-01", f"{year}-12-01"))
        versions.append((f"FC{year}H2", "Forecast", f"{year}-06-30", f"{year}-07-01", f"{year}-12-01"))
    avg_salary = [9000000, 14500000, 10500000, 11000000, 12000000, 10000000]
    for version, scenario, asof, start, end in versions:
        horizon = [m for m in months if start <= m <= end]
        if not horizon:
            continue
        add(t, "pigment/versions", version, scenario, asof, horizon[0], horizon[-1])
        for month in horizon:
            idx = months.index(month)
            # Equal opening allocation plus one planned growth seat/department/6 months.
            for d, (dep, _, _) in enumerate(DEPARTMENTS):
                seats = cfg["opening_employees"] // 6 + int(d < cfg["opening_employees"] % 6) + idx // 6
                if scenario == "Forecast" and dep in ("D02", "D03"):
                    seats += 1
                base = scaled(avg_salary[d] * seats, 1, 12)
                bonus, benefits = scaled(base, 3000 if dep == "D03" else 1000), scaled(base, 2500)
                add(t, "pigment/headcount_plan", version, month, dep, seats, base, bonus, benefits)
                for account, amount in [("6000", base), ("6010", bonus), ("6020", benefits)]:
                    add(t, "pigment/financial_plan", version, month, dep, account, amount)
            revenue = cfg["opening_customers"] * 450000 + idx * 1250000
            if scenario == "Forecast":
                revenue = scaled(revenue, 10500)
            for dep, account, amount in [
                ("D03", "4000", revenue), ("D01", "5000", scaled(revenue, 1200)),
                ("D04", "6100", 3000000), ("D02", "6200", 1800000),
                ("D03", "6200", 1200000), ("D05", "6300", 1500000), ("D05", "6400", 850000),
            ]:
                add(t, "pigment/financial_plan", version, month, dep, account, amount)


def generate(cfg):
    rng = random.Random(cfg["seed"])
    months = [month_add(cfg["start_month"], n) for n in range(cfg["months"])]
    t = empty_tables()
    for row in DEPARTMENTS:
        add(t, "shared/departments", *row)
    for row in ACCOUNTS:
        add(t, "netsuite/accounts", *row)
    build_sales(t, cfg, months, rng)
    build_people(t, cfg, months, rng)
    build_gl(t, cfg, months, rng)
    build_plans(t, cfg, months)
    return t


def write_tables(tables, out, cfg):
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Output directory is not empty: {out}. Choose a new --output directory.")
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in tables.items():
        path = out / (name + ".csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SCHEMAS[name])
            writer.writeheader()
            writer.writerows(rows)
        files[name] = {"rows": len(rows), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps({"schema_version": 1, "synthetic_only": True, "config": cfg, "files": files}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/scenario.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/generated")
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        tables = generate(cfg)
        from .validate import validate, read_tables
        validate(tables, cfg)
        write_tables(tables, args.output, cfg)
        report = validate(read_tables(args.output), cfg)
        (args.output / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=2))
        print(f"Wrote {len(tables)} synthetic CSVs to {args.output.resolve()}")
    except (ValueError, KeyError, OSError, AssertionError) as exc:
        parser.exit(1, f"Generation failed: {exc}\n")


if __name__ == "__main__":
    main()
