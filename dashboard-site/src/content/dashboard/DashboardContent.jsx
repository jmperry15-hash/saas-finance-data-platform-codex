import React, {useState} from 'react';
import {DataComponent, DataTable, Dropdown, EvidenceChart, Filters, MetricCard, SectionHeader, SortableItem, SortableRegion, useDataApp, useDashboardTabs} from '../../data-app-public.jsx';
import {sum,period,financeModel,saasModel,workforceModel,usd,exactUsd,num,pct,monthLabel} from './finance-model.js';
import './dashboard.css';
const tabs=[{id:'dashboard',label:'Financial performance',filterIds:['date','department']},{id:'saas',label:'ARR & bookings',filterIds:['date','segment'],defaultFilters:{date:'2025-10-01..2026-09-30'}},{id:'workforce',label:'Workforce',filterIds:['date','department'],defaultFilters:{date:'2025-10-01..2026-09-30'}}];
const tone=v=>v==null||v===0?'neutral':v>0?'positive':'negative';
const delta=(v,b)=>v==null||b==null?'Unavailable':b===0?(v===0?'0%':'—'):`${v-b>0?'+':''}${pct((v-b)/Math.abs(b))}`;
const col=(field,label,renderCell,deltaTone)=>({field,label:label??field,renderCell,deltaTone});
const line=(fields,currency='USD')=>({type:'line',x:'month',y:fields[0],fields,currency,stackable:false,showXAxisLabel:false,showYAxisLabel:false,valueDecimals:0});
export function DashboardContent(){
 const {snapshot,queries,filters,setFilter}=useDataApp();
 const {activeTabId}=useDashboardTabs(tabs); const tab=tabs.some(t=>t.id===activeTabId)?activeTabId:'dashboard';
 const [detail,setDetail]=useState(null);
 const months=[...new Set(queries.finance.rows.map(r=>r.month))].sort();
 const p=period(filters.date??'2025-01-01..2025-12-31',months);
 const department=filters.department??'all',segment=filters.segment??'all';
 const fr=queries.finance.rows.filter(r=>department==='all'||r.department===department);
 const wr=queries.workforce.rows.filter(r=>department==='all'||r.department===department);
 const sr=queries.saas.rows.filter(r=>segment==='all'||r.segment===segment),br=queries.bookings.rows.filter(r=>segment==='all'||r.segment===segment);
 const f=financeModel(fr,p),s=saasModel(sr,br,p),w=workforceModel(wr,p);
 const blocks={},layout=[];
 function metric(id,title,value,format,queryId,sourceRows,previous,objective=0,description=''){
  blocks[id]={kind:'metric',title,span:3,node:<MetricCard id={id} title={title} queryId={queryId} value={format(value)} comparison={id==='finance-margin'?(previous==null||value==null?'Unavailable':`${value-previous>0?'+':''}${((value-previous)*100).toFixed(1)} pp`):delta(value,previous)} deltaTone={objective?tone((value-previous)*objective):'neutral'} description={description} sourceRows={sourceRows} displayRows={[{period:p.label,value,comparison:previous??null}]} />};return id;
 }
 function chart(id,title,queryId,rows,sourceRows,spec,description='',options={}){blocks[id]={kind:'chart',title,span:6,node:<EvidenceChart id={id} title={title} queryId={queryId} variant="card" rows={rows.map(r=>Object.fromEntries([spec.x,spec.y,...(spec.fields??[]),spec.series].filter(Boolean).map(k=>[k,r[k]])))} sourceRows={sourceRows} spec={{...spec,colors:spec.colorBySign?undefined:Object.fromEntries((spec.fields??[spec.y]).map((field,index)=>[field,`var(--chart-${index+1})`]))}} height={260} description={description} {...options}/>};return id;}
 function table(id,title,queryId,rows,sourceRows,columns,options={}){blocks[id]={kind:'table',title,span:12,node:<DataComponent id={id} title={title} queryId={queryId} variant="card" kind="table" displayRows={rows} sourceRows={sourceRows}><DataTable rows={rows} columns={columns} label={title} searchable={false} {...options}/></DataComponent>};return id;}
 const row=(id,items,title,kind)=>layout.push({id:`${tab}:${id}`,items,kind,...(title?{header:<SectionHeader id={`${tab}:${id}:heading`} title={title}/>}:{})});
 const sourceF=f.hasBudget||!p.priorComplete?f.current:[...f.current,...f.previous],sourceS=p.priorComplete?[...s.current,...s.previous]:s.current,sourceW=p.priorComplete?[...w.current,...w.previous]:w.current;
 if(tab==='dashboard'){
  const base=f.budget??f.prior;
  row('metrics',[
   metric('finance-revenue','Revenue',f.actual.revenue,usd,'finance',sourceF,base?.revenue,1),
   metric('finance-expenses','Total expenses',f.actual.expense,usd,'finance',sourceF,base?.expense,-1),
   metric('finance-profit','Operating profit',f.actual.profit,usd,'finance',sourceF,base?.profit,1),
   metric('finance-margin','Operating margin',f.actual.margin,pct,'finance',sourceF,base?.margin,1,'Operating profit divided by revenue. Unavailable when revenue is zero.')
  ],null,'metrics');
  row('trends',[
   chart('finance-revenue-trend',f.hasBudget?'Revenue versus budget':'Monthly revenue','finance',f.monthly,f.current,line(f.hasBudget?['Revenue','Budget revenue']:['Revenue'])),
   chart('finance-spend-trend',f.hasBudget?'Expenses versus budget':'Monthly expenses','finance',f.monthly,f.current,line(f.hasBudget?['Expenses','Budget expenses']:['Expenses']))
  ],'Monthly performance');
  row('drivers',[
   chart('finance-departments','Department expenses','finance',f.departments,f.current.filter(r=>r.account_type==='Expense'),{type:'horizontalBar',x:'department',y:'Actual',fields:f.hasBudget?['Actual','Budget']:['Actual'],currency:'USD',stackable:false,valueDecimals:0}),
   chart('finance-variance','Account variance contribution','finance',f.accounts.map(r=>({account:r.account,'Favorable variance':r.favorable})),f.current,{type:'horizontalBar',x:'account',y:'Favorable variance',currency:'USD',colorBySign:true,stackable:false,valueDecimals:0},'Positive is favorable. These account contributions reconcile to operating-profit variance. Budget comparison is unavailable outside 2025.')
  ],'Spending and variance drivers');
  const detailRows=detail?.type==='account'?f.current.filter(r=>r.account_id===detail.key):null;
  row('pnl',[table('finance-pnl','P&L account detail','finance',f.accounts, f.current,[col('account','Account'),col('actual','Actual',exactUsd),col('budget','BUD2025',exactUsd),col('favorable','Favorable variance',exactUsd,tone),col('varianceRatio','Actual − budget %',pct)],{rowKey:'account_id',onRowSelect:r=>setDetail({type:'account',key:r.account_id,name:r.account}),rowActionLabel:r=>`Inspect ${r.account}`,searchable:true})],'P&L detail');
  if(detailRows){row('detail',[table('finance-account-records',`${detail.name} · month and department`,'finance',detailRows.map(r=>({...r,period:monthLabel(r.month),actual:r.actual_cents/100,budget:r.budget_cents==null?null:r.budget_cents/100})),detailRows,[col('period','Month'),col('department','Department'),col('actual','Actual',exactUsd),col('budget','BUD2025',exactUsd)],{searchable:true})]);}
 }else if(tab==='saas'){
  row('metrics',[
   metric('saas-arr','Ending ARR',s.actual.arr,usd,'saas',sourceS,s.prior?.arr,1,'Ending monthly recurring revenue × 12; not summed across the selected period.'),
   metric('saas-customers','Ending active customers',s.actual.customers,num,'saas',sourceS,s.prior?.customers,1),
   metric('saas-revenue','Recognized revenue',s.actual.revenue,usd,'saas',sourceS,s.prior?.revenue,1,'Sum of monthly recurring revenue; reconciles to the GL in this fictional scenario.'),
   metric('saas-bookings','Signed bookings',s.actual.bookings,usd,'bookings',p.priorComplete?[...s.cb,...s.pb]:s.cb,s.prior?.bookings,1,'Full annual value of new contracts and renewals booked during the selected period.')
  ],null,'metrics');
  row('trends',[
   chart('saas-arr-trend','Ending ARR by month','saas',s.monthly,s.current,line(['ARR'])),
   chart('saas-booking-trend','New business and renewal bookings','bookings',s.monthly,s.cb,{type:'bar',x:'month',y:'New business',fields:['New business','Renewal'],currency:'USD',stackable:true,valueDecimals:0})
  ],'Recurring revenue and sales');
  row('mix',[
   chart('saas-customer-trend','Active customers by month','saas',s.monthly,s.current,line(['Customers'],null)),
   chart('saas-segments','Ending ARR by segment','saas',s.segments,s.current.filter(r=>r.month===p.end),{type:'horizontalBar',x:'segment',y:'ARR',currency:'USD',stackable:false,valueDecimals:0})
  ]);
  row('customers',[table('saas-customer-table','Customer portfolio','saas',s.customers,s.current,[col('customer','Customer'),col('segment','Segment'),col('arr','Ending ARR',exactUsd),col('revenue','Period revenue',exactUsd)],{searchable:true})],'Customer and contract detail');
  row('contracts',[table('saas-contract-table','Signed contracts','bookings',s.cb.map(r=>({...r,period:monthLabel(r.month),booked:r.booked_value_cents/100})),s.cb,[col('period','Month'),col('customer','Customer'),col('booking_type','Type'),col('contract_id','Contract'),col('booked','Annual value',exactUsd)],{searchable:true})]);
 }else{
  row('metrics',[
   metric('workforce-headcount','Ending headcount',w.actual.headcount,num,'workforce',sourceW,w.prior?.headcount),
   metric('workforce-fte','Ending FTE',w.actual.fte,num,'workforce',sourceW,w.prior?.fte),
   metric('workforce-cost','Personnel costs',w.actual.cost,usd,'workforce',sourceW,w.prior?.cost),
   metric('workforce-unit-cost','Cost per FTE-month',w.actual.costPerFte,usd,'workforce',sourceW,w.prior?.costPerFte,0,'Period personnel cost divided by the sum of monthly FTE. A weighted monthly cost, not cost divided by ending headcount.')
  ],null,'metrics');
  row('trends',[
   chart('workforce-headcount-trend','Headcount and FTE','workforce',w.monthly,w.current,line(['Headcount','FTE'],null)),
   chart('workforce-cost-trend','Monthly personnel costs','workforce',w.monthly,w.current,{type:'bar',x:'month',y:'Base pay',fields:['Base pay','Variable pay','Benefits'],currency:'USD',stackable:true,valueDecimals:0})
  ],'Workforce and cost trajectory');
  row('departments',[
   chart('workforce-department-cost','Personnel cost by department','workforce',w.departments,w.current,{type:'horizontalStackedBar',x:'department',y:'Base pay',fields:['Base pay','Variable pay','Benefits'],currency:'USD',valueDecimals:0}),
   chart('workforce-department-headcount','Ending headcount by department','workforce',w.departments,w.current.filter(r=>r.month===p.end),{type:'horizontalBar',x:'department',y:'headcount',stackable:false,valueDecimals:0})
  ],'Department composition');
  row('detail',[table('workforce-detail','Department workforce detail','workforce',w.departments,w.current,[col('department','Department'),col('headcount','Ending headcount',num),col('fte','Ending FTE',num),col('cost','Personnel cost',exactUsd),col('Base pay','Base pay',exactUsd),col('Variable pay','Variable pay',exactUsd),col('Benefits','Benefits',exactUsd)])]);
 }
 const scope=tab==='dashboard'?(f.hasBudget?'Comparison: BUD2025':`Comparison: prior period${p.priorComplete?' · '+p.priorLabel:' unavailable'}. BUD2025 is only available for selections wholly within 2025.`):`Comparison: ${p.priorComplete?p.priorLabel:'prior period unavailable'}. ARR, customers, headcount and FTE use ending balances.`;
 return <>
  <Filters sticky filters={snapshot.filters.filter(f=>f.id!=='date'&&tabs.find(t=>t.id===tab).filterIds.includes(f.id))} queries={queries} values={filters} onChange={(k,v)=>{setDetail(null);setFilter(k,v)}} clearLabel="Reset filters">
   <Dropdown label="From" showLabel value={p.start} choices={months.filter(m=>m<=p.end)} onChange={v=>{setDetail(null);setFilter('date',`${v}..${p.end}`)}} formatChoice={monthLabel}/>
   <Dropdown label="Through" showLabel value={p.end} choices={months.filter(m=>m>=p.start)} onChange={v=>{setDetail(null);setFilter('date',`${p.start}..${v}`)}} formatChoice={monthLabel}/>
  </Filters>
  <div className="finance-scope"><span>{p.label} · Full months · USD</span><span>{scope}</span><span>Fictional company · snapshot through Sep 2026</span></div>
  {detail?.type==='account'&&tab==='dashboard'&&<button className="finance-back" onClick={()=>setDetail(null)}>Close account detail</button>}
  <SortableRegion key={tab} id={`juniper:${tab}`} label="Finance dashboard blocks" variant="canvas" columns={12} authoredRevision={1} spacing="standard" rows={layout}>
   {layout.flatMap(r=>r.items).map(id=><SortableItem key={id} id={id} label={blocks[id].title} kind={blocks[id].kind} span={blocks[id].span}>{blocks[id].node}</SortableItem>)}
  </SortableRegion>
 </>;
}
