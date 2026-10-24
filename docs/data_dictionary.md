# Source data dictionary

All exports live under `data/generated/`. Names below are relative to that
directory and have a `.csv` extension. All records are synthetic. CSV is UTF-8,
comma-delimited, with a header row; blank fields represent NULL, never zero.

## Common types and conventions

| Columns | Type for later BigQuery load | Meaning |
| --- | --- | --- |
| All `*_id` | STRING | Stable join keys within one scenario; keep account IDs as strings too |
| All `*_cents` | INT64 | USD cents; divide by 100 for dollars; no floating-point source money |
| `month`, `start_month`, `end_month` | DATE | First day of calendar reporting month |
| All `*_date` | DATE | ISO date `YYYY-MM-DD`; dates described as exclusive are not service days |
| `fte_basis_points`, `bonus_basis_points` | INT64 | 10000 = 100%; 8000 FTE basis points = 0.8 FTE |
| `planned_headcount` | INT64 | Whole employee seats; not FTE or currency |
| Other fields | STRING | Descriptive attributes and categorical values |

Keys are stable on repeated runs with the same scenario/code. Changing the seed
creates a different fictional world; do not merge different seeds as successive
actual source extracts. These files intentionally share department IDs. Future
ingestion will add batch/time metadata outside this source contract.

## Tables and grains

| File | One row represents | Primary key | Main relationships |
| --- | --- | --- | --- |
| `shared/departments` | Department | department_id | Common to workforce, vendors, plans and GL |
| `netsuite/accounts` | GL account | account_id | Used by GL, vendor categories and financial plan |
| `netsuite/vendors` | Vendor | vendor_id | Default department/account classification |
| `netsuite/gl_lines` | Journal line | line_id | journal_id groups debit/credit pair; optional entity IDs |
| `salesforce/customers` | Customer or prospect | customer_id | Parent of opportunities/contracts/monthly snapshots |
| `salesforce/opportunities` | Sales opportunity | opportunity_id | Customer; won opportunity has one contract |
| `salesforce/contracts` | Annual subscription term | contract_id | Customer and opportunity |
| `salesforce/bookings` | Signed contract in reporting window | booking_id | One per in-window contract |
| `salesforce/customer_monthly` | Customer/prospect per month | customer_id + month | Contract is blank when MRR is zero |
| `workday/employees` | Employee | employee_id | Department; employment dates |
| `workday/employee_monthly` | Active employee per month | employee_id + month | Employee, department, month |
| `pigment/versions` | Historical plan version | version_id | Parent of financial/headcount plans |
| `pigment/headcount_plan` | Department workforce plan per month/version | version_id + month + department_id | Departments and versions |
| `pigment/financial_plan` | Account plan per department/month/version | version_id + month + department_id + account_id | Accounts, departments and versions |

## Field definitions

### Shared departments

`department_id`: D01–D06 common key.
`department_name`: readable business department.
`function`: default P&L expense function; revenue has its own classification.

### NetSuite accounts

`account_id`: four-character account key.
`account_name`: account label.
`account_type`: Asset, Liability, Equity, Revenue or Expense.
Only Revenue and Expense belong in the P&L. Accounts 6000–6020 are classified
as COGS or operating expense according to their department.

### NetSuite vendors

`vendor_id`: V-prefixed key.
`vendor_name`: fictional supplier.
`account_id`: default expense account.
`department_id`: cost owner. Six vendors represent hosting, campaigns,
engineering tools, sales tools, facilities, and professional services.

### NetSuite GL lines

`line_id`: unique journal-line key.
`journal_id`: exactly two lines form one balanced journal.
`month`: posting period.
`account_id`: chart-of-accounts reference.
`department_id`: owning department, present even on balance-sheet offsets.
`customer_id`, `employee_id`, `vendor_id`: optional entity links; only populated
for their relevant activity.
`source_type`: Funding, Opening deferred, Booking, Revenue, Payroll, or Vendor.
`source_id`: INITIAL for funding; contract_id for opening deferred/revenue;
booking_id for booking cash; employee_id for payroll (combine with month/account);
vendor_id plus month for vendor service.
`debit_cents`, `credit_cents`: nonnegative amounts; exactly one side is positive.
`memo`: transaction description, including labeled seasonal vendor costs.

Revenue is credit minus debit. Expenses are debit minus credit. Avoid summing
all GL lines as spending: cash/deferred/equity offsets would double-count activity.

### Salesforce customers

`customer_id`: C-prefixed key, including prospects.
`customer_name`: unmistakably synthetic label.
`segment`: SMB, Mid-market, or Enterprise, influencing initial contract size.
`region`: North America, EMEA, or APAC; all contracts still use USD.
`acquired_date`: first contract start; blank for prospects. Customers that churn
remain in this table and retain their acquisition date.

### Salesforce opportunities

`opportunity_id`: O-prefixed key.
`customer_id`: associated account.
`close_date`: actual date for closed opportunities, expected date for Proposal.
`stage`: Closed Won, Closed Lost, or Proposal.
`opportunity_type`: New business or Renewal.
`annual_value_cents`: proposed or signed full annual amount; not recognized revenue.
Only Closed Won opportunities create contracts. Renewal amounts include the full
renewal value, not just expansion. Existing opening contracts have pre-window deals.

### Salesforce contracts

`contract_id`: K-prefixed key.
`opportunity_id`: originating won deal.
`customer_id`: subscribing account.
`start_date`: inclusive service/booking/payment date.
`end_date`: exclusive, exactly 12 months after start.
`mrr_cents`: monthly subscription service amount for this term.
`contract_value_cents`: 12 × MRR, paid upfront. The last terms can extend beyond
the reporting window; their remaining revenue stays deferred.

### Salesforce bookings

`booking_id`: B-prefixed key.
`opportunity_id`, `contract_id`, `customer_id`: transaction lineage.
`month`: booking date, first of month in this simulation.
`booking_type`: New business or Renewal.
`booked_value_cents`: full annual signed contract value. Pre-window bookings are
excluded, while their contracts remain available for opening balance calculations.

### Salesforce customer monthly

`customer_id`, `month`: compound grain, including pre-acquisition, churned and
prospect zero-MRR rows.
`contract_id`: active contract, blank if none.
`mrr_cents`: active monthly recurring revenue; zero if inactive.
`arr_cents`: 12 × MRR; a point-in-time measure.
`movement`: New, Expansion, Contraction, Churn or Unchanged versus prior month.
`mrr_change_cents`: current minus previous MRR; negative for contraction/churn.
The first month's comparison includes pre-window contracts; opening customers
are not misclassified as new. Renewals with the same MRR are Unchanged, despite
having a new booking. Reactivation is outside this scenario.

### Workday employees

`employee_id`: E-prefixed key.
`employee_name`: synthetic label.
`department_id`: fixed department for the whole scenario.
`hire_date`: first employment day, always first of month.
`termination_date`: inclusive last day, blank for no departure within the window.
`fte_basis_points`: full time = 10000; a small subset is 8000.
`annual_base_cents`: full-time annual reference salary at hire for new hires or
at the beginning of the modeled window for existing employees, before later raises.
`bonus_basis_points`: variable compensation target, 3000 Sales or 1000 otherwise.

### Workday employee monthly

`employee_id`, `month`, `department_id`: employee-period and department linkage.
`fte_basis_points`: active FTE; headcount counts rows while FTE sums this / 10000.
`base_pay_cents`: reference salary with January increases, scaled by FTE / 12.
`bonus_cents`: variable compensation target × monthly base.
`benefits_cents`: 25% of monthly base, including modeled employer payroll taxes.
`personnel_cost_cents`: base + bonus + benefits.
Absent employees have no monthly row; no zero-pay inactive rows are created.

### Pigment versions

`version_id`: BUDyyyy or FCyyyyH2.
`scenario`: Budget or Forecast.
`as_of_date`: when planning assumptions were set (prior December 1 or June 30).
`start_month`, `end_month`: inclusive available plan horizon within the source
window. Different versions may cover the same month; explicitly select one.

### Pigment headcount plan

`version_id`, `month`, `department_id`: planning grain.
`planned_headcount`: opening department allocation plus growth assumptions;
forecast adds a seat to Engineering and Sales. All planned seats assume 1.0 FTE.
`planned_base_pay_cents`: department reference salary × planned seats / 12.
`planned_bonus_cents`: department variable-compensation assumption × base.
`planned_benefits_cents`: 25% of planned base.
These amounts tie to personnel financial-plan rows for the same keys.

### Pigment financial plan

`version_id`, `month`, `department_id`, `account_id`: unique financial plan grain.
`amount_cents`: positive displayed revenue or expense; not debit-signed journal
activity. Budget revenue starts at opening customers × $4,500 monthly plus
$12,500 per elapsed month. H2 forecast revenue assumes 5% more than budget.
Hosting is 12% of planned revenue. Other non-payroll categories use fixed monthly
assumptions, which intentionally miss actual seasonal events and create variances.

## Reconciliation and join guidance

Customer-month revenue equals GL account 4000 by customer and month. Annual
bookings credit deferred revenue and debit cash. Recognized revenue debits
deferred revenue, which rolls forward to the remaining prepaid service obligation.
Payroll ties to GL accounts 6000, 6010 and 6020 by employee, month, and department.

Aggregate monthly GL and plan separately to month/department/account before
joining on all keys; filter one version first. Join headcount plans from the plan
side or use a complete comparison grid so planned-only departments/seats remain.
Do not join department-level planned seats to individual employees and then sum
the repeated plan amount. Distinct employee IDs and plan version IDs serve
different purposes; the plan is not a roster.
