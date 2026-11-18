from fastapi import APIRouter,Depends
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .execution_models import TrialExecution,CostReview
from .execution_schemas import StartTrial,FinishTrial,ReviewInput,ReviseReview
from . import execution_service as svc
router=APIRouter()
@router.get('/executions')
def executions(s=Depends(db_session),u=Depends(current)):return [svc.view(s,x)for x in s.scalars(select(TrialExecution).order_by(TrialExecution.id.desc()))]
@router.post('/executions')
def start(p:StartTrial,s=Depends(db_session),u=Depends(writers)):
    x=svc.begin(s,p,u);s.commit();return svc.view(s,x)
@router.post('/executions/{eid}/finish')
def finish(eid:int,p:FinishTrial,s=Depends(db_session),u=Depends(writers)):
    x=svc.finish(s,eid,p,u);s.commit();return svc.view(s,x)
@router.get('/cost-reviews')
def reviews(s=Depends(db_session),u=Depends(current)):return [svc.view(s,x)for x in s.scalars(select(CostReview).order_by(CostReview.id.desc()))]
@router.post('/cost-reviews')
def prepare(p:ReviewInput,s=Depends(db_session),u=Depends(writers)):
    x=svc.prepare_review(s,p,u);s.commit();return svc.view(s,x)
@router.patch('/cost-reviews/{rid}')
def revise(rid:int,p:ReviseReview,s=Depends(db_session),u=Depends(writers)):
    x=svc.revise(s,rid,p,u);s.commit();return svc.view(s,x)
@router.post('/cost-reviews/{rid}/sign')
def sign(rid:int,s=Depends(db_session),u=Depends(admin)):
    x=svc.sign(s,rid,u);s.commit();return svc.view(s,x)
