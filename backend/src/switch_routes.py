from fastapi import APIRouter, Depends
from sqlalchemy import select
from .db import db_session
from .auth import current, writers, admin
from .switch_models import MachineSwitchRequest
from .switch_schemas import SwitchRequestInput
from . import switch_service as svc

router = APIRouter()


@router.get('/machine-switches')
def list_switches(s=Depends(db_session), u=Depends(current)):
    rows = s.scalars(select(MachineSwitchRequest).order_by(MachineSwitchRequest.id.desc()))
    return [svc.view(s, x) for x in rows]


@router.post('/machine-switches')
def request_switch(p: SwitchRequestInput, s=Depends(db_session), u=Depends(writers)):
    req = svc.create_or_evaluate(s, p, u)
    s.commit()
    return svc.view(s, req)


@router.post('/machine-switches/{req_id}/approve')
def approve_switch(req_id: int, s=Depends(db_session), u=Depends(admin)):
    req = svc.approve(s, req_id, u)
    s.commit()
    return svc.view(s, req)
