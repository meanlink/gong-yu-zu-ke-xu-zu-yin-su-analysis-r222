from fastapi import APIRouter, Depends

from ..auth import current_user, require_roles
from . import billing
from .billing_schemas import ContractIn, InvoiceIn

router = APIRouter(prefix='/lease-desk/contracts',tags=['签约及首账单'])
coordinator = require_roles('service_coordinator')
analyst = require_roles('analyst')


@router.get('')
def board(_user=Depends(current_user)):
    return billing.board()


@router.post('/{offer_id}',status_code=201)
def record(offer_id:int,payload:ContractIn,user=Depends(coordinator)):
    return billing.sign(offer_id,payload,user)


@router.post('/{offer_id}/invoices',status_code=201)
def check(offer_id:int,payload:InvoiceIn,user=Depends(analyst)):
    return billing.check_invoice(offer_id,payload,user)
