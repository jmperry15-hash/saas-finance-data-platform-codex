"""Validate saved CSVs independently; exit nonzero on any failed control."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .schema import KEYS, SCHEMAS

ROOT = Path(__file__).resolve().parents[2]
INTEGER_FIELDS = {"planned_headcount", "fte_basis_points", "bonus_basis_points"}


def read_tables(folder):
    tables = {}
    for name, columns in SCHEMAS.items():
        with (folder / (name + ".csv")).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(columns):
                raise ValueError("Unexpected CSV columns: " + name)
            rows = list(reader)
        for row in rows:
            for field, value in row.items():
                if field is None or value is None:
                    raise ValueError("Malformed CSV row: " + name)
                if field.endswith("_cents") or field in INTEGER_FIELDS:
                    row[field] = int(value)
        tables[name] = rows
    return tables


def grouped(rows, keys, value):
    result = defaultdict(int)
    for row in rows:
        result[tuple(row[k] for k in keys)] += row[value]
    return dict(result)


def validate(t, cfg):
    checks = []

    def check(label, condition):
        if not condition:
            raise ValueError("Validation failed: " + label)
        checks.append(label)

    from .generate import month_add, month_end, scaled
    months = [month_add(cfg["start_month"], i) for i in range(cfg["months"])]
    check("All expected tables present", set(t) == set(SCHEMAS))
    dimensions = {field: {r[field] for r in t[name]} for field, name in [
        ("department_id", "shared/departments"), ("account_id", "netsuite/accounts"),
        ("customer_id", "salesforce/customers"), ("employee_id", "workday/employees"),
        ("vendor_id", "netsuite/vendors"), ("opportunity_id", "salesforce/opportunities"),
        ("contract_id", "salesforce/contracts"), ("version_id", "pigment/versions"),
    ]}
    nullable = {"customer_id", "employee_id", "vendor_id", "contract_id", "acquired_date", "termination_date"}
    for name, rows in t.items():
        keys = [tuple(row[k] for k in KEYS[name]) for row in rows]
        check(name + ": unique nonempty primary key", len(keys) == len(set(keys)) and all(all(k) for k in keys))
        check(name + ": exact schema", all(tuple(row) == SCHEMAS[name] for row in rows))
        for field in SCHEMAS[name]:
            if field in dimensions:
                can_be_blank = (field in nullable and name == "netsuite/gl_lines") or (field == "contract_id" and name == "salesforce/customer_monthly")
                allowed = dimensions[field] | ({""} if can_be_blank else set())
                check(name + ": valid " + field, all(r[field] in allowed for r in rows))
            if field.endswith("_cents") or field in INTEGER_FIELDS:
                check(name + ": integer " + field, all(type(r[field]) is int for r in rows))
                if field != "mrr_change_cents":
                    check(name + ": nonnegative " + field, all(r[field] >= 0 for r in rows))
            if field.endswith("date") or field in ("month", "start_month", "end_month"):
                for row in rows:
                    if row[field]:
                        date.fromisoformat(row[field])
                check(name + ": ISO dates " + field, all(r[field] or field in nullable for r in rows))
            if field == "month":
                check(name + ": periods in range", all(r[field] in months for r in rows))
    contracts = {r["contract_id"]: r for r in t["salesforce/contracts"]}
    opps = {r["opportunity_id"]: r for r in t["salesforce/opportunities"]}
    customers = t["salesforce/customers"]
    check("Customer population", len(customers) == cfg["opening_customers"] + cfg["new_customers"] + cfg["prospects"])
    check("Employee population", len(t["workday/employees"]) == cfg["opening_employees"] + cfg["new_employees"])
    for c in contracts.values():
        check(c["contract_id"] + ": annual term and won opportunity", c["end_date"] == month_add(c["start_date"], 12) and c["contract_value_cents"] == c["mrr_cents"] * 12 and opps[c["opportunity_id"]]["stage"] == "Closed Won" and opps[c["opportunity_id"]]["customer_id"] == c["customer_id"] and opps[c["opportunity_id"]]["annual_value_cents"] == c["contract_value_cents"] and opps[c["opportunity_id"]]["close_date"] == c["start_date"])
    check("Each won opportunity has one contract", Counter(c["opportunity_id"] for c in contracts.values()) == Counter(o["opportunity_id"] for o in opps.values() if o["stage"] == "Closed Won"))
    expected_bookings = {c["contract_id"] for c in contracts.values() if months[0] <= c["start_date"] <= months[-1]}
    bookings = t["salesforce/bookings"]
    check("Exactly one booking per in-window contract", Counter(b["contract_id"] for b in bookings) == Counter(expected_bookings))
    check("Bookings equal signed contract value and period", all(b["booked_value_cents"] == contracts[b["contract_id"]]["contract_value_cents"] and b["month"] == contracts[b["contract_id"]]["start_date"] and b["customer_id"] == contracts[b["contract_id"]]["customer_id"] and b["opportunity_id"] == contracts[b["contract_id"]]["opportunity_id"] and b["booking_type"] == opps[b["opportunity_id"]]["opportunity_type"] for b in bookings))
    snapshots = t["salesforce/customer_monthly"]
    check("Complete customer-month grid including zero balances", {(r["customer_id"], r["month"]) for r in snapshots} == {(c["customer_id"], m) for c in customers for m in months})
    index = {(r["customer_id"], r["month"]): r for r in snapshots}
    for customer in customers:
        cid = customer["customer_id"]
        cs = sorted([c for c in contracts.values() if c["customer_id"] == cid], key=lambda r: r["start_date"])
        check(cid + ": no overlapping contracts", all(a["end_date"] <= b["start_date"] for a, b in zip(cs, cs[1:])))
        check(cid + ": acquisition date", customer["acquired_date"] == (cs[0]["start_date"] if cs else ""))
        previous = sum(c["mrr_cents"] for c in cs if c["start_date"] <= month_add(months[0], -1) < c["end_date"])
        for month in months:
            row = index[cid, month]
            active = [c for c in cs if c["start_date"] <= month < c["end_date"]]
            expected = sum(c["mrr_cents"] for c in active)
            change = expected - previous
            movement = "New" if expected and not previous else "Churn" if previous and not expected else "Expansion" if change > 0 else "Contraction" if change < 0 else "Unchanged"
            if (row["mrr_cents"], row["arr_cents"], row["mrr_change_cents"], row["movement"], row["contract_id"]) != (expected, expected * 12, change, movement, active[0]["contract_id"] if active else ""):
                raise ValueError("Validation failed: customer MRR bridge " + cid + " " + month)
            previous = expected
    checks.append("Every customer MRR/ARR balance and movement matches contracts")
    payroll = t["workday/employee_monthly"]
    expected_payroll = {}
    for emp in t["workday/employees"]:
        check(emp["employee_id"] + ": valid employment dates and FTE", emp["hire_date"].endswith("-01") and (not emp["termination_date"] or emp["hire_date"] <= emp["termination_date"] == month_end(emp["termination_date"])) and 0 < emp["fte_basis_points"] <= 10000)
        for m in months:
            if emp["hire_date"] <= m and (not emp["termination_date"] or m <= emp["termination_date"]):
                salary = emp["annual_base_cents"]
                for _ in range(int(m[:4]) - max(int(emp["hire_date"][:4]), int(months[0][:4]))):
                    salary = scaled(salary, 10400)
                base = scaled(scaled(salary, emp["fte_basis_points"]), 1, 12)
                expected_payroll[emp["employee_id"], m] = (emp["department_id"], emp["fte_basis_points"], base, scaled(base, emp["bonus_basis_points"]), scaled(base, 2500))
    check("Payroll covers exactly the active employee-months", set(expected_payroll) == {(p["employee_id"], p["month"]) for p in payroll})
    check("Payroll compensation and FTE match roster", all(tuple(p[k] for k in ("department_id", "fte_basis_points", "base_pay_cents", "bonus_cents", "benefits_cents")) == expected_payroll[p["employee_id"], p["month"]] and p["personnel_cost_cents"] == p["base_pay_cents"] + p["bonus_cents"] + p["benefits_cents"] for p in payroll))
    gl = t["netsuite/gl_lines"]
    check("Each journal balances", grouped(gl, ["journal_id"], "debit_cents") == grouped(gl, ["journal_id"], "credit_cents"))
    check("Each line has one positive side", all((r["debit_cents"] > 0) != (r["credit_cents"] > 0) for r in gl))
    check("Each month balances", grouped(gl, ["month"], "debit_cents") == grouped(gl, ["month"], "credit_cents"))
    check("Exactly two lines per source journal", all(n == 2 for n in Counter(g["journal_id"] for g in gl).values()))
    source_accounts = {"Funding": {"1000", "3000"}, "Opening deferred": {"1000", "2100"}, "Booking": {"1000", "2100"}, "Revenue": {"2100", "4000"}, "Payroll": {"1000", "6000", "6010", "6020"}, "Vendor": {"1000", "5000", "6100", "6200", "6300", "6400"}}
    check("Known source types and permitted accounts", all(g["source_type"] in source_accounts and g["account_id"] in source_accounts[g["source_type"]] for g in gl))
    revenue = [r for r in gl if r["account_id"] == "4000"]
    check("GL revenue reconciles to each customer-month", grouped(revenue, ["customer_id", "month"], "credit_cents") == grouped([s for s in snapshots if s["mrr_cents"]], ["customer_id", "month"], "mrr_cents"))
    for account, field in [("6000", "base_pay_cents"), ("6010", "bonus_cents"), ("6020", "benefits_cents")]:
        check("Payroll reconciles to GL " + account, grouped([g for g in gl if g["account_id"] == account], ["employee_id", "month", "department_id"], "debit_cents") == grouped(payroll, ["employee_id", "month", "department_id"], field))
    gl_bookings = [g for g in gl if g["source_type"] == "Booking" and g["account_id"] == "2100"]
    check("Every booking posts once to deferred revenue", Counter(g["source_id"] for g in gl_bookings) == Counter(b["booking_id"] for b in bookings))
    booking_index = {b["booking_id"]: b for b in bookings}
    check("Booking posting amount, customer, and month", all((g["credit_cents"], g["customer_id"], g["month"]) == (booking_index[g["source_id"]]["booked_value_cents"], booking_index[g["source_id"]]["customer_id"], booking_index[g["source_id"]]["month"]) for g in gl_bookings))
    deferred = 0
    for month in months:
        deferred += sum(g["credit_cents"] - g["debit_cents"] for g in gl if g["account_id"] == "2100" and g["month"] == month)
        expected = sum(c["mrr_cents"] for c in contracts.values() for n in range(12) if c["start_date"] <= month and month < month_add(c["start_date"], n))
        check(month + ": deferred revenue equals unearned contract service", deferred == expected)
    versions = {r["version_id"]: r for r in t["pigment/versions"]}
    hc = t["pigment/headcount_plan"]
    plans = t["pigment/financial_plan"]
    check("Plan months match version horizon and are after version date", all(versions[r["version_id"]]["start_month"] <= r["month"] <= versions[r["version_id"]]["end_month"] and r["month"] > versions[r["version_id"]]["as_of_date"] for r in hc + plans))
    expected_hc = {(v["version_id"], m, dep) for v in versions.values() for m in months if v["start_month"] <= m <= v["end_month"] for dep in dimensions["department_id"]}
    check("Complete headcount plan grid", {(r["version_id"], r["month"], r["department_id"]) for r in hc} == expected_hc)
    plan_pairs = {(d, a) for d in dimensions["department_id"] for a in ("6000", "6010", "6020")} | {("D03", "4000"), ("D01", "5000"), ("D04", "6100"), ("D02", "6200"), ("D03", "6200"), ("D05", "6300"), ("D05", "6400")}
    check("Complete financial plan grid", {(p["version_id"], p["month"], p["department_id"], p["account_id"]) for p in plans} == {(v["version_id"], m, d, a) for v in versions.values() for m in months if v["start_month"] <= m <= v["end_month"] for d, a in plan_pairs})
    for account, field in [("6000", "planned_base_pay_cents"), ("6010", "planned_bonus_cents"), ("6020", "planned_benefits_cents")]:
        check("Personnel plan reconciles " + account, grouped([p for p in plans if p["account_id"] == account], ["version_id", "month", "department_id"], "amount_cents") == grouped(hc, ["version_id", "month", "department_id"], field))
    accounts = {a["account_id"]: a["account_type"] for a in t["netsuite/accounts"]}
    check("Financial plans contain only P&L accounts", all(accounts[p["account_id"]] in ("Revenue", "Expense") for p in plans))
    ending = [s for s in snapshots if s["month"] == months[-1]]
    return {"status": "PASS", "checks_passed": len(checks), "synthetic_only": True,
            "period": [months[0], months[-1]], "rows": {name: len(rows) for name, rows in t.items()},
            "control_totals": {"gl_debits_cents": sum(g["debit_cents"] for g in gl),
                               "gl_credits_cents": sum(g["credit_cents"] for g in gl),
                               "revenue_cents": sum(g["credit_cents"] for g in revenue),
                               "bookings_cents": sum(b["booked_value_cents"] for b in bookings),
                               "personnel_cost_cents": sum(p["personnel_cost_cents"] for p in payroll),
                               "ending_arr_cents": sum(s["arr_cents"] for s in ending),
                               "ending_paying_customers": sum(s["mrr_cents"] > 0 for s in ending),
                               "ending_headcount": sum(p["month"] == months[-1] for p in payroll),
                               "ending_deferred_revenue_cents": deferred},
            "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/generated")
    args = parser.parse_args()
    try:
        manifest = json.loads((args.input / "manifest.json").read_text())
        report = validate(read_tables(args.input), manifest["config"])
        print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Validation failed: {exc}\n")


if __name__ == "__main__":
    main()
