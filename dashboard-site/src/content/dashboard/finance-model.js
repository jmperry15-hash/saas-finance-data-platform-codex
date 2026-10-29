export const sum=(rows,key)=>rows.reduce((s,r)=>s+(r[key]??0),0);
export const monthLabel=m=>new Date(m+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',year:'numeric',timeZone:'UTC'});
export const usd=v=>v==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:2}).format(v);
export const exactUsd=v=>v==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(v);
export const num=v=>v==null?'—':new Intl.NumberFormat('en-US',{maximumFractionDigits:1}).format(v);
export const pct=v=>v==null?'—':(v*100).toFixed(1)+'%';
export function period(value,allMonths){
 const range=value&&value!=='all'?value.split('..'): [allMonths[0],allMonths.at(-1)];
 const start=range[0].slice(0,7)+'-01',end=(range[1]??range[0]).slice(0,7)+'-01';
 const months=allMonths.filter(m=>m>=start&&m<=end);
 const shift=(m,n)=>{const d=new Date(m+'T00:00:00Z'); d.setUTCMonth(d.getUTCMonth()+n);return d.toISOString().slice(0,10)};
 const count=(new Date(end).getUTCFullYear()-new Date(start).getUTCFullYear())*12+new Date(end).getUTCMonth()-new Date(start).getUTCMonth()+1;
 const previous=Array.from({length:count},(_,i)=>shift(start,i-count));
 return {start,end,months,previous,complete:months.length===count,priorComplete:previous.every(m=>allMonths.includes(m)),label:months.length?`${monthLabel(start)} – ${monthLabel(end)}`:'No covered months',priorLabel:`${monthLabel(previous[0])} – ${monthLabel(previous.at(-1))}`};
}
export function group(rows,fields,measures){
 const map=new Map();for(const r of rows){const k=fields.map(f=>r[f]).join('|');if(!map.has(k))map.set(k,Object.fromEntries([...fields.map(f=>[f,r[f]]),...measures.map(f=>[f,0])]));const v=map.get(k);for(const f of measures)v[f]+=r[f]??0;}return [...map.values()];
}
export function financeModel(rows,p){
 const current=rows.filter(r=>p.months.includes(r.month)),previous=rows.filter(r=>p.previous.includes(r.month));
 const hasBudget=p.complete&&current.length>0&&current.every(r=>r.budget_cents!=null);
 const totals=rs=>{const revenue=sum(rs.filter(r=>r.account_type==='Revenue'),'actual_cents')/100,expense=sum(rs.filter(r=>r.account_type==='Expense'),'actual_cents')/100;return {revenue,expense,profit:revenue-expense,margin:revenue?((revenue-expense)/revenue):null}};
 const actual=totals(current),prior=p.priorComplete?totals(previous):null;
 const budget=hasBudget?totals(current.map(r=>({...r,actual_cents:r.budget_cents}))):null;
 const monthly=p.months.map(month=>{const rs=current.filter(r=>r.month===month),t=totals(rs);return {month,Revenue:t.revenue,Expenses:t.expense,'Operating profit':t.profit,'Budget revenue':hasBudget?sum(rs.filter(r=>r.account_type==='Revenue'),'budget_cents')/100:null,'Budget expenses':hasBudget?sum(rs.filter(r=>r.account_type==='Expense'),'budget_cents')/100:null}});
 const accounts=group(current,['account_id','account','account_type'],['actual_cents','budget_cents']).map(r=>({...r,actual:r.actual_cents/100,budget:hasBudget?r.budget_cents/100:null,favorable:hasBudget?(r.account_type==='Revenue'?r.actual_cents-r.budget_cents:r.budget_cents-r.actual_cents)/100:null,varianceRatio:hasBudget&&r.budget_cents?(r.actual_cents-r.budget_cents)/r.budget_cents:null})).sort((a,b)=>a.account_id.localeCompare(b.account_id));
 const departments=group(current.filter(r=>r.account_type==='Expense'),['department'],['actual_cents','budget_cents']).map(r=>({department:r.department,Actual:r.actual_cents/100,Budget:hasBudget?r.budget_cents/100:null}));
 return {current,previous,hasBudget,actual,prior,budget,monthly,accounts,departments};
}
export function saasModel(rows,bookings,p){
 const current=rows.filter(r=>p.months.includes(r.month)),previous=rows.filter(r=>p.previous.includes(r.month));
 const cb=bookings.filter(r=>p.months.includes(r.month)),pb=bookings.filter(r=>p.previous.includes(r.month));
 const totals=(rs,bs,end)=>({arr:sum(rs.filter(r=>r.month===end),'arr_cents')/100,customers:sum(rs.filter(r=>r.month===end),'active_customers'),revenue:sum(rs,'mrr_cents')/100,bookings:sum(bs,'booked_value_cents')/100});
 const actual=totals(current,cb,p.end),prior=p.priorComplete?totals(previous,pb,p.previous.at(-1)):null;
 const monthly=p.months.map(month=>{const r=current.filter(r=>r.month===month),b=cb.filter(r=>r.month===month);return {month,ARR:sum(r,'arr_cents')/100,Customers:sum(r,'active_customers'),Revenue:sum(r,'mrr_cents')/100,'New business':sum(b.filter(r=>r.booking_type==='New business'),'booked_value_cents')/100,Renewal:sum(b.filter(r=>r.booking_type==='Renewal'),'booked_value_cents')/100}});
 const segments=group(current.filter(r=>r.month===p.end),['segment'],['arr_cents','active_customers']).map(r=>({segment:r.segment,ARR:r.arr_cents/100,Customers:r.active_customers}));
 const customers=group(current,['customer_id','customer','segment'],['mrr_cents']).map(r=>({...r,revenue:r.mrr_cents/100,arr:sum(current.filter(v=>v.customer_id===r.customer_id&&v.month===p.end),'arr_cents')/100})).filter(r=>r.revenue||r.arr).sort((a,b)=>b.arr-a.arr);
 return {current,previous,cb,pb,actual,prior,monthly,segments,customers};
}
export function workforceModel(rows,p){
 const current=rows.filter(r=>p.months.includes(r.month)),previous=rows.filter(r=>p.previous.includes(r.month));
 const totals=(rs,end)=>({headcount:sum(rs.filter(r=>r.month===end),'headcount'),fte:sum(rs.filter(r=>r.month===end),'fte_basis_points')/10000,cost:sum(rs,'personnel_cost_cents')/100,costPerFte:sum(rs,'fte_basis_points')?sum(rs,'personnel_cost_cents')/100/(sum(rs,'fte_basis_points')/10000):null});
 const actual=totals(current,p.end),prior=p.priorComplete?totals(previous,p.previous.at(-1)):null;
 const monthly=p.months.map(month=>{const r=current.filter(r=>r.month===month),t=totals(r,month);return {month,Headcount:t.headcount,FTE:t.fte,'Base pay':sum(r,'base_pay_cents')/100,'Variable pay':sum(r,'bonus_cents')/100,Benefits:sum(r,'benefits_cents')/100}});
 const departments=group(current,['department'],['base_pay_cents','bonus_cents','benefits_cents','personnel_cost_cents']).map(r=>({...r,headcount:sum(current.filter(v=>v.department===r.department&&v.month===p.end),'headcount'),fte:sum(current.filter(v=>v.department===r.department&&v.month===p.end),'fte_basis_points')/10000,cost:r.personnel_cost_cents/100,'Base pay':r.base_pay_cents/100,'Variable pay':r.bonus_cents/100,Benefits:r.benefits_cents/100}));
 return {current,previous,actual,prior,monthly,departments};
}
