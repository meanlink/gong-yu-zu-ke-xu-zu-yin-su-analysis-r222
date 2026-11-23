from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user, require_roles
from . import budgets, offers
from .offer_schemas import BudgetIn, OfferAction, OfferIn

router = APIRouter(prefix='/lease-desk',tags=['续租预算与报价'])
analyst = require_roles('analyst')
manager = require_roles('customer_manager')


@router.get('/budgets')
def budget_board(_user=Depends(current_user)):
    return budgets.board()


@router.put('/budgets')
def configure(payload:BudgetIn,user=Depends(analyst)):
    return budgets.configure(payload,user)


@router.get('/offers')
def offer_board(_user=Depends(current_user)):
    return offers.board()


@router.post('/offers',status_code=201)
def draft(payload:OfferIn,user=Depends(manager)):
    return offers.create(payload,user)


@router.post('/offers/{offer_id}/transition')
def transition(offer_id:int,payload:OfferAction,user=Depends(current_user)):
    required = 'analyst' if payload.decision=='issue' else 'customer_manager'
    if user['role']!=required:
        raise HTTPException(403,'当前岗位不能执行该报价动作')
    return offers.transition(offer_id,payload,user)
