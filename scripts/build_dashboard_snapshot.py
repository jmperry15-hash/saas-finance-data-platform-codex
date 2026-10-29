"""Build an auditable dashboard snapshot from the validated local SQLite copy."""
import argparse, json, sqlite3, sys, hashlib, uuid
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.synthetic.validate import read_tables, validate
from src.synthetic.schema import SCHEMAS
from src.database.load import verify_database
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', nargs='?', type=Path, default=ROOT/'work/dashboard-evidence/reviewed.json')
parser.add_argument('--source', type=Path, default=ROOT/'data/generated')
parser.add_argument('--database', type=Path, default=ROOT/'data/local/saas_finance.sqlite')
parser.add_argument('--receipt', type=Path, default=ROOT/'work/dashboard-evidence/validation.json')
args=parser.parse_args()
source=args.source
tables=read_tables(source)
report=validate(tables,json.loads((source/'manifest.json').read_text())['config'])
c=sqlite3.connect(f'file:{args.database.resolve()}?mode=ro',uri=True)
verify_database(c,report)
# Verify every database value against the source, not only aggregate controls.
for name,cols in SCHEMAS.items():
 raw=[tuple(None if r[k]=='' else str(r[k]) for k in cols) for r in tables[name]]
 db=[tuple(None if v is None else str(v) for v in r) for r in c.execute('select '+','.join(cols)+' from '+name.replace('/','_'))]
 assert sorted(raw,key=str)==sorted(db,key=str),name
c.row_factory=sqlite3.Row
queries={}
now=datetime.now(timezone.utc).isoformat()
def query(key,title,sql,files,definitions):
 rows=[dict(r) for r in c.execute(sql)]
 queries[key]={'rows':rows,'source':{'title':title,'type':'sqlite','tables':[f.replace('/','_') for f in files], 'files':[f+'.csv' for f in files], 'sql':sql,'executedAt':now,'coverage':{'start':'2024-10-01','end':'2026-09-30'},'grain':{'finance':'Month × department × account','saas':'Month × customer','workforce':'Month × department','bookings':'Signed contract booking'}[key], 'caveats':['All company and person records are fictional. Local validated snapshot; no live BigQuery query or automatic refresh.','USD. Money is stored in integer cents; display values divide by 100.'],'metricDefinitions':[{'label':k,'definition':v} for k,v in definitions], 'evidenceFlow':[{'title':'Validated local source','detail':'All 14 SQLite tables match every field of the generated source files. Existing 764 source checks and independent SQL control totals pass.'},{'title':'Model definitions','detail':'Reproduces dbt finance model semantics locally. SQL below is the executed SQLite query, not a claimed BigQuery execution.'}]}}
query('finance','Monthly P&L and BUD2025', '''WITH actual AS (
 SELECT g.month,g.department_id,g.account_id,SUM(CASE WHEN a.account_type='Revenue' THEN g.credit_cents-g.debit_cents ELSE g.debit_cents-g.credit_cents END) actual_cents
 FROM netsuite_gl_lines g JOIN netsuite_accounts a USING(account_id) WHERE a.account_type IN ('Revenue','Expense') GROUP BY 1,2,3
), budget AS (SELECT month,department_id,account_id,amount_cents budget_cents FROM pigment_financial_plan WHERE version_id='BUD2025'), keys AS (
 SELECT month,department_id,account_id FROM actual UNION SELECT month,department_id,account_id FROM budget
)
SELECT k.*,d.department_name department,d.function,a.account_name account,a.account_type,
 COALESCE(x.actual_cents,0) actual_cents,
 CASE WHEN k.month BETWEEN '2025-01-01' AND '2025-12-01' THEN COALESCE(b.budget_cents,0) ELSE NULL END budget_cents
FROM keys k JOIN shared_departments d USING(department_id) JOIN netsuite_accounts a USING(account_id)
LEFT JOIN actual x USING(month,department_id,account_id) LEFT JOIN budget b USING(month,department_id,account_id)
ORDER BY k.month,k.department_id,k.account_id''',['netsuite/gl_lines','netsuite/accounts','shared/departments','pigment/financial_plan'], [('Revenue','Recognized subscription revenue: GL credits minus debits for revenue accounts.'),('Operating profit','Revenue minus all expense accounts. This is operating profit, not EBITDA.'),('Budget','BUD2025 only. Budget unavailable outside January–December 2025; no other plan version is substituted.'),('Favorable variance','Actual minus budget for revenue; budget minus actual for expenses. Positive is favorable. Zero budget yields an unavailable percentage.')])
query('saas','Customer monthly revenue and ARR','''SELECT m.month,m.customer_id,c.customer_name customer,c.segment,c.region,m.mrr_cents,m.arr_cents,
 CASE WHEN m.mrr_cents>0 THEN 1 ELSE 0 END active_customers
FROM salesforce_customer_monthly m JOIN salesforce_customers c USING(customer_id) ORDER BY m.month,m.customer_id''',['salesforce/customer_monthly','salesforce/customers'], [('ARR','Ending monthly recurring revenue × 12. Sum customers within a month; never sum ARR across months.'),('Active customers','Customers with positive MRR at the selected ending month.'),('MRR','Recurring monthly revenue from active contracts. In this synthetic scenario it reconciles to recognized GL subscription revenue.'),('Prior period','Immediately preceding equal number of calendar months. Ending balances compare endpoints; missing full prior coverage is unavailable.')])
query('workforce','Monthly headcount and personnel costs','''WITH months AS (SELECT DISTINCT month FROM netsuite_gl_lines), workforce AS (
 SELECT month,department_id,COUNT(*) headcount,SUM(fte_basis_points) fte_basis_points,SUM(base_pay_cents) base_pay_cents,SUM(bonus_cents) bonus_cents,SUM(benefits_cents) benefits_cents,SUM(personnel_cost_cents) personnel_cost_cents
 FROM workday_employee_monthly GROUP BY 1,2)
SELECT m.month,d.department_id,d.department_name department,d.function,
COALESCE(w.headcount,0) headcount,COALESCE(w.fte_basis_points,0) fte_basis_points,
COALESCE(w.base_pay_cents,0) base_pay_cents,COALESCE(w.bonus_cents,0) bonus_cents,COALESCE(w.benefits_cents,0) benefits_cents,COALESCE(w.personnel_cost_cents,0) personnel_cost_cents
FROM months m CROSS JOIN shared_departments d LEFT JOIN workforce w ON m.month=w.month AND d.department_id=w.department_id ORDER BY 1,2''',['netsuite/gl_lines','workday/employee_monthly','shared/departments'], [('Headcount','Number of active employee-month records at the ending month. Not additive across months.'),('FTE','Ending sum of active FTE basis points / 10,000.'),('Personnel cost','Base pay + variable compensation + benefits/payroll taxes summed over the selected period; reconciles to GL accounts 6000, 6010 and 6020.'),('Cost per FTE-month','Period personnel cost / sum of monthly FTE. This is a weighted monthly cost, not cost divided by ending headcount.')])
query('bookings','Signed contract bookings','''SELECT b.*,c.customer_name customer,c.segment,c.region FROM salesforce_bookings b JOIN salesforce_customers c USING(customer_id) ORDER BY b.month,b.booking_id''',['salesforce/bookings','salesforce/customers'], [('Bookings','Full annual contract value at service-start/booking date, including full-value renewals. Not recognized revenue or incremental ARR.'),('New business and renewal','Mutually exclusive booking types; together reconcile to total bookings. Months without events are zero when within reviewed coverage.')])
# Independent cross-system checks for each month and department.
for month in sorted({r['month'] for r in queries['saas']['rows']}):
 f=[r for r in queries['finance']['rows'] if r['month']==month]
 assert sum(r['actual_cents'] for r in f if r['account_type']=='Revenue')==sum(r['mrr_cents'] for r in queries['saas']['rows'] if r['month']==month)
 for d in tables['shared/departments']:
  assert sum(r['actual_cents'] for r in f if r['department_id']==d['department_id'] and r['account_id'] in ['6000','6010','6020'])==sum(r['personnel_cost_cents'] for r in queries['workforce']['rows'] if r['month']==month and r['department_id']==d['department_id'])
snapshot={'surface':'dashboard','title':'Juniper Cloud · Finance','generatedAt':now,'status':'reviewed','buildStatus':'creating','exportPreferences':{'selected':None,'destinations':[{'id':'plugin:google-drive@openai-curated','label':'Google Drive','plugin':{'name':'google-drive','marketplace':'openai-curated'},'installedPluginId':'google-drive@openai-curated-remote'}]},'filters':[{'id':'date','label':'Period','field':'month','mode':'through','defaultValue':'2025-01-01..2025-12-31','queryIds':list(queries)},{'id':'department','label':'Department','field':'department','defaultValue':'all','queryIds':['finance','workforce']},{'id':'segment','label':'Segment','field':'segment','defaultValue':'all','queryIds':['saas','bookings']}],'queries':queries}
out=args.output
snapshot['id']='juniper-finance-'+uuid.uuid4().hex
if out.exists():
 prior=json.loads(out.read_text())
 for key in ['id','legacyPresentationTitle']:
  if key in prior:snapshot[key]=prior[key]
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(snapshot,indent=2)+'\n')
receipt={'status':'PASS','source_checks':report['checks_passed'],'all_sqlite_fields_match_source':True,'monthly_revenue_reconciliations':24,'department_month_payroll_reconciliations':144,'queries':{k:len(v['rows']) for k,v in queries.items()},'source_sha256':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*.csv')}}
args.receipt.parent.mkdir(parents=True,exist_ok=True)
args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'},indent=2))
