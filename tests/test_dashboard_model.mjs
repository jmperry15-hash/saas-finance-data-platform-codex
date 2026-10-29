import assert from 'node:assert/strict';
import fs from 'node:fs';
import {period,financeModel,saasModel,workforceModel,sum} from '../dashboard-site/src/content/dashboard/finance-model.js';
const q=JSON.parse(fs.readFileSync(process.argv[2] || new URL('../dashboard-site/src/data.json',import.meta.url))).queries;
const months=[...new Set(q.finance.rows.map(r=>r.month))].sort();
const expectations=JSON.parse(fs.readFileSync(process.argv[3] || new URL('../data/local/pnl_expected.json',import.meta.url)));
let checks=0;
const eq=(a,b)=>{assert.ok(Math.abs(a-b)<.00001,`${a} != ${b}`);checks++};
for(const m of months){
 const p=period(m,months),f=financeModel(q.finance.rows,p),s=saasModel(q.saas.rows,q.bookings.rows,p),w=workforceModel(q.workforce.rows,p);
 const ex=expectations.find(r=>r.month===m);
 eq(f.actual.revenue,ex.revenue_cents/100);eq(f.actual.expense,ex.expense_cents/100);eq(f.actual.profit,ex.operating_profit_cents/100);eq(s.actual.revenue,f.actual.revenue);
 eq(w.actual.cost,sum(f.current.filter(r=>['6000','6010','6020'].includes(r.account_id)),'actual_cents')/100);
 eq(sum(s.segments,'ARR'),s.actual.arr);eq(sum(w.departments,'headcount'),w.actual.headcount);
 if(m.startsWith('2025')){assert.ok(f.hasBudget);eq(sum(f.accounts,'favorable'),f.actual.profit-f.budget.profit)}else assert.equal(f.budget,null);
}
const yr=period('2025-10-01..2026-09-30',months);assert.equal(yr.priorComplete,true);
const s=saasModel(q.saas.rows,q.bookings.rows,yr),w=workforceModel(q.workforce.rows,yr);
eq(s.actual.arr,7572453.60);eq(s.actual.customers,100);eq(w.actual.headcount,88);eq(w.actual.fte,87);
assert.equal(period('2024-10-01..2025-09-30',months).priorComplete,false);
assert.equal(financeModel(q.finance.rows,period('2025-12-01..2026-01-31',months)).budget,null);
const all=financeModel(q.finance.rows,yr);
const split=[...new Set(q.finance.rows.map(r=>r.department))].map(d=>financeModel(q.finance.rows.filter(r=>r.department===d),yr));
eq(split.reduce((v,m)=>v+m.actual.expense,0),all.actual.expense);
const empty=workforceModel([],yr);eq(empty.actual.headcount,0);assert.equal(empty.actual.costPerFte,null);
console.log(`PASS: ${checks} independent monthly and boundary reconciliations, plus coverage/plan assertions.`);
