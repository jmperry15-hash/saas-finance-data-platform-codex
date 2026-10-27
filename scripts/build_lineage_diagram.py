"""Build the educational lineage PDF; requires reportlab (document tooling only).

Run from the project root. Reads SQL/code metadata only; never connects to Google.
The displayed model edges are checked against ref()/source() in the SQL files.
"""
import re
import subprocess
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1600, 1100
C = {'ink':'#172B3A', 'muted':'#516575', 'line':'#8A9BA8',
     'python':'#23706B', 'raw':'#2663A4', 'model':'#7056A5',
     'report':'#187C75', 'query':'#A86A20', 'future':'#78828D',
     'bg':'#F6F8FB', 'panel':'#FFFFFF'}
c = canvas.Canvas(str(OUT / 'saas_finance_lineage.pdf'), pagesize=(W,H))
c.setTitle('SaaS Finance Platform | Python, SQL and Data Lineage')
c.setAuthor('Jack Perry | SaaS Finance Learning Project')
cards, edges, labels = {}, [], []
model_edges, displayed_models = set(), set()

def text(x,y,s,size=15,color='ink',font='Helvetica'):
    c.setFillColor(HexColor(C.get(color,color)))
    c.setFont(font,size)
    c.drawString(x,H-y-size,s)

def card(key,x,y,w,h,title,lines=(),kind='model',future=False):
    cards[key]=(x,y,w,h,title,lines,kind,future)
    if key.startswith('m:'): displayed_models.add(key[2:])

def anchor(key,side='right',offset=0):
    x,y,w,h,*_=cards[key]
    return {'right':(x+w,y+h/2+offset),'left':(x,y+h/2+offset),
            'top':(x+w/2+offset,y),'bottom':(x+w/2+offset,y+h)}[side]

def edge(a,b,via=(),side_a='right',side_b='left',kind='data',offset_a=0,offset_b=0):
    start=anchor(a,side_a,offset_a); end=anchor(b,side_b,offset_b)
    if not via and side_a=='right' and side_b=='left' and start[1]!=end[1]:
        mid=(start[0]+end[0])/2
        via=((mid,start[1]),(mid,end[1]))
    edges.append(([start,*via,end],kind))
    if b.startswith('m:'):
        model_edges.add((a,b))

def label(x,y,s): labels.append((x,y,s))

def header(n,title,sub):
    c.setFillColor(HexColor(C['bg']));c.rect(0,0,W,H,fill=1,stroke=0)
    text(50,32,'SAAS FINANCE / DATA LINEAGE',13,'python','Helvetica-Bold')
    text(50,58,title,32,'ink','Helvetica-Bold')
    text(50,105,sub,16,'muted')
    text(50,146,'SOLID  Data read / transformation     DOTTED  Control / validation     DASHED  Planned connection',13,'muted')
    c.setStrokeColor(HexColor('#DCE3EA'));c.line(50,H-179,1550,H-179)
    text(50,1057,'26 OCT 2026  |  Synthetic data only  |  Code snapshot '+REV+'  |  No live warehouse refresh performed for this diagram',12,'muted')
    text(1455,1057,f'{n} / 3',12,'muted','Helvetica-Bold')

def finish():
    for points,kind in edges:
        color=C['line'] if kind=='data' else C['python'] if kind=='control' else C['future']
        c.setStrokeColor(HexColor(color));c.setFillColor(HexColor(color));c.setLineWidth(2)
        c.setDash([2,4] if kind=='control' else [8,5] if kind=='future' else [])
        p=c.beginPath();p.moveTo(points[0][0],H-points[0][1])
        for x,y in points[1:]:p.lineTo(x,H-y)
        c.drawPath(p)
        x,y=points[-1];px,py=points[-2]
        dx,dy=x-px,y-py; length=(dx*dx+dy*dy)**.5
        if length:
            ux,uy=dx/length,dy/length
            p=c.beginPath();p.moveTo(x,H-y)
            p.lineTo(x-9*ux+4*uy,H-(y-9*uy-4*ux))
            p.lineTo(x-9*ux-4*uy,H-(y-9*uy+4*ux));p.close()
            c.drawPath(p,fill=1,stroke=0)
    c.setDash([])
    for key,(x,y,w,h,title,lines,kind,future) in cards.items():
        col=C[kind]
        c.setFillColor(HexColor('#FFFFFF'));c.setStrokeColor(HexColor(col));c.setLineWidth(1.3)
        c.setDash([6,4] if future else [])
        c.roundRect(x,H-y-h,w,h,8,fill=1,stroke=1);c.setDash([])
        c.setFillColor(HexColor(col));c.rect(x+1,H-y-h+8,4,h-16,fill=1,stroke=0)
        title_size=min(15, 15*(w-31)/max(1,stringWidth(title,'Helvetica-Bold',15)))
        assert title_size>=12,(key,'title too small')
        assert stringWidth(title,'Helvetica-Bold',title_size)<w-30,(key,title)
        text(x+16,y+13,title,title_size,kind,'Helvetica-Bold')
        yy=y+39
        for line in lines:
            assert stringWidth(line,'Helvetica',14)<w-30,(key,line)
            assert yy+14<=y+h-9,(key,'height')
            text(x+16,yy,line,14,'ink');yy+=20
    for x,y,s in labels:
        width=stringWidth(s,'Helvetica',12)
        c.setFillColor(HexColor(C['bg']));c.rect(x-3,H-y-16,width+6,18,fill=1,stroke=0)
        text(x,y,s,12,'muted')
    c.showPage();cards.clear();edges.clear();labels.clear()

REV=subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT,text=True).strip()
header(1,'How the whole platform connects','Python runs locally or in Cloud Shell. BigQuery stores raw tables and executes the SQL behind dbt views.')
card('config',50,215,260,150,'Scenario + shared schema',[
    'config/scenario.json','src/synthetic/schema.py','Seed, dates, IDs, accounts,','departments and column types'],'python')
card('generate',355,215,280,150,'Python source generator',[
    'src/synthetic/generate.py','build_sales -> build_people','-> build_gl -> build_plans','validate.py checks saved CSVs'],'python')
card('csv',680,215,250,150,'14 synthetic CSVs',[
    'data/generated/<system>/','24 months: Oct 2024-Sep 2026','manifest.json: counts + hashes','Money stored as integer cents'],'raw')
card('bulk',975,215,280,150,'Initial bulk upload',[
    'scripts/prepare_bigquery_bundle.py','ZIP: CSVs + explicit schemas','scripts/cloud_shell_upload.py','Cloud Shell runs bq load'],'python')
card('bq',1300,215,250,150,'BigQuery raw tables',[
    'Project: saas-finance-','learning-512616','Region: us-south1','14 tables across 5 datasets'],'raw')
edge('config','generate');edge('generate','csv');edge('csv','bulk');edge('bulk','bq')
card('glcheck',680,435,250,110,'Validate the GL',[
    'src/ingestion/validate_gl.py','Pandas: dates, cents, keys,','journal debit/credit balance'],'python')
card('glload',975,435,280,110,'Repeatable GL refresh',[
    'src/ingestion/load_gl.py','Batch WRITE_TRUNCATE load','Only raw_netsuite.gl_lines'],'python')
edge('csv','glcheck',side_a='bottom',side_b='top');edge('glcheck','glload')
edge('glload','bq',via=((1278,490),(1278,335)),offset_b=45)
card('rawlist',1300,405,250,325,'All uploaded sources',[
    'raw_shared: departments','raw_netsuite: accounts,','vendors, gl_lines','raw_salesforce: customers,','opportunities, contracts,','bookings, customer_monthly','raw_workday: employees,','employee_monthly','raw_pigment: versions,','headcount_plan, financial_plan','Names map 1:1 from CSV files','(system/table.csv).'],'raw')
card('sqlite',50,435,585,110,'Local SQL learning branch',[
    'src/database/load.py + sql/schema.sql -> data/local/saas_finance.sqlite',
    'src/database/query.py + sql/lessons/*.sql (or DB Browser for SQLite)',
    'A separate local learning database; it does not feed BigQuery.'],'python')
edge('csv','sqlite',side_a='bottom',side_b='top',offset_a=-95,via=((710,395),(342.5,395)))
card('api',50,620,370,110,'Mock API server',[
    'src/ingestion/mock_api.py','Reads generated salesforce/customers.csv',
    'Local HTTP /customers endpoint'],'python')
card('extract',480,620,370,110,'Paginated API extraction',[
    'src/ingestion/extract_customers.py','HTTP + JSON -> 6 pages / 130 customers',
    'Schema checks, retries, complete-snapshot write'],'python')
card('apiout',910,620,345,110,'Local API snapshot',[
    'data/local/api/customers.csv','Extraction exercise verified',
    'No API-to-BigQuery connection yet'],'raw')
edge('csv','api',side_a='bottom',side_b='top',offset_a=-115,via=((690,385),(30,385),(30,585),(235,585)))
edge('api','extract');edge('extract','apiout')
card('dbtcode',50,790,800,110,'Local dbt code + Python lesson runner',[
    'scripts/dbt_lesson.py -> dbt build -> dbt/models/staging/*.sql + dbt/models/marts/*.sql',
    'dbt compiles source() and ref() into BigQuery SQL; profiles choose the project/region.',
    'Checks billing, source availability and expiration settings before the selected lesson.'],'python')
card('views',1200,790,350,110,'BigQuery reporting views',[
    'staging: 8 views | finance: 6 views','SQL executes here; code lives locally.',
    'Exact model dependencies: pages 2-3'],'report')
edge('dbtcode','views',kind='control');label(886,823,'compile / build / test')
edge('bq','views',side_a='right',side_b='top',offset_b=150,via=((1578,290),(1578,765),(1525,765)))
card('ci',50,940,800,85,'GitHub Actions: workflow prepared locally; hosted run pending',[
    '.github/workflows/validate.yml -> generate + validate + 60 Python tests; no cloud refresh.',
    'Local Git stores code/history. No remote is configured. Complete refresh orchestration is planned.'],'future',True)
card('streamlit',1200,940,350,85,'Streamlit dashboard - planned',[
    'Will query the finance reporting views.',
    'Filters, charts, spending and variances.'],'future',True)
edge('views','streamlit',side_a='bottom',side_b='top',kind='future')
finish()

header(2,'Accounting and planning: exact SQL lineage','Each staging/reporting box is one .sql file and one BigQuery view. Arrows show direct model dependencies.')
for x,s in [(50,'BIGQUERY RAW'),(330,'STAGING VIEWS'),(670,'FINANCE VIEWS'),(1320,'READ-ONLY SQL')]:text(x,193,s,12,'muted','Helvetica-Bold')
card('s:netsuite.accounts',50,240,230,90,'raw_netsuite.accounts',['Account IDs, names, types'],'raw')
card('m:stg_accounts',330,240,270,90,'stg_accounts',['Account classifications'])
card('s:netsuite.gl_lines',50,425,230,90,'raw_netsuite.gl_lines',['Journal lines; debit / credit'],'raw')
card('m:stg_gl_lines',330,425,270,90,'stg_gl_lines',['GL line detail in cents'])
card('s:pigment.versions',50,655,230,90,'raw_pigment.versions',['Budget / Forecast versions'],'raw')
card('m:stg_plan_versions',330,655,270,90,'stg_plan_versions',['Version IDs + period scope'])
card('s:pigment.financial_plan',50,825,230,90,'raw_pigment.financial_plan',['Version / month / dept / acct'],'raw')
card('m:stg_financial_plan',330,825,270,90,'stg_financial_plan',['Plan amounts in cents'])
card('m:rpt_pnl_monthly',670,240,300,130,'rpt_pnl_monthly',[
    'Grain: one row per month','Revenue, expense, operating profit',
    'Revenue = credits - debits','Expenses = debits - credits'],'report')
card('m:fct_pnl_monthly',670,425,300,130,'fct_pnl_monthly',[
    'Grain: month / department / account','Revenue and expense actuals',
    'Excludes balance sheet accounts','Supports department spend analysis'],'report')
card('m:fct_budget_vs_actual',1020,655,275,170,'fct_budget_vs_actual',[
    'Grain: version / month / dept / acct','Currently selects BUD2025 only',
    'FULL OUTER JOIN actual + budget','Retains missing-side records',
    'Raw and favorable variances','Zero budget -> NULL ratio'],'report')
card('q:05pnl',1320,240,230,110,'05_bookings_revenue_arr.sql',[
    'Reads this P&L view plus','ARR and bookings views.','See page 3 for the other inputs.'],'query')
card('q:03',1320,685,230,110,'03_budget_vs_actual.sql',[
    'Summarizes by month','and account type.','Converts cents to dollars.'],'query')
card('q:02',50,550,230,65,'02_gl_control.sql',['Raw debit / credit totals'],'query')
for source,model in [('netsuite.accounts','stg_accounts'),('netsuite.gl_lines','stg_gl_lines'),('pigment.versions','stg_plan_versions'),('pigment.financial_plan','stg_financial_plan')]:edge('s:'+source,'m:'+model)
edge('m:stg_accounts','m:rpt_pnl_monthly')
edge('m:stg_accounts','m:fct_pnl_monthly',via=((622,285),(622,460)),offset_b=-30)
edge('m:stg_gl_lines','m:fct_pnl_monthly')
edge('m:stg_gl_lines','m:rpt_pnl_monthly',via=((645,470),(645,335)),offset_b=30)
edge('m:stg_accounts','m:fct_budget_vs_actual',side_a='top',via=((465,220),(995,220),(995,700)),offset_b=-40)
label(1030,227,'Account type controls favorable sign')
edge('m:fct_pnl_monthly','m:fct_budget_vs_actual',via=((985,490),(985,720)),offset_b=-20)
edge('m:stg_plan_versions','m:fct_budget_vs_actual',via=((640,700),(640,760)),offset_b=20)
edge('m:stg_financial_plan','m:fct_budget_vs_actual',via=((985,870),(985,790)),offset_b=50)
edge('m:rpt_pnl_monthly','q:05pnl')
edge('m:fct_budget_vs_actual','q:03')
edge('s:netsuite.gl_lines','q:02',side_a='bottom',side_b='top')
card('checks',50,955,920,70,'Validation layer (selected examples; not extra reporting tables)',[
    'dbt/tests/: gl_journals_balance.sql, pnl_reconciles_to_raw.sql, budget_reconciles_to_raw.sql'],'python')
card('unused',1020,865,530,160,'Uploaded, but not used by current dbt models',[
    'raw_netsuite.vendors: source generation / local validation',
    'raw_pigment.headcount_plan: source and plan validation',
    'Neither is currently declared as a dbt source.',
    'Department names come from the shared source (page 3).',
    'Paths: dbt/models/staging/ and dbt/models/marts/'],'raw')
finish()

header(3,'SaaS and workforce: exact SQL lineage','Calendar inputs preserve zero-activity months. Supporting raw records also feed validation, separately from reporting models.')
for x,s in [(50,'BIGQUERY RAW'),(370,'STAGING VIEWS'),(800,'FINANCE VIEWS'),(1250,'READ-ONLY SQL')]:text(x,193,s,12,'muted','Helvetica-Bold')
card('s:salesforce.customer_monthly',50,235,270,90,'raw_salesforce.customer_monthly',['Customer / month MRR and ARR'],'raw')
card('m:stg_customer_monthly',370,235,310,90,'stg_customer_monthly',['One row per customer / month'])
card('m:rpt_arr_monthly',800,235,340,110,'rpt_arr_monthly',[
    'One row per month: MRR, ARR,','active customers, ARR change / growth','Active customer: MRR > 0'],'report')
card('q:04',1250,235,300,90,'04_arr_trend.sql',['Displays dollars and growth %'],'query')
card('s:salesforce.bookings',50,415,270,90,'raw_salesforce.bookings',['One row per signed booking event'],'raw')
card('m:stg_bookings',370,415,310,90,'stg_bookings',['Signed value: new business / renewal'])
card('m:rpt_bookings_monthly',800,415,340,110,'rpt_bookings_monthly',[
    'One row per month: counts + value','New business / renewals separated','Customer snapshots supply the calendar'],'report')
card('q:05',1250,415,300,110,'05_bookings_revenue_arr.sql',[
    'Joins 3 views on month:','rpt_bookings_monthly, rpt_arr_monthly,','rpt_pnl_monthly (from page 2)'],'query')
card('s:workday.employee_monthly',50,605,270,90,'raw_workday.employee_monthly',['Employee / month payroll + FTE'],'raw')
card('m:stg_employee_monthly',370,605,310,90,'stg_employee_monthly',['Base pay + bonus + benefits'])
card('s:shared.departments',50,780,270,90,'raw_shared.departments',['Shared department ID and name'],'raw')
card('m:stg_departments',370,780,310,90,'stg_departments',['Department name + function'])
card('m:rpt_workforce_monthly',800,605,340,130,'rpt_workforce_monthly',[
    'One row per month / department','Headcount, FTE and personnel costs',
    'Months x departments -> retain zeros','Payroll costs already belong in the GL'],'report')
card('s:netsuite.gl_lines',800,795,340,75,'raw_netsuite.gl_lines (page 2)',[
    'DISTINCT month supplies reporting calendar'],'raw')
card('q:06',1250,605,300,100,'06_workforce_summary.sql',[
    'Aggregates departments by month.','Displays FTE and payroll dollars.'],'query')
card('q:01',1250,780,300,90,'01_departments.sql',[
    'Reads raw_shared.departments directly.','Replace YOUR_PROJECT_ID before use.'],'query')
for s,m in [('salesforce.customer_monthly','stg_customer_monthly'),('salesforce.bookings','stg_bookings'),('workday.employee_monthly','stg_employee_monthly'),('shared.departments','stg_departments')]:edge('s:'+s,'m:'+m)
edge('m:stg_customer_monthly','m:rpt_arr_monthly')
edge('m:stg_bookings','m:rpt_bookings_monthly')
edge('m:stg_customer_monthly','m:rpt_bookings_monthly',via=((735,280),(735,445)),offset_b=-25)
label(698,358,'month calendar')
edge('m:stg_employee_monthly','m:rpt_workforce_monthly')
edge('m:stg_departments','m:rpt_workforce_monthly',via=((755,825),(755,705)),offset_b=35)
edge('s:netsuite.gl_lines','m:rpt_workforce_monthly',side_a='top',side_b='bottom')
edge('m:rpt_arr_monthly','q:04')
edge('m:rpt_arr_monthly','q:05',via=((1190,290),(1190,445)),offset_b=-25)
edge('m:rpt_bookings_monthly','q:05')
edge('m:rpt_workforce_monthly','q:06')
edge('s:shared.departments','q:01',side_a='bottom',side_b='bottom',via=((185,895),(1400,895)))
card('support',50,935,680,90,'Supporting raw records: validation inputs',[
    'raw_salesforce.customers / contracts / opportunities; raw_workday.employees',
    'These 4 tables are declared dbt sources but are not direct model inputs.'],'raw')
card('tests',800,935,750,90,'Data quality and reconciliation tests',[
    'Customer coverage; bookings vs signed contracts / won opportunities; roster coverage.',
    'Employee/month/account payroll vs raw GL: personnel_costs_match_gl.sql.'],'python')
edge('support','tests',kind='control')
finish()

# Fail if the diagram omits, invents or misroutes a direct model dependency.
actual_edges=set(); actual_models=set()
for path in (ROOT/'dbt/models').rglob('*.sql'):
    name=path.stem;actual_models.add(name);sql=path.read_text()
    for parent in re.findall(r"ref\(['\"]([^'\"]+)['\"]\)",sql):
        actual_edges.add(('m:'+parent,'m:'+name))
    for system,table in re.findall(r"source\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\)",sql):
        actual_edges.add(('s:'+system+'.'+table,'m:'+name))
assert actual_models==displayed_models,(actual_models-displayed_models,displayed_models-actual_models)
assert actual_edges==model_edges,(actual_edges-model_edges,model_edges-actual_edges)
c.save()
print(f'PASS: {len(actual_models)} models and {len(actual_edges)} direct dependencies match SQL.')
print(OUT/'saas_finance_lineage.pdf')
