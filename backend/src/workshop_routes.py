from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .services import serialize,record
from .workshop_models import MaintenanceWindow,ResinLot,TrialMaterial,TrialDelivery
from .workshop_schemas import WindowInput,Inspection,ResinInput,ResinState,MaterialIssue,MaterialReturn,DeliveryInput,ReceiptInput,CustomerDecision,CloseDelivery
from . import workshop_service as svc
router=APIRouter()
@router.get('/maintenance-windows')
def windows(s=Depends(db_session),u=Depends(current)):return [svc.view(s,x)for x in s.scalars(select(MaintenanceWindow).order_by(MaintenanceWindow.id.desc()))]
@router.post('/maintenance-windows')
def create_window(p:WindowInput,s=Depends(db_session),u=Depends(writers)):
    x=svc.create_window(s,p,u);s.commit();return x
@router.post('/maintenance-windows/{id}/approve')
def approve(id:int,s=Depends(db_session),u=Depends(admin)):
    x=svc.approve_window(s,id,u);s.commit();return x
@router.post('/maintenance-windows/{id}/complete')
def complete(id:int,p:Inspection,s=Depends(db_session),u=Depends(writers)):
    x=svc.finish_window(s,id,p,u);s.commit();return x
@router.get('/resin-lots')
def lots(s=Depends(db_session),u=Depends(current)):return [serialize(x)for x in s.scalars(select(ResinLot).order_by(ResinLot.id.desc()))]
@router.post('/resin-lots')
def create_lot(p:ResinInput,s=Depends(db_session),u=Depends(admin)):
    x=ResinLot(**p.model_dump(),available_kg=p.received_kg,state='available');s.add(x);s.flush();record(s,u,'树脂批次入库 '+x.code);s.commit();return serialize(x)
@router.patch('/resin-lots/{id}/state')
def lot_state(id:int,p:ResinState,s=Depends(db_session),u=Depends(admin)):
    x=svc.locked(s,ResinLot,id)
    if x.state==p.state:raise HTTPException(409,'树脂批次已为该状态')
    x.state=p.state;record(s,u,'树脂隔离状态 '+x.code);s.commit();return serialize(x)
@router.get('/trial-materials')
def materials(s=Depends(db_session),u=Depends(current)):return [svc.view(s,x)for x in s.scalars(select(TrialMaterial).order_by(TrialMaterial.id.desc()))]
@router.post('/trial-materials')
def issue(p:MaterialIssue,s=Depends(db_session),u=Depends(writers)):
    x=svc.issue(s,p,u);s.commit();return x
@router.post('/trial-materials/{id}/return')
def return_material(id:int,p:MaterialReturn,s=Depends(db_session),u=Depends(writers)):
    x=svc.return_material(s,id,p,u);s.commit();return x
@router.get('/trial-deliveries')
def deliveries(s=Depends(db_session),u=Depends(current)):return [svc.view(s,x)for x in s.scalars(select(TrialDelivery).order_by(TrialDelivery.id.desc()))]
@router.post('/trial-deliveries')
def deliver(p:DeliveryInput,s=Depends(db_session),u=Depends(writers)):
    x=svc.deliver(s,p,u);s.commit();return x
@router.post('/trial-deliveries/{id}/receive')
def receive(id:int,p:ReceiptInput,s=Depends(db_session),u=Depends(writers)):
    x=svc.receive_delivery(s,id,p,u);s.commit();return x
@router.post('/trial-deliveries/{id}/decision')
def decision(id:int,p:CustomerDecision,s=Depends(db_session),u=Depends(writers)):
    x=svc.decide_delivery(s,id,p,u);s.commit();return x
@router.post('/trial-deliveries/{id}/close')
def close(id:int,p:CloseDelivery,s=Depends(db_session),u=Depends(admin)):
    x=svc.close_delivery(s,id,p,u);s.commit();return x
