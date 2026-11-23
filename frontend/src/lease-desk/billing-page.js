import {api} from '../api.js';
import {badge, el, table} from '../components.js';
import {field, form, leaseStatus, money, title} from './shared.js';

export async function billingPage(main,user,refresh) {
  const {offers,today}=await api('/lease-desk/contracts');
  main.append(title('签约与首账单','登记合同签约凭证，首账单按启租月实际天数折算。核对成功后进入续租实绩复核。'));
  for (const row of offers) {
    const path=`/lease-desk/contracts/${row.id}`;
    const matched=row.invoices.some(invoice=>invoice.status==='matched');
    const sign=user.role==='service_coordinator' && row.status==='issued' && row.valid_through>=today
      ? form('登记合同凭证',[field('contract_ref','已签合同编号'),field('signed_on','签约日',{type:'date',max:today})], '确认签约',path,refresh) : null;
    const check=user.role==='analyst' && row.contract && !matched
      ? form('核对首月账单',[field('invoice_ref','首账单凭证'),field('invoiced_cents','实际账单（分）',{type:'number',min:0,step:1}),field('note','核对依据',{minlength:5})],
        '登记账单核对',`${path}/invoices`,refresh) : null;
    main.append(el('article',{class:'panel lease-card','data-contract':row.id},[
      el('div',{class:'panel-title'},[el('h2',{text:`${row.ref} · ${row.tenant_name}`}),badge(matched?'首账单已匹配':leaseStatus[row.status])]),
      el('p',{text:`${row.property_code} · 启租 ${row.lease_start} · 续至 ${row.proposed_end}`}),
      row.contract ? el('p',{text:`${row.contract.contract_ref} · 首期至 ${row.contract.first_period_end} · 应收 ${money(row.contract.first_expected_cents)}`}) : null,
      row.contract ? table(['账单凭证','实际','应收','差额','结果'],row.invoices.map(invoice=>[invoice.invoice_ref,money(invoice.invoiced_cents),money(invoice.expected_cents),money(invoice.invoiced_cents-invoice.expected_cents),invoice.status==='matched'?'匹配':'存在差额'])) : null,
      sign,check,
    ]));
  }
  if (!offers.length) main.append(el('p',{class:'panel',text:'暂无已发出的续租报价。'}));
}
