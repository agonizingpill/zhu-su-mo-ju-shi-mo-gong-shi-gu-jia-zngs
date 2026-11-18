from sqlalchemy import String, Float, Integer, ForeignKey, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(String(120),unique=True)
    password_hash: Mapped[str]=mapped_column(String(180))
    role: Mapped[str]=mapped_column(String(20))
class Mould(Base):
    __tablename__='moulds'
    __table_args__=(CheckConstraint('cavities > 0 AND slides >= 0 AND weight_kg > 0'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    code: Mapped[str]=mapped_column(String(40),unique=True)
    name: Mapped[str]=mapped_column(String(120))
    cavities: Mapped[int]=mapped_column(Integer)
    slides: Mapped[int]=mapped_column(Integer)
    steel: Mapped[str]=mapped_column(String(20))
    weight_kg: Mapped[float]=mapped_column(Float)
class MachineSlot(Base):
    __tablename__='machine_slots'
    __table_args__=(UniqueConstraint('machine','start_hour'),CheckConstraint('capacity_hours > 0 AND reserved_hours >= 0 AND reserved_hours <= capacity_hours'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    machine: Mapped[str]=mapped_column(String(40))
    start_hour: Mapped[str]=mapped_column(String(40))
    capacity_hours: Mapped[float]=mapped_column(Float)
    reserved_hours: Mapped[float]=mapped_column(Float,default=0)
class Estimate(Base):
    __tablename__='estimates'
    __table_args__=(CheckConstraint('rate > 0 AND setup_hours >= 0 AND quote_amount >= 0'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    code: Mapped[str]=mapped_column(String(40),unique=True)
    mould_id: Mapped[int]=mapped_column(ForeignKey('moulds.id'))
    slot_id: Mapped[int|None]=mapped_column(ForeignKey('machine_slots.id'),nullable=True)
    rate: Mapped[float]=mapped_column(Float)
    setup_hours: Mapped[float]=mapped_column(Float)
    predicted_hours: Mapped[float|None]=mapped_column(Float,nullable=True)
    quote_amount: Mapped[float]=mapped_column(Float)
    status: Mapped[str]=mapped_column(String(20),default='draft')
    model_result: Mapped[dict|None]=mapped_column(JSON,nullable=True)
class TrialHistory(Base):
    __tablename__='trial_history'
    id: Mapped[int]=mapped_column(primary_key=True)
    trial_code: Mapped[str]=mapped_column(String(40),unique=True)
    cavities: Mapped[int]=mapped_column(Integer)
    slides: Mapped[int]=mapped_column(Integer)
    steel: Mapped[str]=mapped_column(String(20))
    weight_kg: Mapped[float]=mapped_column(Float)
    actual_hours: Mapped[float]=mapped_column(Float)
class Audit(Base):
    __tablename__='audits'
    id: Mapped[int]=mapped_column(primary_key=True)
    actor: Mapped[str]=mapped_column(String(120))
    action: Mapped[str]=mapped_column(String(200))
    stamp: Mapped[str]=mapped_column(String(40))
