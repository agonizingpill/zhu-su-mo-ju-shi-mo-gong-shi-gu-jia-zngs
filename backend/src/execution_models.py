"""Shop-floor actuals are immutable once completed; commercial snapshots survive later edits."""
from sqlalchemy import String,Float,Integer,ForeignKey,JSON,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class TrialExecution(Base):
    __tablename__='trial_executions'
    __table_args__=(CheckConstraint('actual_hours IS NULL OR actual_hours > 0'),CheckConstraint('good_shots >= 0 AND total_shots >= good_shots'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    estimate_id:Mapped[int]=mapped_column(ForeignKey('estimates.id'),unique=True)
    started_at:Mapped[str]=mapped_column(String(40))
    ended_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    actual_hours:Mapped[float|None]=mapped_column(Float,nullable=True)
    good_shots:Mapped[int]=mapped_column(Integer,default=0)
    total_shots:Mapped[int]=mapped_column(Integer,default=0)
    overtime_reason:Mapped[str]=mapped_column(String(600),default='')
    snapshot:Mapped[dict]=mapped_column(JSON)
    status:Mapped[str]=mapped_column(String(20),default='running')
class CostReview(Base):
    __tablename__='cost_reviews'
    __table_args__=(CheckConstraint('material_cost >= 0 AND actual_cost >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    execution_id:Mapped[int]=mapped_column(ForeignKey('trial_executions.id'),unique=True)
    material_cost:Mapped[float]=mapped_column(Float)
    actual_cost:Mapped[float]=mapped_column(Float)
    quoted_amount:Mapped[float]=mapped_column(Float)
    variance_hours:Mapped[float]=mapped_column(Float)
    variance_pct:Mapped[float]=mapped_column(Float)
    margin:Mapped[float]=mapped_column(Float)
    reason:Mapped[str]=mapped_column(String(600),default='')
    status:Mapped[str]=mapped_column(String(20),default='draft')
    signed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
