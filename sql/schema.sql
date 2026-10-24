-- Milestone 2 SQLite schema. Source columns and grains follow src/synthetic/schema.py.
-- Dates use ISO TEXT; money uses INTEGER cents; foreign keys require PRAGMA foreign_keys = ON.
-- This is local SQL practice, not BigQuery DDL.

CREATE TABLE shared_departments (
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    department_name TEXT NOT NULL CHECK(department_name <> ''),
    function TEXT NOT NULL CHECK(function <> ''),
    PRIMARY KEY (department_id)
);

CREATE TABLE netsuite_accounts (
    account_id TEXT NOT NULL CHECK(account_id <> ''),
    account_name TEXT NOT NULL CHECK(account_name <> ''),
    account_type TEXT NOT NULL CHECK(account_type <> ''),
    PRIMARY KEY (account_id)
);

CREATE TABLE netsuite_vendors (
    vendor_id TEXT NOT NULL CHECK(vendor_id <> ''),
    vendor_name TEXT NOT NULL CHECK(vendor_name <> ''),
    account_id TEXT NOT NULL CHECK(account_id <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    PRIMARY KEY (vendor_id),
    FOREIGN KEY (account_id) REFERENCES netsuite_accounts(account_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id)
);

CREATE TABLE salesforce_customers (
    customer_id TEXT NOT NULL CHECK(customer_id <> ''),
    customer_name TEXT NOT NULL CHECK(customer_name <> ''),
    segment TEXT NOT NULL CHECK(segment <> ''),
    region TEXT NOT NULL CHECK(region <> ''),
    acquired_date TEXT CHECK(acquired_date <> ''),
    PRIMARY KEY (customer_id)
);

CREATE TABLE salesforce_opportunities (
    opportunity_id TEXT NOT NULL CHECK(opportunity_id <> ''),
    customer_id TEXT NOT NULL CHECK(customer_id <> ''),
    close_date TEXT NOT NULL CHECK(close_date <> ''),
    stage TEXT NOT NULL CHECK(stage <> ''),
    opportunity_type TEXT NOT NULL CHECK(opportunity_type <> ''),
    annual_value_cents INTEGER NOT NULL CHECK(typeof(annual_value_cents) = 'integer' AND annual_value_cents >= 0),
    PRIMARY KEY (opportunity_id),
    FOREIGN KEY (customer_id) REFERENCES salesforce_customers(customer_id)
);

CREATE TABLE salesforce_contracts (
    contract_id TEXT NOT NULL CHECK(contract_id <> ''),
    opportunity_id TEXT NOT NULL CHECK(opportunity_id <> ''),
    customer_id TEXT NOT NULL CHECK(customer_id <> ''),
    start_date TEXT NOT NULL CHECK(start_date <> ''),
    end_date TEXT NOT NULL CHECK(end_date <> ''),
    mrr_cents INTEGER NOT NULL CHECK(typeof(mrr_cents) = 'integer' AND mrr_cents >= 0),
    contract_value_cents INTEGER NOT NULL CHECK(typeof(contract_value_cents) = 'integer' AND contract_value_cents >= 0),
    PRIMARY KEY (contract_id),
    FOREIGN KEY (opportunity_id) REFERENCES salesforce_opportunities(opportunity_id),
    FOREIGN KEY (customer_id) REFERENCES salesforce_customers(customer_id),
    UNIQUE (opportunity_id),
    CHECK(contract_value_cents = mrr_cents * 12),
    CHECK(end_date > start_date)
);

CREATE TABLE salesforce_bookings (
    booking_id TEXT NOT NULL CHECK(booking_id <> ''),
    opportunity_id TEXT NOT NULL CHECK(opportunity_id <> ''),
    contract_id TEXT NOT NULL CHECK(contract_id <> ''),
    customer_id TEXT NOT NULL CHECK(customer_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    booking_type TEXT NOT NULL CHECK(booking_type <> ''),
    booked_value_cents INTEGER NOT NULL CHECK(typeof(booked_value_cents) = 'integer' AND booked_value_cents >= 0),
    PRIMARY KEY (booking_id),
    FOREIGN KEY (opportunity_id) REFERENCES salesforce_opportunities(opportunity_id),
    FOREIGN KEY (contract_id) REFERENCES salesforce_contracts(contract_id),
    FOREIGN KEY (customer_id) REFERENCES salesforce_customers(customer_id),
    UNIQUE (contract_id)
);

CREATE TABLE salesforce_customer_monthly (
    customer_id TEXT NOT NULL CHECK(customer_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    contract_id TEXT CHECK(contract_id <> ''),
    mrr_cents INTEGER NOT NULL CHECK(typeof(mrr_cents) = 'integer' AND mrr_cents >= 0),
    arr_cents INTEGER NOT NULL CHECK(typeof(arr_cents) = 'integer' AND arr_cents >= 0),
    movement TEXT NOT NULL CHECK(movement <> ''),
    mrr_change_cents INTEGER NOT NULL CHECK(typeof(mrr_change_cents) = 'integer'),
    PRIMARY KEY (customer_id, month),
    FOREIGN KEY (customer_id) REFERENCES salesforce_customers(customer_id),
    FOREIGN KEY (contract_id) REFERENCES salesforce_contracts(contract_id),
    CHECK(arr_cents = mrr_cents * 12)
);

CREATE TABLE workday_employees (
    employee_id TEXT NOT NULL CHECK(employee_id <> ''),
    employee_name TEXT NOT NULL CHECK(employee_name <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    hire_date TEXT NOT NULL CHECK(hire_date <> ''),
    termination_date TEXT CHECK(termination_date <> ''),
    fte_basis_points INTEGER NOT NULL CHECK(typeof(fte_basis_points) = 'integer' AND fte_basis_points >= 0 AND fte_basis_points BETWEEN 1 AND 10000),
    annual_base_cents INTEGER NOT NULL CHECK(typeof(annual_base_cents) = 'integer' AND annual_base_cents >= 0),
    bonus_basis_points INTEGER NOT NULL CHECK(typeof(bonus_basis_points) = 'integer' AND bonus_basis_points >= 0),
    PRIMARY KEY (employee_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id)
);

CREATE TABLE workday_employee_monthly (
    employee_id TEXT NOT NULL CHECK(employee_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    fte_basis_points INTEGER NOT NULL CHECK(typeof(fte_basis_points) = 'integer' AND fte_basis_points >= 0 AND fte_basis_points BETWEEN 1 AND 10000),
    base_pay_cents INTEGER NOT NULL CHECK(typeof(base_pay_cents) = 'integer' AND base_pay_cents >= 0),
    bonus_cents INTEGER NOT NULL CHECK(typeof(bonus_cents) = 'integer' AND bonus_cents >= 0),
    benefits_cents INTEGER NOT NULL CHECK(typeof(benefits_cents) = 'integer' AND benefits_cents >= 0),
    personnel_cost_cents INTEGER NOT NULL CHECK(typeof(personnel_cost_cents) = 'integer' AND personnel_cost_cents >= 0),
    PRIMARY KEY (employee_id, month),
    FOREIGN KEY (employee_id) REFERENCES workday_employees(employee_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id),
    CHECK(personnel_cost_cents = base_pay_cents + bonus_cents + benefits_cents)
);

CREATE TABLE pigment_versions (
    version_id TEXT NOT NULL CHECK(version_id <> ''),
    scenario TEXT NOT NULL CHECK(scenario <> ''),
    as_of_date TEXT NOT NULL CHECK(as_of_date <> ''),
    start_month TEXT NOT NULL CHECK(start_month <> ''),
    end_month TEXT NOT NULL CHECK(end_month <> ''),
    PRIMARY KEY (version_id)
);

CREATE TABLE pigment_headcount_plan (
    version_id TEXT NOT NULL CHECK(version_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    planned_headcount INTEGER NOT NULL CHECK(typeof(planned_headcount) = 'integer' AND planned_headcount >= 0),
    planned_base_pay_cents INTEGER NOT NULL CHECK(typeof(planned_base_pay_cents) = 'integer' AND planned_base_pay_cents >= 0),
    planned_bonus_cents INTEGER NOT NULL CHECK(typeof(planned_bonus_cents) = 'integer' AND planned_bonus_cents >= 0),
    planned_benefits_cents INTEGER NOT NULL CHECK(typeof(planned_benefits_cents) = 'integer' AND planned_benefits_cents >= 0),
    PRIMARY KEY (version_id, month, department_id),
    FOREIGN KEY (version_id) REFERENCES pigment_versions(version_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id)
);

CREATE TABLE pigment_financial_plan (
    version_id TEXT NOT NULL CHECK(version_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    account_id TEXT NOT NULL CHECK(account_id <> ''),
    amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer' AND amount_cents >= 0),
    PRIMARY KEY (version_id, month, department_id, account_id),
    FOREIGN KEY (version_id) REFERENCES pigment_versions(version_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id),
    FOREIGN KEY (account_id) REFERENCES netsuite_accounts(account_id)
);

CREATE TABLE netsuite_gl_lines (
    line_id TEXT NOT NULL CHECK(line_id <> ''),
    journal_id TEXT NOT NULL CHECK(journal_id <> ''),
    month TEXT NOT NULL CHECK(month <> ''),
    account_id TEXT NOT NULL CHECK(account_id <> ''),
    department_id TEXT NOT NULL CHECK(department_id <> ''),
    customer_id TEXT CHECK(customer_id <> ''),
    employee_id TEXT CHECK(employee_id <> ''),
    vendor_id TEXT CHECK(vendor_id <> ''),
    source_type TEXT NOT NULL CHECK(source_type <> ''),
    source_id TEXT NOT NULL CHECK(source_id <> ''),
    debit_cents INTEGER NOT NULL CHECK(typeof(debit_cents) = 'integer' AND debit_cents >= 0),
    credit_cents INTEGER NOT NULL CHECK(typeof(credit_cents) = 'integer' AND credit_cents >= 0),
    memo TEXT NOT NULL CHECK(memo <> ''),
    PRIMARY KEY (line_id),
    FOREIGN KEY (account_id) REFERENCES netsuite_accounts(account_id),
    FOREIGN KEY (department_id) REFERENCES shared_departments(department_id),
    FOREIGN KEY (customer_id) REFERENCES salesforce_customers(customer_id),
    FOREIGN KEY (employee_id) REFERENCES workday_employees(employee_id),
    FOREIGN KEY (vendor_id) REFERENCES netsuite_vendors(vendor_id),
    CHECK((debit_cents > 0 AND credit_cents = 0) OR (credit_cents > 0 AND debit_cents = 0))
);
