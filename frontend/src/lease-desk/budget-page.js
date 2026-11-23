import {api} from '../api.js';
import {el, table} from '../components.js';
import {field, form, money, select, title} from './shared.js';

export async function budgetPage(main,user,refresh) {
  const {budgets,neighborhoods}=await api('/lease-desk/budgets');
  main.append(title('片区让利预算','按新租期开始月份核算签约让利和当前有效报价承诺。'));
  if (user.role==='analyst') main.append(el('section',{class:'panel'},[form('设定让利额度',[
    select('neighborhood','房源片区',neighborhoods.map(item=>[item,item])),
    field('starts_month','启租月第一日',{type:'date'}),field('cap_cents','预算额度（分）',{type:'number',min:0,step:1}),
    field('justification','额度依据',{minlength:5}),
  ],'保存让利额度','/lease-desk/budgets',refresh,{method:'PUT'})]));
  main.append(el('section',{class:'panel'},[table(['片区','启租月','预算额度','已承诺','余额','口径'],
    budgets.map(row=>[row.neighborhood,row.starts_month,money(row.cap_cents),money(row.committed_cents),money(row.remaining_cents),row.justification]))]));
}
