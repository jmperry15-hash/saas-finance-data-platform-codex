"""CSV contracts: ordered column names, grains, and primary keys.

Monetary values are integer USD cents: BigQuery can load them as INT64.
Convert to dollars only when presenting results. Empty strings represent NULL.
"""

SCHEMAS = {
    "shared/departments": ("department_id", "department_name", "function"),
    "netsuite/accounts": ("account_id", "account_name", "account_type"),
    "netsuite/vendors": ("vendor_id", "vendor_name", "account_id", "department_id"),
    "netsuite/gl_lines": ("line_id", "journal_id", "month", "account_id", "department_id", "customer_id", "employee_id", "vendor_id", "source_type", "source_id", "debit_cents", "credit_cents", "memo"),
    "salesforce/customers": ("customer_id", "customer_name", "segment", "region", "acquired_date"),
    "salesforce/opportunities": ("opportunity_id", "customer_id", "close_date", "stage", "opportunity_type", "annual_value_cents"),
    "salesforce/contracts": ("contract_id", "opportunity_id", "customer_id", "start_date", "end_date", "mrr_cents", "contract_value_cents"),
    "salesforce/bookings": ("booking_id", "opportunity_id", "contract_id", "customer_id", "month", "booking_type", "booked_value_cents"),
    "salesforce/customer_monthly": ("customer_id", "month", "contract_id", "mrr_cents", "arr_cents", "movement", "mrr_change_cents"),
    "workday/employees": ("employee_id", "employee_name", "department_id", "hire_date", "termination_date", "fte_basis_points", "annual_base_cents", "bonus_basis_points"),
    "workday/employee_monthly": ("employee_id", "month", "department_id", "fte_basis_points", "base_pay_cents", "bonus_cents", "benefits_cents", "personnel_cost_cents"),
    "pigment/versions": ("version_id", "scenario", "as_of_date", "start_month", "end_month"),
    "pigment/headcount_plan": ("version_id", "month", "department_id", "planned_headcount", "planned_base_pay_cents", "planned_bonus_cents", "planned_benefits_cents"),
    "pigment/financial_plan": ("version_id", "month", "department_id", "account_id", "amount_cents"),
}

KEYS = {name: (cols[0],) for name, cols in SCHEMAS.items()}
KEYS.update({
    "salesforce/customer_monthly": ("customer_id", "month"),
    "workday/employee_monthly": ("employee_id", "month"),
    "pigment/headcount_plan": ("version_id", "month", "department_id"),
    "pigment/financial_plan": ("version_id", "month", "department_id", "account_id"),
})

DEPARTMENTS = [
    ("D01", "Customer Success", "Cost of revenue"),
    ("D02", "Engineering", "Research and development"),
    ("D03", "Sales", "Sales and marketing"),
    ("D04", "Marketing", "Sales and marketing"),
    ("D05", "Finance", "General and administrative"),
    ("D06", "People", "General and administrative"),
]
ACCOUNTS = [
    ("1000", "Cash", "Asset"),
    ("2100", "Deferred revenue", "Liability"),
    ("3000", "Contributed capital", "Equity"),
    ("4000", "Subscription revenue", "Revenue"),
    ("5000", "Cloud hosting", "Expense"),
    ("6000", "Base salaries", "Expense"),
    ("6010", "Variable compensation", "Expense"),
    ("6020", "Employer benefits and payroll taxes", "Expense"),
    ("6100", "Marketing programs", "Expense"),
    ("6200", "Software subscriptions", "Expense"),
    ("6300", "Facilities", "Expense"),
    ("6400", "Professional services", "Expense"),
]


def empty_tables():
    return {name: [] for name in SCHEMAS}


def add(tables, name, *values):
    columns = SCHEMAS[name]
    if len(values) != len(columns):
        raise ValueError("Wrong column count for " + name)
    tables[name].append(dict(zip(columns, values)))
