"""Render the current project data flow as a vector PDF. No cloud access."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/saas_finance_data_flow.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
W,H=1600,1080
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('SaaS Finance Lab | How the data moves')
c.setAuthor('Jack Perry | AI-assisted learning project')
BG='#F5F3ED';INK='#172D34';MUTED='#54676A';GREEN='#236B5B';LINE='#8BADA2';ORANGE='#BB633E'
def txt(x,y,s,size=17,color=INK,bold=False):
 c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold' if bold else 'Helvetica',size);c.drawString(x,H-y-size,s)
def box(x,y,w,h,title,lines,accent=GREEN):
 c.setFillColor(HexColor('#FFFFFF'));c.setStrokeColor(HexColor('#D9DFD8'));c.roundRect(x,H-y-h,w,h,12,fill=1,stroke=1)
 c.setFillColor(HexColor(accent));c.roundRect(x,H-y-5,w,5,2,fill=1,stroke=0)
 txt(x+18,y+18,title,20,INK,True)
 for i,s in enumerate(lines):
  size=min(16,16*(w-36)/stringWidth(s,'Helvetica',16))
  assert size>=13,(title,s)
  txt(x+18,y+55+i*25,s,size,MUTED)
def arrow(points,dashed=False):
 c.setStrokeColor(HexColor(LINE));c.setLineWidth(2.2);c.setDash([5,4] if dashed else [])
 p=c.beginPath();p.moveTo(points[0][0],H-points[0][1])
 for x,y in points[1:]:p.lineTo(x,H-y)
 c.drawPath(p);c.setDash([])
 x,y=points[-1];a,b=points[-2];dx=x-a;dy=y-b;l=(dx*dx+dy*dy)**.5;ux=dx/l;uy=dy/l
 p=c.beginPath();p.moveTo(x,H-y);p.lineTo(x-10*ux+5*uy,H-y+10*uy+5*ux);p.lineTo(x-10*ux-5*uy,H-y+10*uy-5*ux);p.close();c.setFillColor(HexColor(LINE));c.drawPath(p,fill=1,stroke=0)
c.setFillColor(HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
txt(45,28,'SAAS FINANCE LAB  /  PROJECT MAP',14,GREEN,True)
txt(45,56,'How the data moves',42,INK,True)
txt(45,111,'Fictional source systems. Real data engineering concepts. One reconciled finance reporting pipeline.',20,MUTED)
txt(45,158,'01  GENERATE SOURCE EXPORTS LOCALLY WITH PYTHON',14,GREEN,True)
sources=[('NetSuite-like',['accounts / vendors / gl_lines','12 accounts / 16,648 GL lines']),('Salesforce-like',['customers / opportunities','contracts / bookings','customer_monthly']),('Workday-like',['employees / employee_monthly','96 employee records']),('Pigment-like',['versions / financial_plan','headcount_plan']),('Shared master data',['departments','6 consistent department IDs'])]
for i,(t,ls) in enumerate(sources):box(45+i*305,190,290,140,t,ls)
for i in range(5):arrow([(190+i*305,330),(190+i*305,354)])
c.setStrokeColor(HexColor(LINE));c.setLineWidth(2);c.line(190,H-354,1410,H-354);arrow([(190,354),(190,405)])
txt(350,372,'02  RUN THE MANUAL REFRESH',14,GREEN,True)
box(45,405,270,160,'Python ingestion',['Freeze + validate input CSVs','Batch loads: WRITE_TRUNCATE','Verify every uploaded field'])
box(350,405,270,160,'BigQuery raw',['raw_netsuite / raw_salesforce','raw_workday / raw_pigment','raw_shared: 14 tables total'])
box(655,405,270,160,'dbt Core + SQL',['8 staging + 6 finance views','BigQuery executes the SQL','104 data tests + 4 unit tests'])
box(960,405,270,160,'Verified export',['4 reporting SQL queries','4,047 rows checked in Python','Saved warehouse snapshot'])
box(1265,405,290,160,'Data + Sites dashboard',['P&L, budget, ARR, bookings','Workforce + department spend','Local app; separate publication'])
for x in [315,620,925,1230]:arrow([(x,485),(x+35,485)])
# Distinct control and learning paths.
box(45,640,440,165,'Independent reconciliation',['Frozen CSVs -> local SQLite calculations','Python compares every reporting field','Dashed line = validation, not another source'])
arrow([(180,565),(180,640)],True)
arrow([(485,680),(1095,680),(1095,565)],True)
box(525,720,490,160,'GitHub stores code; Actions tests it',['Python, SQL, dbt and dashboard source in Git','Manual CI: fresh synthetic data + offline tests','No Google credentials or warehouse refresh in CI'],ORANGE)
box(1055,720,500,160,'Separate API learning exercise',['Mock HTTP API -> paginated Python extractor','130 customers / 6 pages -> local customers.csv','API-to-BigQuery connection remains deferred'],ORANGE)
box(45,840,440,125,'Metric rules',['Revenue / bookings / costs: sum the period','ARR / customers / headcount / FTE: ending value'])
txt(525,918,'WHAT CHANGES WHEN YOU REFRESH?',14,GREEN,True)
txt(525,947,'Replaces raw data, rebuilds views, checks results, updates the local snapshot.',17,MUTED)
txt(525,975,'Hosted publication is separate. Browsing the dashboard does not query BigQuery.',17,MUTED)
c.setStrokeColor(HexColor('#CBD4CB'));c.line(45,48,1555,48)
txt(45,1037,'Verified implementation: 29 Oct 2026  |  Synthetic data: Oct 2024 - Sep 2026  |  AI-assisted learning project',14,MUTED)
c.save();print(OUT)
