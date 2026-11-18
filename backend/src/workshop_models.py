"""Maintenance, consumables and customer acceptance are separate workshop obligations."""
from decimal import Decimal
from sqlalchemy import String,Integer,ForeignKey,JSON,CheckConstraint,Numeric,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class MaintenanceWindow(Base):
    __tablename__='maintenance_windows'
    id:Mapped[int]=mapped_column(primary_key=True)
    mould_id:Mapped[int]=mapped_column(ForeignKey('moulds.id'))
    starts_at:Mapped[str]=mapped_column(String(40))
    ends_at:Mapped[str]=mapped_column(String(40))
    reason:Mapped[str]=mapped_column(String(600))
    state:Mapped[str]=mapped_column(String(20),default='planned')
    approved_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    inspection_note:Mapped[str]=mapped_column(String(600),default='')
class ResinLot(Base):
    __tablename__='resin_lots'
    __table_args__=(CheckConstraint('received_kg > 0 AND available_kg >= 0 AND available_kg <= received_kg AND unit_price > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True)
    grade:Mapped[str]=mapped_column(String(60))
    received_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    available_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    unit_price:Mapped[Decimal]=mapped_column(Numeric(12,2))
    state:Mapped[str]=mapped_column(String(20),default='available')
class TrialMaterial(Base):
    __tablename__='trial_materials'
    __table_args__=(UniqueConstraint('execution_id','lot_id'),CheckConstraint('issued_kg > 0 AND returned_kg >= 0 AND returned_kg <= issued_kg AND unit_price_snapshot > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    execution_id:Mapped[int]=mapped_column(ForeignKey('trial_executions.id'))
    lot_id:Mapped[int]=mapped_column(ForeignKey('resin_lots.id'))
    issued_kg:Mapped[Decimal]=mapped_column(Numeric(12,3))
    returned_kg:Mapped[Decimal]=mapped_column(Numeric(12,3),default=0)
    unit_price_snapshot:Mapped[Decimal]=mapped_column(Numeric(12,2))
    state:Mapped[str]=mapped_column(String(20),default='issued')
    return_note:Mapped[str]=mapped_column(String(600),default='')
class ReviewMaterialLedger(Base):
    __tablename__='review_material_ledgers'
    id:Mapped[int]=mapped_column(primary_key=True)
    review_id:Mapped[int]=mapped_column(ForeignKey('cost_reviews.id'),unique=True)
    net_cost:Mapped[Decimal]=mapped_column(Numeric(14,2))
    lines:Mapped[list]=mapped_column(JSON)
class TrialDelivery(Base):
    __tablename__='trial_deliveries'
    __table_args__=(CheckConstraint('good_samples > 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    review_id:Mapped[int]=mapped_column(ForeignKey('cost_reviews.id'),unique=True)
    good_samples:Mapped[int]=mapped_column(Integer)
    tracking:Mapped[str]=mapped_column(String(120),unique=True)
    state:Mapped[str]=mapped_column(String(20),default='dispatched')
    snapshot:Mapped[dict]=mapped_column(JSON)
    received_by:Mapped[str]=mapped_column(String(120),default='')
    customer_note:Mapped[str]=mapped_column(String(600),default='')
    correction_review_id:Mapped[int|None]=mapped_column(ForeignKey('cost_reviews.id'),nullable=True)
    closed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
