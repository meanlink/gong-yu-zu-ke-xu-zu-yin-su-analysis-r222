import {leaseLabels, renderLease} from './lease-desk/workspace.js';
import {residentLabels,renderResident} from './resident-operations.js';
import {api, saveSession, clearSession, session} from './api.js';
import {el, table, toast, badge} from './components.js';

const state = {user: session(), page: location.hash.slice(1) || 'dashboard'};
const app = document.querySelector('#app');
const pages = ['dashboard','properties','services','renewals',...Object.keys(residentLabels)];
const labels = {dashboard:'运营总览', properties:'房源档案', services:'报修服务', renewals:'问卷与跟进', ...residentLabels, ...leaseLabels};

function loginView(){
  app.innerHTML='';
  const shell = el('main',{class:'login-shell'},[
    el('section',{class:'login-visual'},[
      el('div',{class:'eyebrow',text:'HARBORSTAY / RETENTION SIGNALS'}),
      el('h1',{text:'把续租意愿，拆成可以跟进的信号。'}),
      el('p',{text:'连接房源、服务事件和租客问卷，让客户经营从月底猜测变成有证据的动作。'}),
      el('div',{class:'signal-line'},[el('span',{text:'住房运营分析'}),el('span',{text:'2026 Q4'}),el('span',{text:'租客关系组'})])
    ]),
    el('section',{class:'login-panel'},[
      el('div',{class:'panel-kicker',text:'内部工作台'}), el('h2',{text:'登录续租信号台'}),
      el('p',{class:'muted',text:'选择角色账号进入对应业务动作。演示密码：rental123'}),
      el('form',{id:'login-form'},[
        el('label',{},['账号',el('input',{name:'email',value:'analyst@harborstay.local',required:true})]),
        el('label',{},['密码',el('input',{name:'password',type:'password',value:'rental123',required:true})]),
        el('button',{class:'button primary',type:'submit',text:'进入工作台'})
      ]),
      el('div',{class:'role-notes'},[el('div',{},[badge('分析师','blue'),'运行模型、复核样本']),el('div',{},[badge('客户经理','orange'),'审批分析、处理跟进']),el('div',{},[badge('服务协调','green'),'维护报修事件'])])
    ])
  ]);
  app.append(shell);
  document.querySelector('#login-form').addEventListener('submit', async e=>{e.preventDefault(); const fd=new FormData(e.target); try{const data=await api('/auth/login',{method:'POST',body:JSON.stringify({email:fd.get('email'),password:fd.get('password')})}); saveSession(data); state.user=data.user; render();}catch(err){toast(err.message,'error')}});
}
function shell(){
  app.innerHTML='';
  const nav = el('aside',{class:'side-nav'},[
    el('div',{class:'brand'},[el('div',{class:'brand-mark',text:'HS'}),el('div',{},[el('strong',{text:'海棠湾'}),el('small',{text:'续租信号台'})])]),
    el('div',{class:'nav-label',text:'工作区'}),
    ...pages.map(p=>el('a',{href:`#${p}`,class:state.page===p?'active':''},[el('span',{class:'nav-dot'}),labels[p]])),
    el('div',{class:'nav-spacer'}),
    el('div',{class:'user-block'},[el('small',{text:state.user.full_name}),el('span',{text:state.user.role==='customer_manager'?'客户经理':state.user.role==='analyst'?'数据分析师':'服务协调员'})]),
    el('button',{class:'button ghost',onClick:()=>{clearSession();state.user=null;loginView();},text:'退出'})
  ]);
  const main = el('main',{class:'main-area'});
  app.append(nav,main); return main;
}
async function dashboard(main){
  const [d, a, tasks] = await Promise.all([api('/dashboard'), api('/analysis/latest'), api('/followups')]);
  main.append(el('div',{class:'page-head'},[
    el('div',{},[
      el('div',{class:'eyebrow',text:'RETENTION OPERATIONS / 2026 Q4'}),
      el('h1',{text:'续租信号总览'}),
      el('p',{class:'muted',text:'从服务体验到续租动作，今天先处理最需要被听见的租客。'})
    ]),
    el('div',{class:'head-meta',text:`更新于 ${new Date().toLocaleString('zh-CN',{hour12:false})}`})
  ]));
  main.append(el('section',{class:'metric-row'},[
    metric('在管房源',d.properties,'units'),
    metric('活跃租客',d.active_tenants,'residents'),
    metric('待跟进',d.followups,'actions'),
    metric('平均意愿',Number(d.avg_intent).toFixed(1)+'/10','intent')
  ]));
  const taskRows = tasks.slice(0,4).map(t => el('div',{class:'task-row'},[
    badge(t.priority,t.priority==='high'?'red':'orange'),
    el('div',{},[
      el('strong',{text:t.tenant_name}),
      el('small',{text:t.reason})
    ]),
    el('span',{class:'task-date',text:t.due_date})
  ]));
  main.append(el('section',{class:'split-grid'},[
    el('div',{class:'panel large'},[
      el('div',{class:'panel-title'},[el('h2',{text:'模型摘要'}),badge('Python 计算','blue')]),
      el('div',{class:'finding'},[
        el('div',{class:'finding-number',text:String(a.partial_correlation)}),
        el('div',{},[
          el('strong',{text:'偏相关系数'}),
          el('p',{class:'muted',text:a.partial_corr_label}),
          el('p',{class:'interpret',text:a.explanation})
        ])
      ]),
      el('div',{class:'model-strip'},[
        el('span',{text:`样本 ${a.sample_size} 份`}),
        el('span',{text:`R² ${a.stepwise.r2}`}),
        el('span',{text:`入模 ${a.stepwise.selected_features.join(' · ')}`})
      ])
    ]),
    el('div',{class:'panel'},[
      el('div',{class:'panel-title'},[
        el('h2',{text:'今日跟进清单'}),
        el('a',{href:'#renewals',class:'text-link',text:'查看全部'})
      ]),
      ...taskRows
    ])
  ]));
  main.append(el('section',{class:'callout'},[
    el('div',{},[
      el('div',{class:'eyebrow',text:'下一步'}),
      el('h2',{text:'让一次报修，成为一次关系修复。'}),
      el('p',{class:'muted',text:'先看服务解决时长和服务评分，再决定谁需要电话、谁适合发续租方案。'})
    ]),
    el('a',{href:'#renewals',class:'button secondary',text:'打开续租复核'})
  ]));
}
function metric(title,value,kind){return el('div',{class:`metric ${kind}`},[el('span',{class:'metric-label',text:title}),el('strong',{text:String(value)}),el('span',{class:'metric-rule',text:kind==='actions'?'需要客户经理动作':'来自实时业务表'})]);}
async function properties(main){ const [ps,ts]=await Promise.all([api('/properties'),api('/tenants')]); main.append(pageTitle('房源档案','看清租金、房龄和在住关系，为续租解释保留上下文。')); main.append(el('section',{class:'panel'},[el('div',{class:'panel-title'},[el('h2',{text:'房源与租客关系'}),badge(`${ps.length} 套房源`,'blue')]),table(['房源','片区','租金','楼层','房龄','租客','状态'],ps.map(p=>{const t=ts.find(x=>x.property_id===p.id);return [p.code,p.neighborhood,`¥${p.monthly_rent}`,`${p.floor}F`,`${p.property_age_years}年`,t?.full_name||'—',badge(t?.status==='active'?'在住':'已退租',t?.status==='active'?'green':'neutral').textContent]}))])); }
async function services(main){ const [events,ts]=await Promise.all([api('/service-events'),api('/tenants')]); main.append(pageTitle('报修服务','服务事件是续租解释的重要前因，先让处理过程可见。')); const form=el('form',{class:'inline-form',id:'service-form'},[select('tenant_id','租客',ts.filter(t=>t.status==='active').map(t=>[t.id,t.full_name])),select('category','问题类别',[['漏水','漏水'],['空调','空调'],['网络','网络'],['清洁','清洁'],['电梯','电梯']]),select('severity','紧急度',[['routine','常规'],['urgent','紧急'],['emergency','特急']]),el('input',{name:'summary',placeholder:'简述服务事件',required:true}),el('button',{class:'button primary',type:'submit',text:'登记事件'})]); main.append(el('section',{class:'panel'},[el('div',{class:'panel-title'},[el('h2',{text:'新增服务事件'}),badge('服务协调员 / 客户经理','green')]),form])); main.append(el('section',{class:'panel'},[el('div',{class:'panel-title'},[el('h2',{text:'近期服务记录'}),badge(`${events.length} 条`,'blue')]),table(['租客','房源','类别','紧急度','耗时','评分','状态'],events.map(e=>[e.tenant_name,e.property_code,e.category,e.severity,e.resolution_days?`${e.resolution_days} 天`:'处理中',e.satisfaction_score||'—',e.status==='resolved'?'已解决':'处理中']))])); document.querySelector('#service-form').addEventListener('submit',async e=>{e.preventDefault();const fd=new FormData(e.target);try{await api('/service-events',{method:'POST',body:JSON.stringify({tenant_id:Number(fd.get('tenant_id')),category:fd.get('category'),severity:fd.get('severity'),summary:fd.get('summary'),status:'resolved',satisfaction_score:4})});toast('服务事件已登记','success');render()}catch(err){toast(err.message,'error')}}); }
async function renewals(main){
  const [surveys,tasks] = await Promise.all([api('/surveys'),api('/followups')]);
  main.append(pageTitle('问卷与跟进','把问卷采集、解释模型和客户经营复核放在同一条链上。'));
  const tenantOptions = [...new Map(surveys.map(s=>[s.tenant_id,[s.tenant_id,s.tenant_name]])).values()];
  const form = el('form',{class:'survey-form',id:'survey-form'},[
    select('tenant_id','选择租客',tenantOptions),
    el('input',{name:'lease_period',value:'2026-2027',placeholder:'租期',required:true}),
    scoreInput('cleanliness_score','整洁'),
    scoreInput('service_score','服务'),
    scoreInput('value_score','性价比'),
    scoreInput('community_score','社区'),
    el('input',{name:'renewal_intent',type:'number',min:1,max:10,step:1,value:'6',placeholder:'续租意愿 1-10'}),
    el('input',{name:'comments',placeholder:'租客原话或跟进备注'}),
    el('button',{class:'button primary',type:'submit',text:'采集问卷'})
  ]);
  main.append(el('section',{class:'panel'},[
    el('div',{class:'panel-title'},[el('h2',{text:'问卷采集'}),badge('重复问卷将被阻断','orange')]),
    form
  ]));
  const surveyRows = surveys.map(s=>[
    s.tenant_name,s.lease_period,s.service_score,`${s.renewal_intent}/10`,
    s.status==='reviewed'?'已复核':'待复核',s.comments
  ]);
  const taskCards = tasks.map(t=>{
    const close = t.status!=='closed' && state.user.role==='customer_manager' ? el('button',{class:'button tiny',text:'标记已跟进',onClick:async()=>{
      await api(`/followups/${t.id}/close`,{method:'POST'}); toast('任务已关闭','success'); render();
    }}) : null;
    return el('div',{class:'task-card'},[
      el('div',{class:'task-card-top'},[badge(t.priority,t.priority==='high'?'red':'orange'),el('strong',{text:t.tenant_name})]),
      el('p',{text:t.reason}),
      el('small',{text:`${t.property_code} · 截止 ${t.due_date}`}),
      close
    ]);
  });
  main.append(el('section',{class:'split-grid'},[
    el('div',{class:'panel'},[
      el('div',{class:'panel-title'},[el('h2',{text:'问卷样本'}),badge(`${surveys.length} 份`,'blue')]),
      table(['租客','租期','服务','意愿','状态','备注'],surveyRows)
    ]),
    el('div',{class:'panel'},[
      el('div',{class:'panel-title'},[el('h2',{text:'跟进清单'}),badge(`${tasks.length} 项`,'red')]),
      ...taskCards
    ])
  ]));
  const analysisButton = el('button',{class:'button secondary',text:'运行偏相关与逐步回归',onClick:async()=>{
    try{const a=await api('/analysis/run',{method:'POST'});toast(`分析完成，偏相关 ${a.partial_correlation}`,'success');render();}
    catch(err){toast(err.message,'error');}
  }});
  const reviewButton = state.user.role==='customer_manager' ? el('button',{class:'button orange',text:'客户经营复核并生成清单',onClick:async()=>{
    try{const r=await api('/reviews/approve',{method:'POST',body:JSON.stringify({note:'已复核模型解释与租客原话，安排分级沟通'})});toast(`已生成 ${r.created_followups} 条跟进`,'success');render();}
    catch(err){toast(err.message,'error');}
  }}) : null;
  main.append(el('section',{class:'action-bar'},[
    el('div',{},[
      el('strong',{text:'复核动作'}),
      el('p',{class:'muted',text:'客户经理确认后，只有活跃租客会进入跟进清单。已退租和重复问卷在后端被阻断。'})
    ]),
    el('div',{class:'action-row'},[analysisButton,reviewButton])
  ]));
  document.querySelector('#survey-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const fd=new FormData(e.target);
    try{
      await api('/surveys',{method:'POST',body:JSON.stringify({
        tenant_id:Number(fd.get('tenant_id')),lease_period:fd.get('lease_period'),
        cleanliness_score:Number(fd.get('cleanliness_score')),service_score:Number(fd.get('service_score')),
        value_score:Number(fd.get('value_score')),community_score:Number(fd.get('community_score')),
        renewal_intent:Number(fd.get('renewal_intent')),comments:fd.get('comments')
      })});
      toast('问卷已采集','success'); render();
    }catch(err){toast(err.message,'error');}
  });
}
function scoreInput(name,label){return el('label',{class:'compact'},[label,el('input',{name,type:'number',min:1,max:5,step:.1,value:'4'})]);}
function select(name,label,options){return el('label',{class:'compact'},[label,el('select',{name},options.map(o=>el('option',{value:o[0],text:o[1]})))]);}
function pageTitle(title,desc){return el('div',{class:'page-head'},[el('div',{},[el('div',{class:'eyebrow',text:'HARBORSTAY / OPERATIONS'}),el('h1',{text:title}),el('p',{class:'muted',text:desc})])]);}
async function render(){ if(!state.user){loginView();return;} const main=shell(); try{if(state.page==='dashboard')await dashboard(main);if(state.page==='properties')await properties(main);if(state.page==='services')await services(main);if(state.page==='renewals')await renewals(main);if(residentLabels[state.page])await renderResident(main,state.page,state.user,render);if(leaseLabels[state.page])await renderLease(main,state.page,state.user,render);}catch(err){main.append(el('div',{class:'error-state'},[el('h2',{text:'页面加载失败'}),el('p',{text:err.message}),el('button',{class:'button primary',text:'重试',onClick:render})]))}}
window.addEventListener('hashchange',()=>{state.page=location.hash.slice(1)||'dashboard';render()}); render();
