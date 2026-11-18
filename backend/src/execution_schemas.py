from datetime import datetime
from pydantic import BaseModel,Field
class StartTrial(BaseModel):
    estimate_id:int
    started_at:datetime
class FinishTrial(BaseModel):
    ended_at:datetime
    good_shots:int=Field(ge=0,le=1000000)
    total_shots:int=Field(gt=0,le=1000000)
    overtime_reason:str=Field(default='',max_length=600)
class ReviewInput(BaseModel):
    execution_id:int
    material_cost:float=Field(ge=0,le=10000000)
    reason:str=Field(default='',max_length=600)
class ReviseReview(BaseModel):
    material_cost:float=Field(ge=0,le=10000000)
    reason:str=Field(default='',max_length=600)
