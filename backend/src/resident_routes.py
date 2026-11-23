from fastapi import APIRouter, Depends

from . import resident_operations as operations
from .auth import current_user, require_roles
from .resident_inputs import CheckoutIn, InspectionIn, OutcomeIn, RemedyIn, ReviewNote

router = APIRouter(prefix='/resident-operations')
manager = require_roles('customer_manager')
service = require_roles('service_coordinator')
analyst = require_roles('analyst')


@router.get('/remedies')
def remedies(user=Depends(current_user)):
    return operations.list_remedies()


@router.post('/remedies', status_code=201)
def assign(payload: RemedyIn, user=Depends(manager)):
    return operations.assign_remedy(payload, user)


@router.post('/remedies/{record_id}/submit')
def submit_remedy(record_id: int, payload: ReviewNote, user=Depends(service)):
    return operations.update_remedy(record_id, 'submit', payload, user)


@router.post('/remedies/{record_id}/return')
def return_remedy(record_id: int, payload: ReviewNote, user=Depends(manager)):
    return operations.update_remedy(record_id, 'return', payload, user)


@router.post('/remedies/{record_id}/accept')
def accept_remedy(record_id: int, payload: ReviewNote, user=Depends(manager)):
    return operations.update_remedy(record_id, 'accept', payload, user)


@router.get('/checkouts')
def checkouts(user=Depends(current_user)):
    return operations.list_checkouts()


@router.post('/checkouts', status_code=201)
def schedule(payload: CheckoutIn, user=Depends(manager)):
    return operations.schedule_checkout(payload, user)


@router.post('/checkouts/{record_id}/cancel')
def cancel_checkout(record_id: int, payload: ReviewNote, user=Depends(manager)):
    return operations.update_checkout(record_id, 'cancel', payload, user)


@router.post('/checkouts/{record_id}/complete')
def complete_checkout(record_id: int, payload: InspectionIn, user=Depends(service)):
    return operations.update_checkout(record_id, 'complete', payload, user)


@router.get('/outcomes')
def results(user=Depends(current_user)):
    return operations.list_results()


@router.post('/outcomes')
def submit_result(payload: OutcomeIn, user=Depends(manager)):
    return operations.submit_result(payload, user)


@router.post('/outcomes/{record_id}/return')
def return_result(record_id: int, payload: ReviewNote, user=Depends(analyst)):
    return operations.review_result(record_id, 'return', payload, user)


@router.post('/outcomes/{record_id}/confirm')
def confirm_result(record_id: int, payload: ReviewNote, user=Depends(analyst)):
    return operations.review_result(record_id, 'confirm', payload, user)
