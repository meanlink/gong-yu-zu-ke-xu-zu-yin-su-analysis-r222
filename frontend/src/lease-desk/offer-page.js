import {api} from '../api.js';
import {badge, el} from '../components.js';
import {field, form, leaseStatus, money, select, title} from './shared.js';

export async function offersPage(main,user,refresh) {
  const {offers,candidates,today}=await api('/lease-desk/offers');
  main.append(title('续租报价','以原租期次日为启租日。片区预算余额及退租交接状态决定报价是否可发出。'));
  if (user.role==='customer_manager' && candidates.length) main.append(el('section',{class:'panel'},[form('新建续租报价',[
    select('task_id','续租跟进',candidates.map(row=>[row.id,`${row.full_name} · ${row.neighborhood} · 截止 ${row.lease_end_date}`])),
    field('ref','报价编号'),field('term_months','续租月数',{type:'number',min:2,max:18,step:1}),
    field('monthly_discount_cents','每月让利（分）',{type:'number',min:0,step:1}),field('valid_through','报价有效期',{type:'date',min:today}),
    field('rationale','报价依据',{minlength:5}),
  ],'保存报价草稿','/lease-desk/offers',refresh)]));
  for (const row of offers) {
    const active=row.status==='issued' && row.valid_through>=today;
    const path=`/lease-desk/offers/${row.id}/transition`;
    const review=user.role==='analyst' && row.status==='draft' && row.valid_through>=today
      ? form('预算审核',[field('note','审核意见',{minlength:5})],'批准并发出',path,refresh,{extra:{decision:'issue'}}) : null;
    const close=user.role==='customer_manager' && ['issued','draft'].includes(row.status)
      ? form('结束报价',[select('decision','处理动作',active ? [['decline','登记租客拒绝'],['withdraw','撤回报价']] : [['withdraw','撤回报价']]),field('note','操作说明',{minlength:5})],'保存处理',path,refresh) : null;
    main.append(el('article',{class:'panel lease-card','data-offer':row.id},[
      el('div',{class:'panel-title'},[el('h2',{text:`${row.ref} · ${row.tenant_name}`}),badge(active || row.status!=='issued'?leaseStatus[row.status]:'报价已过期')]),
      el('p',{text:`${row.property_code} · ${row.lease_start} 至 ${row.proposed_end} · 有效至 ${row.valid_through}`}),
      el('p',{text:`月租 ${money(row.list_cents-row.monthly_discount_cents)} · 总让利 ${money(row.total_discount_cents)}`}),
      el('p',{class:'muted',text:row.closing_note||row.rationale}),review,close,
    ]));
  }
}
