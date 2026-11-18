from pydantic import BaseModel, Field


class SwitchRequestInput(BaseModel):
    estimate_id: int
    target_slot_id: int
