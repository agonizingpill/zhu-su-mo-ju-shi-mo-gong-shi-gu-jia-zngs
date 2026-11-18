from datetime import datetime,timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from .models import Mould,Estimate
from .execution_models import TrialExecution,CostReview
from .workshop_models import MaintenanceWindow,ResinLot,TrialMaterial,ReviewMaterialLedger,TrialDelivery
from .services import item,serialize,record

def stamp(value):
    from .execution_service import stamp as convert
    return convert(value)
def view(s,x):
    d=serialize(x)
    if isinstance(x,MaintenanceWindow):d['mould_code']=item(s,Mould,x.mould_id).code
    if isinstance(x,TrialMaterial):
        e=item(s,TrialExecution,x.execution_id);d.update(estimate_code=e.snapshot['estimate_code'],lot_code=item(s,ResinLot,x.lot_id).code,net_kg=float(x.issued_kg-x.returned_kg),net_cost=float(((x.issued_kg-x.returned_kg)*x.unit_price_snapshot).quantize(Decimal('.01'))))
    if isinstance(x,TrialDelivery):d['estimate_code']=x.snapshot['estimate_code']
    return d
def locked(s,model,id):
    x=s.scalar(select(model).where(model.id==id).with_for_update().execution_options(populate_existing=True))
    if not x:raise HTTPException(404,'关联记录不存在')
    return x
def create_window(s,p,u):
    item(s,Mould,p.mould_id);start,end=stamp(p.starts_at),stamp(p.ends_at)
    if end<=start:raise HTTPException(409,'保养结束必须晚于开始')
    x=MaintenanceWindow(mould_id=p.mould_id,starts_at=start.isoformat(),ends_at=end.isoformat(),reason=p.reason,state='planned');s.add(x);s.flush();record(s,u,'登记保养窗口 '+str(x.id));return view(s,x)
def approve_window(s,id,u):
    # Lock the mould first, same order as beginning a trial, so approvals cannot race starts.
    candidate=item(s,MaintenanceWindow,id);locked(s,Mould,candidate.mould_id);x=locked(s,MaintenanceWindow,id)
    if x.state!='planned':raise HTTPException(409,'只可批准计划保养，不得重复批准')
    others=s.scalars(select(MaintenanceWindow).where(MaintenanceWindow.mould_id==x.mould_id,MaintenanceWindow.state.in_(['approved','completed']),MaintenanceWindow.id!=x.id))
    if any(datetime.fromisoformat(y.starts_at)<datetime.fromisoformat(x.ends_at) and datetime.fromisoformat(y.ends_at)>datetime.fromisoformat(x.starts_at) for y in others):raise HTTPException(409,'该模具已有重叠批准停机窗口')
    for execution in s.scalars(select(TrialExecution).join(Estimate,TrialExecution.estimate_id==Estimate.id).where(Estimate.mould_id==x.mould_id,TrialExecution.status=='running')):
        if datetime.fromisoformat(execution.started_at)<datetime.fromisoformat(x.ends_at):raise HTTPException(409,'模具有未完工实绩，不能批准与其可能重叠的停机')
    x.state='approved';x.approved_by=u.email;record(s,u,'批准停机保养 '+str(x.id));return view(s,x)
def finish_window(s,id,p,u):
    x=locked(s,MaintenanceWindow,id)
    if x.state!='approved':raise HTTPException(409,'仅已批准保养可记录完检，不可重复完成')
    x.inspection_note=p.inspection_note;x.state='completed';record(s,u,'保养完检 '+str(x.id));return view(s,x)
def trial_ready(s,e,started):
    locked(s,Mould,e.mould_id)
    if s.scalar(select(TrialExecution.id).join(Estimate,TrialExecution.estimate_id==Estimate.id).where(Estimate.mould_id==e.mould_id,TrialExecution.status=='running')):raise HTTPException(409,'同一模具有正在运行的试模，须先完工')
    for w in s.scalars(select(MaintenanceWindow).where(MaintenanceWindow.mould_id==e.mould_id,MaintenanceWindow.state.in_(['approved','completed']))):
        if datetime.fromisoformat(w.starts_at)<=started<datetime.fromisoformat(w.ends_at):raise HTTPException(409,'开工时间落在已批准模具保养停机窗口内')
def issue(s,p,u):
    x=locked(s,TrialExecution,p.execution_id)
    if x.status!='running':raise HTTPException(409,'只有运行中的试模可领材料')
    if s.scalar(select(TrialMaterial.id).where(TrialMaterial.execution_id==x.id,TrialMaterial.lot_id==p.lot_id)):raise HTTPException(409,'该试模已领此批材料，不可重复领料')
    lot=locked(s,ResinLot,p.lot_id)
    if lot.state!='available':raise HTTPException(409,'树脂批次已隔离，不能领料')
    if p.issued_kg>lot.available_kg:raise HTTPException(409,'树脂可用库存不足，领料未扣减')
    lot.available_kg-=p.issued_kg;m=TrialMaterial(execution_id=x.id,lot_id=lot.id,issued_kg=p.issued_kg,returned_kg=0,unit_price_snapshot=lot.unit_price,state='issued');s.add(m);s.flush();record(s,u,'试模领料 '+x.snapshot['estimate_code']);return view(s,m)
def return_material(s,id,p,u):
    candidate=item(s,TrialMaterial,id);x=locked(s,TrialExecution,candidate.execution_id);m=locked(s,TrialMaterial,id)
    if x.status!='completed':raise HTTPException(409,'仅已完工待结算实绩可退余料')
    if s.scalar(select(CostReview.id).where(CostReview.execution_id==x.id)):raise HTTPException(409,'结算已建立，领退料台账冻结')
    if m.state!='issued':raise HTTPException(409,'本笔领料已经退料，不可重复退库')
    if p.returned_kg>m.issued_kg:raise HTTPException(409,'退料不得超过本笔领料重量')
    lot=locked(s,ResinLot,m.lot_id);lot.available_kg+=p.returned_kg;m.returned_kg=p.returned_kg;m.return_note=p.return_note;m.state='returned';record(s,u,'试模余料退库 '+x.snapshot['estimate_code']);return view(s,m)
def material_cost(s,eid):
    rows=list(s.scalars(select(TrialMaterial).where(TrialMaterial.execution_id==eid).order_by(TrialMaterial.id)))
    lines=[view(s,m) for m in rows];cost=sum(((m.issued_kg-m.returned_kg)*m.unit_price_snapshot for m in rows),Decimal(0)).quantize(Decimal('.01'))
    return float(cost),lines
def freeze_material_cost(s,review):
    cost,lines=material_cost(s,review.execution_id)
    ledger=s.scalar(select(ReviewMaterialLedger).where(ReviewMaterialLedger.review_id==review.id))
    if ledger:return
    s.add(ReviewMaterialLedger(review_id=review.id,net_cost=cost,lines=lines))
def deliver(s,p,u):
    r=locked(s,CostReview,p.review_id)
    if r.status!='signed':raise HTTPException(409,'只有已签结算可交付试模样件')
    x=item(s,TrialExecution,r.execution_id);e=item(s,Estimate,x.estimate_id)
    if p.good_samples>x.good_shots:raise HTTPException(409,'交付样件不得超过实绩良品射次数')
    if s.scalar(select(TrialDelivery.id).where(TrialDelivery.review_id==r.id)):raise HTTPException(409,'该签结算已有交付，不可重复发样')
    snap={'review_id':r.id,'execution_id':x.id,'estimate_code':e.code,'mould_id':e.mould_id,'mould_code':x.snapshot['mould_code'],'good_shots':x.good_shots,'actual_hours':x.actual_hours,'material_cost':r.material_cost,'signed_by':r.signed_by,'ended_at':x.ended_at,'dispatched_at':datetime.now(timezone.utc).isoformat()}
    d=TrialDelivery(**p.model_dump(),snapshot=snap,state='dispatched');s.add(d);s.flush();record(s,u,'样件交付 '+e.code);return view(s,d)
def receive_delivery(s,id,p,u):
    d=locked(s,TrialDelivery,id)
    if d.state!='dispatched':raise HTTPException(409,'仅已发样可登记签收，不能重复签收')
    d.received_by=p.received_by;d.state='received';record(s,u,'登记客户签收 '+d.tracking);return view(s,d)
def decide_delivery(s,id,p,u):
    d=locked(s,TrialDelivery,id)
    if d.state!='received':raise HTTPException(409,'客户签收后才能登记接受或整改意见')
    d.state=p.decision;d.customer_note=p.customer_note;record(s,u,'登记客户验收 '+d.tracking);return view(s,d)
def close_delivery(s,id,p,u):
    d=locked(s,TrialDelivery,id)
    if d.state not in ('accepted','rectification'):raise HTTPException(409,'仅接受或待整改交付可由主管关闭，不能重复')
    if d.state=='rectification':
        if not p.correction_review_id:raise HTTPException(409,'整改须绑定新一次同模具已签结实绩')
        r=item(s,CostReview,p.correction_review_id);x=item(s,TrialExecution,r.execution_id);e=item(s,Estimate,x.estimate_id)
        if r.status!='signed' or x.id<=d.snapshot['execution_id'] or e.mould_id!=d.snapshot['mould_id'] or datetime.fromisoformat(x.started_at)<=datetime.fromisoformat(d.snapshot['ended_at']):raise HTTPException(409,'整改必须为原完工之后新执行、同模具且已签结的实绩')
        d.correction_review_id=r.id
    elif p.correction_review_id:raise HTTPException(409,'客户已接受，无须替换整改实绩')
    d.state='closed';d.closed_by=u.email;record(s,u,'主管关闭交付 '+d.tracking);return view(s,d)
