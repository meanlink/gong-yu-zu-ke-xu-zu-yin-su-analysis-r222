import {api} from './api.js';
import {el, badge, table} from './components.js';

export const residentLabels = {remedies:'续租阻碍整改', checkouts:'退租交接排班', outcomes:'续租意愿偏差复核'};
const labels = {assigned:'待整改', pending_check:'待验收', rework:'待补正', accepted:'已验收', scheduled:'已预约',
    cancelled:'已取消', completed:'已交接', submitted:'待复核', returned:'待补正', confirmed:'已确认',
    renewed:'已续租', moved_out:'已退租', ready:'可交付', repair:'需检修', high:'高意愿（7–10）', middle:'中意愿（5–<7）', low:'低意愿（1–<5）'};
const descriptions = {
    remedies:'把阻碍续租的报修问题变成给租客的整改承诺。协调员提交完成依据，客户经理验收后回写原报修。',
    checkouts:'在租期结束前 30 日至结束后 7 日安排验房和钥匙交接。同一房源的预约不得重叠，时间以北京时间为准。',
    outcomes:'对照问卷意愿与实际签约或交接结果。分析师确认后才计入分组实绩。',
};
const tones = {pending_check:'orange', rework:'red', accepted:'green', scheduled:'blue', completed:'green', confirmed:'green', returned:'red'};
const dateTime = value => new Intl.DateTimeFormat('zh-CN', {timeZone:'Asia/Shanghai', dateStyle:'medium', timeStyle:'short', hourCycle:'h23'}).format(new Date(value));
const ymd = value => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Shanghai', year:'numeric', month:'2-digit', day:'2-digit'}).format(value);
const number = value => Number(value).toLocaleString('zh-CN', {maximumFractionDigits:2});
const input = (label, name, attrs = {}) => el('label', {}, [label, el('input', {name, required:true, ...attrs})]);
const memo = (label, name = 'note') => el('label', {}, [label,
    el('textarea', {name, required:true, minlength:4, maxlength:300, rows:2})]);
const selection = (name, choices, placeholder = '请选择') => el('select', {name, required:true}, [el('option', {value:'', text:placeholder}),
    ...choices.map(([value, text]) => el('option', {value, text}))]);
const link = (text, path) => el('a', {class:'text-link', href:`#${path}`, text});
const primary = text => el('button', {class:'button primary', type:'submit', text});

function record(row, title, details, remarks, actions = []) {
    return el('article', {class:'panel resident-record'}, [
        el('header', {}, [el('h3', {text:title}), badge(labels[row.status], tones[row.status] || 'neutral')]),
        el('p', {class:'muted resident-meta', text:`${row.tenant_name} · ${row.property_code}`}),
        el('dl', {}, details.map(([label, text]) => el('div', {}, [el('dt', {text:label}), el('dd', {text})]))),
        ...remarks.filter(Boolean).map(text => el('p', {class:'resident-note', text})),
        actions.length ? el('div', {class:'action-row resident-actions'}, actions) : null,
    ]);
}

function newForm(title, controls, submitLabel, submit, prepare = data => data) {
    const form = el('form', {class:'resident-fields'}, [...controls, el('p', {class:'resident-feedback', role:'status'}), primary(submitLabel)]);
    bind(form, submit, prepare);
    return el('section', {class:'panel resident-form'}, [el('h2', {text:title}), form]);
}

function bind(form, submit, prepare) {
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]');
        const feedback = form.querySelector('[role=status]');
        const data = prepare(Object.fromEntries(new FormData(form)));
        button.disabled = true;
        feedback.textContent = '';
        try {
            await submit(data);
        } catch (err) {
            feedback.textContent = err.message;
        } finally {
            button.disabled = false;
        }
    });
}

function action(main, title, edit, submit, prepare = data => data) {
    return el('button', {type:'button', class:'button ghost', text:title, onClick:() => {
        const dismiss = el('button', {class:'button ghost', type:'button', text:'返回'});
        const form = el('form', {class:'resident-fields'}, [...edit(), el('p', {class:'resident-feedback', role:'status'}),
            el('div', {class:'action-row'}, [primary('确认'), dismiss])]);
        const dialog = el('dialog', {class:'panel resident-dialog'}, [el('h2', {text:title}), form]);
        dismiss.onclick = () => dialog.close();
        dialog.addEventListener('close', () => dialog.remove());
        bind(form, async data => { await submit(data); if (dialog.open) dialog.close(); }, prepare);
        main.append(dialog);
        dialog.showModal();
    }});
}

const taskChoices = tasks => tasks.map(task => [task.id, `${task.tenant_name} · ${task.property_code} · 跟进 #${task.id}`]);
const noChoices = (message, path, label) => el('section', {class:'panel resident-form'}, [el('p', {text:message}), link(label, path)]);

function remedies(main, rows, user, post, tasks, events) {
    const manager = user.role === 'customer_manager';
    const records = rows.map(row => {
        const actions = [];
        if (manager && row.status === 'pending_check') {
            actions.push(action(main, '验收通过', () => [memo('核验依据')], post(`${row.id}/accept`)),
                action(main, '退回整改', () => [memo('补正要求')], post(`${row.id}/return`)));
        }
        if (user.role === 'service_coordinator' && ['assigned','rework'].includes(row.status)) {
            actions.push(action(main, '提交验收', () => [memo('维修或复测记录')], post(`${row.id}/submit`)));
        }
        return record(row, `报修 #${row.event_id} · ${row.category}`, [['承诺日期', row.promise_due], ['实测版本', row.revision],
            ['原报修状态', {open:'待处理',resolved:'已结修',cancelled:'已取消'}[row.event_status]],
            ['解决用时', row.resolution_days == null ? '待核算' : `${number(row.resolution_days)} 天`],
            ['报验时效', row.evidence_at ? (row.evidence_late ? '超承诺日' : '按期') : '待报验']],
            [row.tenant_impact, row.evidence && `现场 · ${row.evidence}`, row.review_note && `验收 · ${row.review_note}`], actions);
    });
    if (!manager) return [records, null];
    const available = events.filter(event => event.status !== 'cancelled' && !rows.some(row => row.event_id === event.id));
    const tasksWithEvent = tasks.filter(task => available.some(event => event.tenant_id === task.tenant_id));
    if (!tasksWithEvent.length) return [records, noChoices('先为在住租客生成跟进，并确认存在同租客的可关联报修。','services','查看报修')];
    const task = selection('task_id', taskChoices(tasksWithEvent));
    const event = selection('event_id', [], '先选跟进任务');
    task.onchange = () => {
        const tenantId = tasksWithEvent.find(row => String(row.id) === task.value)?.tenant_id;
        const choices = available.filter(row => row.tenant_id === tenantId).map(row => [row.id, `#${row.id} · ${row.category} · ${row.summary}`]);
        event.replaceChildren(...selection('event_id', choices, '选择报修').children);
    };
    const edit = newForm('登记整改承诺', [el('label', {}, ['续租跟进', task]), el('label', {}, ['关联报修', event]),
        input('承诺完成日', 'promise_due', {type:'date', min:ymd(new Date())}), memo('对租客的影响与整改目标', 'tenant_impact')],
        '建立整改', post(''));
    return [records, edit];
}

function checkouts(main, rows, user, post, tasks) {
    const manager = user.role === 'customer_manager';
    const records = rows.map(row => {
        const actions = [];
        if (manager && row.status === 'scheduled') actions.push(action(main, '取消预约', () => [memo('取消原因')], post(`${row.id}/cancel`)));
        if (user.role === 'service_coordinator' && row.status === 'scheduled') {
            actions.push(action(main, '验房交接', () => [input('验房记录编号', 'inspection_reference', {minlength:4, maxlength:300}),
                input('退回钥匙数', 'returned_keys', {type:'number', step:1, min:0, max:20}),
                el('label', {}, ['验房房况', selection('unit_condition', [['ready','可交付'], ['repair','需检修']])])], post(`${row.id}/complete`)));
        }
        return record(row, `交接 #${row.id} · ${dateTime(row.starts_at)}`, [['截止时刻', dateTime(row.ends_at)],
            ['原租期结束', row.lease_end], ['钥匙', row.returned_keys ?? '待登记'], ['房况', labels[row.unit_condition] || '待验收'],
            ['房源状态', row.occupancy_status === 'vacant' ? '空置' : '仍在住']],
            [row.instructions, row.inspection_reference && `验房记录 · ${row.inspection_reference}`], actions);
    });
    if (!manager) return [records, null];
    const eligible = tasks.filter(task => !rows.some(row => row.tenant_id === task.tenant_id && row.lease_end === task.lease_end_snapshot && row.status !== 'cancelled'));
    return [records, eligible.length ? newForm('安排验房时段', [el('label', {}, ['在住租客跟进', selection('task_id', taskChoices(eligible))]),
        input('开始（北京时间）','starts_at',{type:'datetime-local'}),
        el('label', {}, ['时长', selection('duration_minutes', [[30,'30 分钟'], [60,'60 分钟'], [90,'90 分钟']])]),
        memo('预约地点与交接说明','instructions')], '预约交接', post(''), data => ({...data, starts_at:`${data.starts_at}:00+08:00`, duration_minutes:Number(data.duration_minutes)})) :
        noChoices('暂无可预约的在住租客跟进。','renewals','查看问卷与跟进')];
}

function outcomes(main, rows, user, post, tasks, tenants) {
    const records = rows.map(row => record(row, `${labels[row.result]} · 样本 #${row.id}`, [['原租期结束', row.lease_end], ['问卷意愿', `${number(row.intent_score)}/10`],
        ['实绩减意愿', `${number(row.intent_delta)} 分`], ['新租期结束 / 交接', row.new_lease_end ?? `交接 #${row.appointment_id}`], ['复核版本', row.revision]],
        [`凭证 · ${row.supporting_reference}`, row.review_note && `复核 · ${row.review_note}`],
        user.role === 'analyst' && row.status === 'submitted' ? [action(main, '确认并入组', () => [memo('复核依据')], post(`${row.id}/confirm`)),
            action(main, '退回样本', () => [memo('补正要求')], post(`${row.id}/return`))] : []));
    if (user.role !== 'customer_manager') return [records, null];
    const expiry = new Map(tenants.map(tenant => [tenant.id, tenant.lease_end_date]));
    const eligible = tasks.filter(task => task.lease_end_snapshot === expiry.get(task.tenant_id) && !rows.some(row =>
        row.tenant_id === task.tenant_id && row.lease_end === task.lease_end_snapshot && row.status !== 'returned'));
    if (!eligible.length) return [records, noChoices('暂无待登记的当前租期跟进。','renewals','查看跟进清单')];
    const result = selection('result', [['renewed','已签续租'],['moved_out','已完成退租交接']]);
    const end = input('新租期结束', 'new_lease_end', {type:'date'});
    end.hidden = true;
    end.querySelector('input').disabled = true;
    result.onchange = () => {
        end.hidden = result.value !== 'renewed';
        end.querySelector('input').disabled = end.hidden;
    };
    return [records, newForm('登记实际租期结果', [el('label', {}, ['续租跟进', selection('task_id', taskChoices(eligible))]),
        el('label', {}, ['实际结果', result]), end, memo('签约或验房凭证索引','supporting_reference')], '提交结果复核', post(''))];
}

export async function renderResident(main, page, user, rerender) {
    const path = `/resident-operations/${page}`;
    const post = suffix => async data => {
        await api(suffix ? `${path}/${suffix}` : path, {method:'POST', body:JSON.stringify(data)});
        if (main.isConnected) rerender();
    };
    const manager = user.role === 'customer_manager';
    const [response, tasks, tenants, events] = await Promise.all([api(path), manager ? api('/followups') : [], manager ? api('/tenants') : [],
        manager && page === 'remedies' ? api('/service-events') : []]);
    if (!main.isConnected) return;
    const occupancy = new Map(tenants.map(row => [row.id, row]));
    const open = tasks.filter(row => row.status !== 'closed' && occupancy.get(row.tenant_id)?.status === 'active' &&
        occupancy.get(row.tenant_id)?.lease_end_date === row.lease_end_snapshot);
    const [records, edit] = page === 'remedies' ? remedies(main, response, user, post, open, events) :
        page === 'checkouts' ? checkouts(main, response, user, post, open) : outcomes(main, response.rows, user, post, tasks, tenants);
    main.append(el('div', {class:'page-head resident-heading'}, [el('div', {}, [el('h1', {text:residentLabels[page]}),
        el('p', {class:'muted', text:descriptions[page]})])]));
    if (page === 'outcomes') {
        main.append(el('section', {class:'panel resident-cohorts'}, [el('h2', {text:'确认样本分组'}),
            el('p', {class:'muted', text:'实际续租按 10 分、退租按 0 分，与原意愿比较。样本仅覆盖已跟进租客。'}),
            table(['意愿组','确认样本','平均意愿','续租数','实际续租率','平均偏差'], response.cohorts.map(row => [labels[row.cohort], row.samples,
                number(row.mean_intent), row.renewed, `${number(row.renewal_rate)}%`, `${number(row.mean_delta)} 分`]), '分析师确认结果后生成分组。')]));
    }
    main.append(el('div', {class:edit ? 'resident-layout with-form' : 'resident-layout'}, [el('section', {class:'resident-register'}, [
        el('h2', {}, ['业务台账', el('small', {text:`${records.length} 单`})]),
        ...(records.length ? records : [el('p', {class:'panel muted', text:'当前没有单据，业务办理后会显示在这里。'})])]), edit]));
}
