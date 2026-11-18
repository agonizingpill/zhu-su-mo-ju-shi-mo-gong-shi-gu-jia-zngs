from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException
from .models import Estimate, Mould, MachineSlot, Audit
from .constants import ESTIMATE_STATES

def record(s,u,action): s.add(Audit(actor=u.email,action=action,stamp=datetime.now(timezone.utc).isoformat()))
def item(s,model,id):
    v=s.get(model,id)
    if v is None: raise HTTPException(404,'记录不存在')
    return v
def serialize(v): return {c.name:float(getattr(v,c.name)) if isinstance(getattr(v,c.name),Decimal) else getattr(v,c.name) for c in v.__table__.columns}
def require_edit(e):
    if e.status in ('committed','calculating'): raise HTTPException(409,'已承诺或计算中的估价不能修改')
def request_capacity(s,e,slot_id):
    if e.status!='estimated': raise HTTPException(409,'请先完成工时估算')
    slot=item(s,MachineSlot,slot_id)
    if e.predicted_hours>slot.capacity_hours-slot.reserved_hours+1e-6: raise HTTPException(409,'机时余量不足，请选择其他时段')
    e.slot_id=slot.id; e.status='requested'
def commit_capacity(s,eid):
    e=s.query(Estimate).filter_by(id=eid).with_for_update().one_or_none()
    if not e: raise HTTPException(404,'估价不存在')
    if e.status!='requested': raise HTTPException(409,'只有已申请机时的估价可承诺')
    floor=round(e.predicted_hours*e.rate*1.15,2)
    if e.quote_amount<floor: raise HTTPException(409,f'报价低于成本底线 {floor:.2f} 元，请修订报价后重新申请')
    slot=s.query(MachineSlot).filter_by(id=e.slot_id).with_for_update().one()
    if e.predicted_hours>slot.capacity_hours-slot.reserved_hours+1e-6: raise HTTPException(409,'机时已被其他承诺占用，不能超售')
    slot.reserved_hours=round(slot.reserved_hours+e.predicted_hours,2)
    e.status='committed'
    return e
