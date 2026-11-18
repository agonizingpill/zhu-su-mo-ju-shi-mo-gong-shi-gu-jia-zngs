from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select
from .models import Estimate,Mould
from .execution_models import TrialExecution,CostReview
from .services import item,serialize,record
from .workshop_service import trial_ready,material_cost,freeze_material_cost
from .workshop_models import ReviewMaterialLedger
SHANGHAI=ZoneInfo('Asia/Shanghai')
def stamp(value):
    return (value.replace(tzinfo=SHANGHAI)if value.tzinfo is None else value).astimezone(timezone.utc)
def view(s,x):
    d=serialize(x)
    if isinstance(x,TrialExecution):
        d['estimate_code']=x.snapshot['estimate_code'];d['net_material_cost']=material_cost(s,x.id)[0]
    else:
        e=item(s,TrialExecution,x.execution_id);d['estimate_code']=e.snapshot['estimate_code'];d['requires_explanation']=abs(x.variance_pct)>20 or x.margin<0
        ledger=s.scalar(select(ReviewMaterialLedger).where(ReviewMaterialLedger.review_id==x.id));d['material_ledger']=serialize(ledger) if ledger else None
    return d
def begin(s,data,u):
    e=s.query(Estimate).filter_by(id=data.estimate_id).with_for_update().one_or_none()
    if not e:raise HTTPException(404,'估单不存在')
    if e.status!='committed' or not e.predicted_hours or not e.slot_id:raise HTTPException(409,'仅已承诺机时的估单可开工')
    if s.scalar(select(TrialExecution.id).where(TrialExecution.estimate_id==e.id)):raise HTTPException(409,'该估单已经开工，不可重复建立实绩')
    trial_ready(s,e,stamp(data.started_at))
    m=item(s,Mould,e.mould_id)
    x=TrialExecution(estimate_id=e.id,started_at=stamp(data.started_at).isoformat(),snapshot={'estimate_code':e.code,'predicted_hours':e.predicted_hours,'quoted_amount':e.quote_amount,'rate':e.rate,'mould_code':m.code,'slot_id':e.slot_id},status='running')
    s.add(x);record(s,u,'试模开工 '+e.code);s.flush();return x
def finish(s,eid,data,u):
    x=s.query(TrialExecution).filter_by(id=eid).with_for_update().one_or_none()
    if not x:raise HTTPException(404,'实绩记录不存在')
    if x.status!='running':raise HTTPException(409,'已完工或已结算实绩已冻结')
    hours=(stamp(data.ended_at)-datetime.fromisoformat(x.started_at)).total_seconds()/3600
    if hours<=0 or hours>168:raise HTTPException(409,'完工须晚于开工，且单次试模不超过168小时')
    if data.good_shots>data.total_shots:raise HTTPException(409,'良品射次不得大于总射次')
    if hours>x.snapshot['predicted_hours']:
        if u.role!='admin':raise HTTPException(403,'超出已承诺机时，须车间负责人确认完工')
        if len(data.overtime_reason.strip())<8:raise HTTPException(409,'超时试模须填写至少8字的原因')
    x.ended_at=stamp(data.ended_at).isoformat();x.actual_hours=round(hours,4);x.good_shots=data.good_shots;x.total_shots=data.total_shots;x.overtime_reason=data.overtime_reason.strip();x.status='completed'
    record(s,u,'试模完工 '+x.snapshot['estimate_code']);return x
def amounts(x,material):
    actual=round(x.actual_hours*x.snapshot['rate']+material,2);quoted=x.snapshot['quoted_amount'];delta=round(x.actual_hours-x.snapshot['predicted_hours'],4)
    return dict(material_cost=material,actual_cost=actual,quoted_amount=quoted,variance_hours=delta,variance_pct=round(delta/x.snapshot['predicted_hours']*100,3),margin=round(quoted-actual,2))
def prepare_review(s,data,u):
    x=s.query(TrialExecution).filter_by(id=data.execution_id).with_for_update().one_or_none()
    if not x:raise HTTPException(404,'实绩不存在')
    if x.status!='completed':raise HTTPException(409,'须先完工，已结算实绩不可重复结算')
    if s.scalar(select(CostReview.id).where(CostReview.execution_id==x.id)):raise HTTPException(409,'该实绩已有结算复核，请修订已有草稿')
    derived,_=material_cost(s,x.id)
    if abs(data.material_cost-derived)>.005:raise HTTPException(409,'材料成本须等于领退料净耗台账，不能手工覆盖')
    v=CostReview(execution_id=x.id,**amounts(x,derived),reason=data.reason.strip(),status='draft');s.add(v);record(s,u,'生成偏差结算 '+x.snapshot['estimate_code']);s.flush();freeze_material_cost(s,v);return v
def revise(s,rid,data,u):
    r=s.query(CostReview).filter_by(id=rid).with_for_update().one_or_none()
    if not r:raise HTTPException(404,'结算不存在')
    if r.status!='draft':raise HTTPException(409,'已签结算不可修改')
    x=item(s,TrialExecution,r.execution_id)
    derived,_=material_cost(s,x.id)
    if abs(data.material_cost-derived)>.005:raise HTTPException(409,'材料成本由净耗台账计算，不可覆盖')
    for k,v in amounts(x,derived).items():setattr(r,k,v)
    r.reason=data.reason.strip();record(s,u,'修订偏差说明 '+x.snapshot['estimate_code']);return r
def sign(s,rid,u):
    r=s.query(CostReview).filter_by(id=rid).with_for_update().one_or_none()
    if not r:raise HTTPException(404,'结算不存在')
    if r.status!='draft':raise HTTPException(409,'结算已签结，不得重复签结')
    x=s.query(TrialExecution).filter_by(id=r.execution_id).with_for_update().one()
    if x.status!='completed':raise HTTPException(409,'关联实绩不是已完工状态')
    derived,_=material_cost(s,x.id)
    for key,value in amounts(x,derived).items():setattr(r,key,value)
    freeze_material_cost(s,r)
    if (abs(r.variance_pct)>20 or r.margin<0)and len(r.reason.strip())<8:raise HTTPException(409,'工时偏差超过20%或负毛利，须填写至少8字的复核说明')
    r.status='signed';r.signed_by=u.email;x.status='settled';record(s,u,'主管签结 '+x.snapshot['estimate_code']);return r
