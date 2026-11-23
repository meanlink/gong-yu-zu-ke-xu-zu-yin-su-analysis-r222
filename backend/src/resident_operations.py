from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .db import connect, query
from .lease_desk.rules import today as lease_today

SHANGHAI = timezone(timedelta(hours=8))
REMEDIES = '''SELECT r.*, t.full_name AS tenant_name, t.lease_end_date, p.code AS property_code,
    e.category, e.summary, e.status AS event_status, e.resolution_days,
    (r.evidence_at AT TIME ZONE 'Asia/Shanghai')::date > r.promise_due AS evidence_late
    FROM retention_remedy r JOIN follow_up_tasks f ON f.id=r.task_id JOIN tenants t ON t.id=f.tenant_id
    JOIN properties p ON p.id=t.property_id JOIN service_events e ON e.id=r.event_id'''
CHECKOUTS = '''SELECT c.*, t.full_name AS tenant_name, p.code AS property_code,
    t.status AS tenant_status, p.occupancy_status FROM checkout_appointment c
    JOIN tenants t ON t.id=c.tenant_id JOIN properties p ON p.id=c.property_id'''
RESULTS = '''SELECT r.*, t.full_name AS tenant_name, p.code AS property_code, p.neighborhood,
    CASE r.result WHEN 'renewed' THEN 10 ELSE 0 END - r.intent_score AS intent_delta
    FROM renewal_result r JOIN tenants t ON t.id=r.tenant_id JOIN properties p ON p.id=t.property_id'''


def get(conn, sql, params, error):
    row = conn.execute(sql, params).fetchone()
    if not row:
        raise HTTPException(404, error)
    return row


def audit(conn, user, action, entity, record_id, detail):
    conn.execute('INSERT INTO audit_logs(actor_email,action,entity_type,entity_id,detail) VALUES (%s,%s,%s,%s,%s)',
                 (user['email'], action, entity, record_id, detail))


def lock_context(conn, task_id, must_be_open=False):
    ref = get(conn, 'SELECT tenant_id FROM follow_up_tasks WHERE id=%s', (task_id,), '续租跟进任务不存在')
    tenant = get(conn, 'SELECT * FROM tenants WHERE id=%s FOR UPDATE', (ref['tenant_id'],), '租客不存在')
    task = get(conn, '''SELECT f.*, s.renewal_intent FROM follow_up_tasks f JOIN renewal_surveys s ON s.id=f.survey_id
        WHERE f.id=%s FOR UPDATE OF f''', (task_id,), '续租跟进任务不存在')
    if task['lease_end_snapshot'] != tenant['lease_end_date']:
        raise HTTPException(409, '该跟进任务属于历史租期，请选择当前租期的任务')
    if must_be_open and (task['status'] == 'closed' or tenant['status'] != 'active'):
        raise HTTPException(409, '只能使用在住租客未结束的跟进任务')
    return task, tenant


def list_remedies():
    return query(REMEDIES + ' ORDER BY r.id DESC')


def list_checkouts():
    return query(CHECKOUTS + ' ORDER BY c.starts_at DESC,c.id DESC')


def list_results():
    with connect() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        rows = conn.execute(RESULTS + ' ORDER BY r.id DESC').fetchall()
        cohorts = conn.execute('''WITH labelled AS (
            SELECT *, CASE WHEN intent_score >= 7 THEN 'high' WHEN intent_score >= 5 THEN 'middle' ELSE 'low' END AS cohort
            FROM renewal_result WHERE status='confirmed')
            SELECT cohort, count(*) AS samples, round(avg(intent_score),2) AS mean_intent,
                count(*) FILTER (WHERE result='renewed') AS renewed,
                round(100.0 * count(*) FILTER (WHERE result='renewed') / count(*),1) AS renewal_rate,
                round(avg(CASE result WHEN 'renewed' THEN 10 ELSE 0 END - intent_score),2) AS mean_delta
            FROM labelled GROUP BY cohort ORDER BY min(intent_score) DESC''').fetchall()
    return {'rows': rows, 'cohorts': cohorts}


def assign_remedy(item, user):
    today = datetime.now(SHANGHAI).date()
    with connect() as conn:
        task, tenant = lock_context(conn, item.task_id, must_be_open=True)
        event = get(conn, 'SELECT * FROM service_events WHERE id=%s FOR UPDATE', (item.event_id,), '报修事件不存在')
        if event['opened_at'] > datetime.now(timezone.utc):
            raise HTTPException(422, '报修登记时间尚未到达')
        if event['tenant_id'] != tenant['id'] or event['property_id'] != tenant['property_id'] or event['status'] == 'cancelled':
            raise HTTPException(422, '只能关联该租客和房源的有效报修')
        if not today <= item.promise_due <= tenant['lease_end_date']:
            raise HTTPException(422, '整改承诺日须在今日和当前租期结束之间')
        if conn.execute('SELECT id FROM retention_remedy WHERE event_id=%s', (event['id'],)).fetchone():
            raise HTTPException(409, '此报修已有整改承诺')
        row = conn.execute('''INSERT INTO retention_remedy(task_id,event_id,promise_due,tenant_impact,created_by)
            VALUES (%s,%s,%s,%s,%s) RETURNING id''', (task['id'], event['id'], item.promise_due, item.tenant_impact, user['id'])).fetchone()
        audit(conn, user, 'remedy_assigned', 'retention_remedy', row['id'], item.tenant_impact)
        return conn.execute(REMEDIES + ' WHERE r.id=%s', (row['id'],)).fetchone()


def update_remedy(record_id, action, item, user):
    with connect() as conn:
        ref = get(conn, 'SELECT task_id FROM retention_remedy WHERE id=%s', (record_id,), '整改承诺不存在')
        _, tenant = lock_context(conn, ref['task_id'])
        row = get(conn, 'SELECT * FROM retention_remedy WHERE id=%s FOR UPDATE', (record_id,), '整改承诺不存在')
        if action == 'submit':
            if row['status'] not in ('assigned', 'rework') or tenant['status'] != 'active':
                raise HTTPException(409, '仅可报验待整改或退回的在住租客工单')
            conn.execute('''UPDATE retention_remedy SET status='pending_check',evidence=%s,evidence_at=now(),evidence_by=%s,
                revision=revision+1,reviewed_by=NULL,review_note=NULL WHERE id=%s''', (item.note, user['id'], record_id))
            status = 'pending_check'
        else:
            if row['status'] != 'pending_check':
                raise HTTPException(409, '仅可处理待验收的整改')
            status = 'accepted' if action == 'accept' else 'rework'
            if status == 'accepted':
                if tenant['status'] != 'active':
                    raise HTTPException(409, '租客已退租，无法验收留租整改')
                conn.execute('''UPDATE service_events SET status='resolved',resolved_at=%s,
                    resolution_days=round(greatest(0,extract(epoch FROM (%s - opened_at))) / 86400,2)
                    WHERE id=%s AND status='open' ''', (row['evidence_at'], row['evidence_at'], row['event_id']))
            conn.execute('UPDATE retention_remedy SET status=%s,reviewed_by=%s,review_note=%s WHERE id=%s',
                         (status, user['id'], item.note, record_id))
        audit(conn, user, 'remedy_' + status, 'retention_remedy', record_id, item.note)
        return conn.execute(REMEDIES + ' WHERE r.id=%s', (record_id,)).fetchone()


def schedule_checkout(item, user):
    ends = item.starts_at + timedelta(minutes=item.duration_minutes)
    local = item.starts_at.astimezone(SHANGHAI)
    with connect() as conn:
        task, tenant = lock_context(conn, item.task_id, must_be_open=True)
        expiry = tenant['lease_end_date']
        if conn.execute("""SELECT 1 FROM renewal_offer WHERE tenant_id=%s AND lease_end=%s
                AND (status='signed' OR (status='issued' AND valid_through>=%s))""",(tenant['id'],expiry,lease_today())).fetchone():
            raise HTTPException(409, '有效报价或已签合同阻止安排退租交接')
        if item.starts_at <= datetime.now(timezone.utc) or not expiry - timedelta(days=30) <= local.date() <= expiry + timedelta(days=7):
            raise HTTPException(422, '请选择未来时段，且交接日期在租期结束前 30 日至结束后 7 日')
        conn.execute('SELECT id FROM properties WHERE id=%s FOR UPDATE', (tenant['property_id'],))
        if conn.execute('''SELECT id FROM renewal_result WHERE tenant_id=%s AND lease_end=%s
            AND status IN ('submitted','confirmed') AND result='renewed' ''', (tenant['id'], expiry)).fetchone():
            raise HTTPException(409, '该租期已有待复核或已确认的续租结果')
        if conn.execute('''SELECT id FROM checkout_appointment WHERE tenant_id=%s AND lease_end=%s AND status <> 'cancelled' ''',
                        (tenant['id'], expiry)).fetchone():
            raise HTTPException(409, '该租期已有未取消交接预约')
        if conn.execute('''SELECT id FROM checkout_appointment WHERE property_id=%s AND status <> 'cancelled'
            AND starts_at < %s AND ends_at > %s''', (tenant['property_id'], ends, item.starts_at)).fetchone():
            raise HTTPException(409, '同一房源该时段已有交接，调整到其他时间再预约')
        row = conn.execute('''INSERT INTO checkout_appointment(task_id,tenant_id,property_id,lease_end,starts_at,ends_at,instructions,created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''', (task['id'], tenant['id'], tenant['property_id'], expiry,
            item.starts_at, ends, item.instructions, user['id'])).fetchone()
        audit(conn, user, 'checkout_scheduled', 'checkout_appointment', row['id'], item.instructions)
        return conn.execute(CHECKOUTS + ' WHERE c.id=%s', (row['id'],)).fetchone()


def update_checkout(record_id, action, item, user):
    with connect() as conn:
        ref = get(conn, 'SELECT task_id FROM checkout_appointment WHERE id=%s', (record_id,), '交接预约不存在')
        _, tenant = lock_context(conn, ref['task_id'])
        conn.execute('SELECT id FROM properties WHERE id=%s FOR UPDATE', (tenant['property_id'],))
        row = get(conn, 'SELECT * FROM checkout_appointment WHERE id=%s FOR UPDATE', (record_id,), '交接预约不存在')
        if row['status'] != 'scheduled':
            raise HTTPException(409, '只有已预约的交接可以执行或取消')
        if action == 'cancel':
            conn.execute("UPDATE checkout_appointment SET status='cancelled',acted_by=%s WHERE id=%s", (user['id'], record_id))
            audit(conn, user, 'checkout_cancelled', 'checkout_appointment', record_id, item.note)
        else:
            if tenant['status'] != 'active' or tenant['lease_end_date'] != row['lease_end'] or tenant['property_id'] != row['property_id']:
                raise HTTPException(409, '在住状态、租期或房源已变化，无法完成交接')
            if datetime.now(timezone.utc) < row['starts_at'] - timedelta(minutes=30):
                raise HTTPException(409, '交接开始前 30 分钟内方可登记验房与钥匙')
            conn.execute('''UPDATE checkout_appointment SET status='completed',acted_by=%s,inspection_reference=%s,
                returned_keys=%s,unit_condition=%s WHERE id=%s''', (user['id'], item.inspection_reference, item.returned_keys, item.unit_condition, record_id))
            conn.execute("UPDATE tenants SET status='moved_out' WHERE id=%s", (tenant['id'],))
            conn.execute('''UPDATE properties SET occupancy_status='vacant' WHERE id=%s
                AND NOT EXISTS (SELECT 1 FROM tenants WHERE property_id=%s AND status='active')''', (row['property_id'], row['property_id']))
            abandoned = conn.execute('''UPDATE retention_remedy r SET status='cancelled' FROM follow_up_tasks f
                WHERE f.id=r.task_id AND f.tenant_id=%s AND f.lease_end_snapshot=%s
                AND r.status NOT IN ('accepted','cancelled') RETURNING r.id''', (tenant['id'], row['lease_end'])).fetchall()
            for remedy in abandoned:
                audit(conn, user, 'remedy_cancelled', 'retention_remedy', remedy['id'], f'退租交接 #{record_id} 已完成')
            audit(conn, user, 'checkout_completed', 'checkout_appointment', record_id, item.inspection_reference)
        return conn.execute(CHECKOUTS + ' WHERE c.id=%s', (record_id,)).fetchone()


def validate_result(conn, task, tenant, result, new_expiry):
    expiry = tenant['lease_end_date']
    checkout = conn.execute('''SELECT * FROM checkout_appointment WHERE tenant_id=%s AND lease_end=%s
        AND status <> 'cancelled' ''', (tenant['id'], expiry)).fetchone()
    if result == 'moved_out':
        if not checkout or checkout['status'] != 'completed' or checkout['task_id'] != task['id'] or new_expiry is not None:
            raise HTTPException(409, '退租结果需要同一跟进任务的已完成交接')
        return checkout['id']
    if tenant['status'] != 'active' or checkout:
        raise HTTPException(409, '有有效退租交接或已退租，不得确认续租')
    offer = conn.execute("""SELECT o.status,o.proposed_end, EXISTS(SELECT 1 FROM renewal_invoice_check i
        WHERE i.offer_id=o.id AND i.status='matched') billing_matched FROM renewal_offer o
        WHERE o.tenant_id=%s AND o.lease_end=%s AND (o.status='signed' OR (o.status='issued' AND o.valid_through>=%s))""",
        (tenant['id'],expiry,lease_today())).fetchone()
    if offer and (offer['status']!='signed' or not offer['billing_matched'] or new_expiry!=offer['proposed_end']):
        raise HTTPException(409, '续租实绩须匹配已签合同租期，并完成首账单核对')
    if not new_expiry or new_expiry < expiry + timedelta(days=30):
        raise HTTPException(422, '续租期至少比原租期延长 30 日')
    if conn.execute('''SELECT r.id FROM retention_remedy r JOIN follow_up_tasks f ON f.id=r.task_id
        WHERE f.tenant_id=%s AND f.lease_end_snapshot=%s AND r.status IN ('assigned','pending_check','rework') LIMIT 1''', (tenant['id'], expiry)).fetchone():
        raise HTTPException(409, '该租客还有未完成验收的续租整改')
    return None


def submit_result(item, user):
    with connect() as conn:
        task, tenant = lock_context(conn, item.task_id)
        appointment = validate_result(conn, task, tenant, item.result, item.new_lease_end)
        saved = conn.execute('''INSERT INTO renewal_result(task_id,tenant_id,lease_end,result,intent_score,
            appointment_id,new_lease_end,supporting_reference,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id,lease_end) DO UPDATE SET task_id=EXCLUDED.task_id,result=EXCLUDED.result,
                intent_score=EXCLUDED.intent_score,appointment_id=EXCLUDED.appointment_id,new_lease_end=EXCLUDED.new_lease_end,
                supporting_reference=EXCLUDED.supporting_reference,created_by=EXCLUDED.created_by,status='submitted',
                revision=renewal_result.revision+1,reviewed_by=NULL,review_note=NULL
            WHERE renewal_result.status='returned' RETURNING id,revision''', (task['id'], tenant['id'], tenant['lease_end_date'],
            item.result, task['renewal_intent'], appointment, item.new_lease_end, item.supporting_reference, user['id'])).fetchone()
        if not saved:
            raise HTTPException(409, '该租期已有待复核或已确认的结果')
        audit(conn, user, 'result_submitted', 'renewal_result', saved['id'], f"第 {saved['revision']} 版 · {item.supporting_reference}")
        return conn.execute(RESULTS + ' WHERE r.id=%s', (saved['id'],)).fetchone()


def review_result(record_id, action, item, user):
    with connect() as conn:
        ref = get(conn, 'SELECT task_id FROM renewal_result WHERE id=%s', (record_id,), '结果样本不存在')
        task, tenant = lock_context(conn, ref['task_id'])
        row = get(conn, 'SELECT * FROM renewal_result WHERE id=%s FOR UPDATE', (record_id,), '结果样本不存在')
        if row['status'] != 'submitted':
            raise HTTPException(409, '只有待复核样本可以处理')
        status = 'returned'
        if action == 'confirm':
            if row['lease_end'] != tenant['lease_end_date']:
                raise HTTPException(409, '租期已经变化，须退回核对')
            validate_result(conn, task, tenant, row['result'], row['new_lease_end'])
            if row['result'] == 'renewed':
                conn.execute('UPDATE tenants SET lease_end_date=%s WHERE id=%s', (row['new_lease_end'], tenant['id']))
            conn.execute("UPDATE follow_up_tasks SET status='closed' WHERE id=%s", (task['id'],))
            status = 'confirmed'
        conn.execute('UPDATE renewal_result SET status=%s,reviewed_by=%s,review_note=%s WHERE id=%s', (status, user['id'], item.note, record_id))
        audit(conn, user, 'result_' + status, 'renewal_result', record_id, item.note)
        return conn.execute(RESULTS + ' WHERE r.id=%s', (record_id,)).fetchone()
