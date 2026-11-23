from fastapi import HTTPException
from psycopg.errors import UniqueViolation

from ..db import connect
from ..resident_operations import audit, get
from .offers import BASE, locked
from .rules import LOCAL, first_invoice, today


def board():
    with connect() as conn:
        opts=conn.execute(BASE+" WHERE o.status IN ('issued','signed') ORDER BY o.id DESC").fetchall()
        contracts={row['offer_id']:row for row in conn.execute('SELECT * FROM renewal_contract').fetchall()}
        invoices={}
        for row in conn.execute('SELECT * FROM renewal_invoice_check ORDER BY checked_at DESC,id DESC').fetchall():
            invoices.setdefault(row['offer_id'],[]).append(row)
        for row in opts:
            row['contract']=contracts.get(row['id'])
            row['invoices']=invoices.get(row['id'],[])
    return {'offers':opts,'today':today()}


def sign(offer_id,payload,user):
    with connect() as conn:
        offer=locked(conn,offer_id)
        if offer['status']!='issued':
            raise HTTPException(409,'只有已发出且未签约报价可以登记合同')
        issued_day=(offer['acted_at'] or offer['created_at']).astimezone(LOCAL).date()
        if not (issued_day<=payload.signed_on<=min(today(),offer['valid_through'])):
            raise HTTPException(422,'签约日期须在报价发出至有效期之间且不能是未来')
        if offer['valid_through']<today():
            raise HTTPException(409,'预算预留已释放，请重新发出报价并登记合同')
        period,expected=first_invoice(offer['lease_start'],offer['list_cents']-offer['monthly_discount_cents'])
        try:
            row=conn.execute('''INSERT INTO renewal_contract(offer_id,contract_ref,signed_on,recorded_by,first_period_end,first_expected_cents)
                VALUES(%s,%s,%s,%s,%s,%s) RETURNING *''',(offer_id,payload.contract_ref,payload.signed_on,user['id'],period,expected)).fetchone()
        except UniqueViolation as exc:
            raise HTTPException(409,'合同凭证已用于其他报价') from exc
        conn.execute("UPDATE renewal_offer SET status='signed',acted_at=now() WHERE id=%s",(offer_id,))
        audit(conn,user,'renewal_contract_recorded','renewal_offer',offer_id,payload.contract_ref)
    return row


def check_invoice(offer_id,payload,user):
    with connect() as conn:
        offer=locked(conn,offer_id)
        if offer['status']!='signed':
            raise HTTPException(409,'先登记签约凭证再核对首张账单')
        contract=get(conn,'SELECT * FROM renewal_contract WHERE offer_id=%s',(offer_id,),'续租合同不存在')
        if conn.execute("SELECT 1 FROM renewal_invoice_check WHERE offer_id=%s AND status='matched'",(offer_id,)).fetchone():
            raise HTTPException(409,'首账单已核对')
        try:
            row=conn.execute('''INSERT INTO renewal_invoice_check(offer_id,invoice_ref,invoiced_cents,expected_cents,note,checked_by)
                VALUES(%s,%s,%s,%s,%s,%s) RETURNING *''',
                (offer_id,payload.invoice_ref,payload.invoiced_cents,contract['first_expected_cents'],payload.note,user['id'])).fetchone()
        except UniqueViolation as exc:
            raise HTTPException(409,'账单号已登记') from exc
        audit(conn,user,'renewal_first_invoice_checked','renewal_offer',offer_id,payload.invoice_ref+' '+row['status'])
    return row
