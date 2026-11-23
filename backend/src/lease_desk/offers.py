from datetime import timedelta

from fastapi import HTTPException
from psycopg.errors import UniqueViolation

from ..db import connect
from ..resident_operations import audit, get, lock_context
from .budgets import committed
from .rules import lease_end, today


BASE = '''SELECT o.*,t.full_name tenant_name,p.code property_code
          FROM renewal_offer o JOIN tenants t ON t.id=o.tenant_id JOIN properties p ON p.id=t.property_id'''


def board():
    with connect() as conn:
        rows = conn.execute(BASE+' ORDER BY o.id DESC').fetchall()
        active = conn.execute('''SELECT DISTINCT ON (f.tenant_id) f.id,t.full_name,t.lease_end_date,p.neighborhood FROM follow_up_tasks f
            JOIN tenants t ON t.id=f.tenant_id JOIN properties p ON p.id=t.property_id
            WHERE t.status='active' AND f.status<>'closed' AND f.lease_end_snapshot=t.lease_end_date AND t.lease_end_date>= %s
            ORDER BY f.tenant_id,f.id DESC''',(today(),)).fetchall()
    return {'offers':rows,'candidates':active,'today':today()}


def create(payload,user):
    with connect() as conn:
        task,tenant=lock_context(conn,payload.task_id,must_be_open=True)
        expiry=tenant['lease_end_date']
        if not today()<=payload.valid_through<=expiry:
            raise HTTPException(422,'报价有效期须在今天至本租期截止期间')
        if conn.execute("SELECT 1 FROM checkout_appointment WHERE tenant_id=%s AND lease_end=%s AND status<>'cancelled'",
                        (tenant['id'],expiry)).fetchone():
            raise HTTPException(409,'已有退租交接的租客不能登记新续租报价')
        unit=get(conn,'SELECT neighborhood,monthly_rent FROM properties WHERE id=%s',(tenant['property_id'],),'房源不存在')
        rent=int(unit['monthly_rent']*100)
        if payload.monthly_discount_cents>=rent:
            raise HTTPException(422,'月让利须低于挂牌月租')
        start=expiry+timedelta(days=1)
        budget=conn.execute('SELECT id FROM retention_budget WHERE neighborhood=%s AND starts_month=%s',
                            (unit['neighborhood'],start.replace(day=1))).fetchone()
        if not budget:
            raise HTTPException(409,'先由分析员建立相应片区和启租月的预算')
        try:
            row=conn.execute('''INSERT INTO renewal_offer(task_id,tenant_id,lease_end,budget_id,ref,term_months,lease_start,
                proposed_end,list_cents,monthly_discount_cents,valid_through,rationale,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
                (task['id'],tenant['id'],expiry,budget['id'],payload.ref,payload.term_months,start,lease_end(start,payload.term_months),
                 rent,payload.monthly_discount_cents,payload.valid_through,payload.rationale,user['id'])).fetchone()
        except UniqueViolation as exc:
            raise HTTPException(409,'本租期已有有效报价，或报价编号已使用') from exc
        audit(conn,user,'renewal_offer_drafted','renewal_offer',row['id'],payload.rationale)
    return row


def locked(conn,offer_id):
    ref=get(conn,'SELECT task_id FROM renewal_offer WHERE id=%s',(offer_id,),'续租报价不存在')
    lock_context(conn,ref['task_id'],must_be_open=True)
    return get(conn,'SELECT * FROM renewal_offer WHERE id=%s FOR UPDATE',(offer_id,),'续租报价不存在')


def transition(offer_id,payload,user):
    with connect() as conn:
        row=locked(conn,offer_id)
        status=row['status']
        if payload.decision=='issue':
            if status!='draft' or row['valid_through']<today():
                raise HTTPException(409,'只能审批尚未过期的报价草稿')
            if conn.execute("SELECT 1 FROM checkout_appointment WHERE tenant_id=%s AND lease_end=%s AND status<>'cancelled'",
                            (row['tenant_id'],row['lease_end'])).fetchone():
                raise HTTPException(409,'有进行中退租交接，暂停报价')
            budget=get(conn,'SELECT cap_cents FROM retention_budget WHERE id=%s FOR UPDATE',(row['budget_id'],),'片区让利预算不存在')
            if committed(conn,row['budget_id'])+row['total_discount_cents']>budget['cap_cents']:
                raise HTTPException(409,'片区预算不足，报价未发出')
            next_status='issued'
        elif payload.decision=='decline' and status=='issued':
            next_status='declined'
        elif payload.decision=='withdraw' and status in {'draft','issued'}:
            next_status='withdrawn'
        else:
            raise HTTPException(409,'报价当前不可执行该动作')
        out=conn.execute('''UPDATE renewal_offer SET status=%s,closing_note=%s,acted_at=now(),
            issued_by=CASE WHEN %s='issued' THEN %s ELSE issued_by END WHERE id=%s RETURNING *''',
            (next_status,payload.note,next_status,user['id'],offer_id)).fetchone()
        audit(conn,user,'renewal_offer_'+next_status,'renewal_offer',offer_id,payload.note)
    return out
