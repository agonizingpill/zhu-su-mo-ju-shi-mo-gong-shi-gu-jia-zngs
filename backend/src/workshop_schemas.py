from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
class Clean(BaseModel):model_config=ConfigDict(str_strip_whitespace=True)
class WindowInput(Clean):
    mould_id:int=Field(gt=0)
    starts_at:datetime
    ends_at:datetime
    reason:str=Field(min_length=8,max_length=600)
class Inspection(Clean):inspection_note:str=Field(min_length=8,max_length=600)
class ResinInput(Clean):
    code:str=Field(min_length=2,max_length=60)
    grade:str=Field(min_length=2,max_length=60)
    received_kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
    unit_price:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=2)
class ResinState(Clean):state:Literal['available','quarantine']
class MaterialIssue(Clean):
    execution_id:int=Field(gt=0)
    lot_id:int=Field(gt=0)
    issued_kg:Decimal=Field(gt=0,le=100000,max_digits=12,decimal_places=3)
class MaterialReturn(Clean):
    returned_kg:Decimal=Field(ge=0,le=100000,max_digits=12,decimal_places=3)
    return_note:str=Field(min_length=8,max_length=600)
class DeliveryInput(Clean):
    review_id:int=Field(gt=0)
    good_samples:int=Field(gt=0,le=1000000)
    tracking:str=Field(min_length=4,max_length=120)
class ReceiptInput(Clean):received_by:str=Field(min_length=2,max_length=120)
class CustomerDecision(Clean):
    decision:Literal['accepted','rectification']
    customer_note:str=Field(min_length=8,max_length=600)
class CloseDelivery(Clean):correction_review_id:int|None=Field(default=None,gt=0)
