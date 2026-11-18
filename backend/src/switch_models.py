"""Machine-switch evaluation for committed-but-not-started estimates.

The original regression estimate is preserved: this table only carries a
frozen snapshot of the original commitment and a separate, evidence-backed
opinion about moving the work to another machine. Nothing here mutates
Estimate.predicted_hours or the customer quote.
"""
from sqlalchemy import String, Float, Integer, ForeignKey, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class MachineSwitchRequest(Base):
    __tablename__ = 'machine_switch_requests'
    __table_args__ = (
        UniqueConstraint('estimate_id', name='uq_switch_estimate'),
        CheckConstraint('status in (\'pending\',\'rejected\',\'eligible\',\'switched\')'),
        CheckConstraint('conservative_hours IS NULL OR conservative_hours > 0'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey('estimates.id'))
    target_slot_id: Mapped[int] = mapped_column(ForeignKey('machine_slots.id'))

    # Frozen at request time: evaluations and approvals always read this snapshot,
    # never a later edited commitment.
    original_snapshot: Mapped[dict] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(20), default='pending')
    reject_reason: Mapped[str | None] = mapped_column(String(600), nullable=True)

    # Learning output (null while pending or when rejected for missing evidence).
    comparable_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    machine_sample_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    baseline_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_lower_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_upper_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    saving_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    saving_lower_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    saving_upper_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    conservative_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    quote_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
