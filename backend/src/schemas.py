from pydantic import BaseModel, Field
from typing import Literal
class Login(BaseModel):
    email:str
    password:str
class MouldInput(BaseModel):
    code:str=Field(min_length=1,max_length=40)
    name:str=Field(min_length=1,max_length=120)
    cavities:int=Field(ge=1,le=64)
    slides:int=Field(ge=0,le=32)
    steel:Literal['P20','H13','S136']
    weight_kg:float=Field(gt=0,le=20000)
class EstimateInput(BaseModel):
    code:str=Field(min_length=1,max_length=40)
    mould_id:int
    rate:float=Field(gt=0,le=10000)
    setup_hours:float=Field(ge=0,le=48)
    quote_amount:float=Field(ge=0,le=10000000)
class QuoteInput(BaseModel):
    quote_amount:float=Field(ge=0,le=10000000)
class SlotChoice(BaseModel):
    slot_id:int
class SlotInput(BaseModel):
    machine:str=Field(min_length=1,max_length=40)
    start_hour:str=Field(min_length=1,max_length=40)
    capacity_hours:float=Field(gt=0,le=168)
