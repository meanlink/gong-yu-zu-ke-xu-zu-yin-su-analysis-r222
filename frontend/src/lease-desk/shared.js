import {api} from '../api.js';
import {el, toast} from '../components.js';

const currency=new Intl.NumberFormat('zh-CN',{style:'currency',currency:'CNY'});
export const money = cents => currency.format(Number(cents)/100);
export const leaseStatus = {draft:'预算待批',issued:'报价已发',signed:'合同已签',declined:'租客拒绝',withdrawn:'已撤回'};
export const label = (title, input) => el('label',{class:'lease-field'},[el('span',{text:title}), input]);
export const field = (name,title,attrs={}) => label(title,el('input',{name,required:true,...attrs}));
export const select = (name,title,values) => label(title,el('select',{name,required:true}, values.map(([value,text])=>el('option',{value,text}))));
export const title = (name,copy) => el('header',{class:'page-head'},[el('div',{},[el('h1',{text:name}),el('p',{class:'muted',text:copy})])]);

export function form(heading, fields, submit, path, refresh, {method='POST',extra={}}={}) {
  const button=el('button',{class:'button primary',type:'submit',text:submit});
  const view=el('form',{class:'lease-form',onSubmit:async event=>{
    event.preventDefault(); button.disabled=true;
    try {
      const body={...Object.fromEntries(new FormData(view)),...extra};
      await api(path,{method,body:JSON.stringify(body)});
      toast('业务记录已保存','success'); await refresh();
    } catch(error) { toast(error.message,'error'); }
    finally { button.disabled=false; }
  }},[el('h3',{text:heading}),el('div',{class:'lease-grid'},fields),button]);
  return view;
}
