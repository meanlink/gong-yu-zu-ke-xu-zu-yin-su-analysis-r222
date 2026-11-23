from fastapi import HTTPException

from ..db import connect
from ..resident_operations import audit
from .rules import today


USE = "(status='signed' OR (status='issued' AND valid_through >= %s))"


def committed(conn,budget_id):
    return conn.execute(f'SELECT coalesce(sum(total_discount_cents),0) used FROM renewal_offer WHERE budget_id=%s AND {USE}',
                        (budget_id,today())).fetchone()['used']


def board():
    with connect() as conn:
        rows = conn.execute('SELECT * FROM retention_budget ORDER BY starts_month DESC,neighborhood').fetchall()
        for row in rows:
            row['committed_cents'] = committed(conn,row['id'])
            row['remaining_cents'] = row['cap_cents']-row['committed_cents']
        districts = conn.execute('SELECT DISTINCT neighborhood FROM properties ORDER BY neighborhood').fetchall()
    return {'budgets':rows,'neighborhoods':[row['neighborhood'] for row in districts]}


def configure(payload,user):
    if payload.starts_month.day != 1:
        raise HTTPException(422,'预算月份必须填写当月第一日')
    with connect() as conn:
        if not conn.execute('SELECT 1 FROM properties WHERE neighborhood=%s LIMIT 1',(payload.neighborhood,)).fetchone():
            raise HTTPException(422,'片区不存在')
        conn.execute('''INSERT INTO retention_budget(neighborhood,starts_month,cap_cents,justification,configured_by)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(neighborhood,starts_month) DO NOTHING''',
            (payload.neighborhood,payload.starts_month,payload.cap_cents,payload.justification,user['id']))
        row=conn.execute('''SELECT id FROM retention_budget WHERE neighborhood=%s AND starts_month=%s FOR UPDATE''',
                         (payload.neighborhood,payload.starts_month)).fetchone()
        if committed(conn,row['id'])>payload.cap_cents:
            raise HTTPException(409,'新额度低于当前已承诺让利')
        conn.execute('UPDATE retention_budget SET cap_cents=%s,justification=%s,configured_by=%s WHERE id=%s',
                     (payload.cap_cents,payload.justification,user['id'],row['id']))
        audit(conn,user,'retention_budget_configured','retention_budget',row['id'],payload.justification)
    return {'id':row['id'],'cap_cents':payload.cap_cents}
