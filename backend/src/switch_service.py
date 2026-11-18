"""Commitment-preserving machine-switch workflow.

Evaluation only reads frozen snapshots and signed actuals. The original
regression hours, rate and quote on Estimate are never rewritten; the approved
migration moves reserved hours between slots atomically, and any failed check
leaves the original commitment untouched.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from .models import Estimate, Mould, MachineSlot
from .execution_models import TrialExecution
from .services import item, serialize, record
from .switch_models import MachineSwitchRequest
from .switch_learn import evaluate_switch


def _snapshot(s, e, slot, mould):
    return {
        'estimate_code': e.code,
        'mould_code': mould.code,
        'original_slot_id': slot.id,
        'original_machine': slot.machine,
        'original_start_hour': slot.start_hour,
        'committed_hours': e.predicted_hours,
        'rate': e.rate,
        'setup_hours': e.setup_hours,
        'quote_amount': e.quote_amount,
        'frozen_at': datetime.now(timezone.utc).isoformat(),
    }


def view(s, req):
    d = serialize(req)
    e = item(s, Estimate, req.estimate_id)
    mould = item(s, Mould, e.mould_id)
    target = item(s, MachineSlot, req.target_slot_id)
    original_slot_id = req.original_snapshot['original_slot_id']
    original = s.get(MachineSlot, original_slot_id)
    d.update(
        estimate_code=e.code,
        mould_code=mould.code,
        target_machine=target.machine,
        target_start_hour=target.start_hour,
        original_machine=req.original_snapshot['original_machine'],
        original_start_hour=req.original_snapshot['original_start_hour'],
        original_slot_id=original_slot_id,
        target_available_hours=round(target.capacity_hours - target.reserved_hours, 2),
        target_capacity_hours=target.capacity_hours,
        original_reserved_hours=original.reserved_hours if original else None,
        has_started=bool(s.scalar(select(TrialExecution.id).where(TrialExecution.estimate_id == e.id))),
    )
    return d


def create_or_evaluate(s, data, u):
    """Idempotent entry: retries resume/re-run in place and never add a new request."""
    e = s.query(Estimate).filter_by(id=data.estimate_id).with_for_update().one_or_none()
    if not e:
        raise HTTPException(404, '估单不存在')
    if e.status != 'committed' or not e.slot_id:
        raise HTTPException(409, '仅已承诺且未撤回的估单可评估换机')
    if s.scalar(select(TrialExecution.id).where(TrialExecution.estimate_id == e.id)):
        raise HTTPException(409, '估单已开工，保留原机台，不参与换机评估')

    original_slot = item(s, MachineSlot, e.slot_id)
    target_slot = s.get(MachineSlot, data.target_slot_id)
    if not target_slot:
        raise HTTPException(404, '目标时段不存在')
    if target_slot.id == original_slot.id:
        raise HTTPException(409, '目标时段与原承诺时段相同，无须换机')
    if target_slot.machine == original_slot.machine:
        raise HTTPException(409, '目标时段与原承诺在同一机台，换机评估须跨机台')

    mould = item(s, Mould, e.mould_id)
    existing = s.scalar(select(MachineSwitchRequest).where(MachineSwitchRequest.estimate_id == e.id).with_for_update())

    # A finished switch is immutable; a pending/rejected request is re-run in place
    # (interrupt-resumable), re-targeting is allowed and no second row is created.
    if existing and existing.status == 'switched':
        raise HTTPException(409, '该估单已完成换机，不可重复申请')

    status, reason, payload = evaluate_switch(s, mould, original_slot.machine, target_slot.machine)

    if existing is None:
        existing = MachineSwitchRequest(
            estimate_id=e.id, target_slot_id=target_slot.id,
            original_snapshot=_snapshot(s, e, original_slot, mould),
        )
        s.add(existing)
        action = '提交换机评估 '
    else:
        existing.target_slot_id = target_slot.id
        existing.original_snapshot = _snapshot(s, e, original_slot, mould)
        action = '重跑换机评估 '

    for col in ('comparable_count', 'machine_sample_counts', 'baseline_hours', 'target_hours',
                'target_lower_hours', 'target_upper_hours', 'saving_hours', 'saving_lower_hours',
                'saving_upper_hours', 'conservative_hours', 'floor_amount', 'quote_amount', 'evidence'):
        setattr(existing, col, None)
    existing.approved_by = None
    existing.approved_at = None
    existing.target_slot_id = target_slot.id
    existing.status = status
    existing.reject_reason = reason

    # Keep the learning output even when rejected (e.g. saving interval crosses
    # zero): the page must show the evidence behind a refusal, not a blank card.
    if payload:
        for k, v in payload.items():
            setattr(existing, k, v)
    if status == 'eligible':
        # Conservative migration reserve: upper 90% bound of target machine hours,
        # never below the original regression floor of 0.5h.
        existing.conservative_hours = round(existing.target_upper_hours, 2)
        floor = round(e.predicted_hours * e.rate * 1.15, 2)
        existing.floor_amount = floor
        existing.quote_amount = e.quote_amount
        if e.quote_amount < floor:
            existing.status = 'rejected'
            existing.reject_reason = f'当前报价 {e.quote_amount:.2f} 元低于底价 {floor:.2f} 元，换机不改变报价，拒绝推荐'
    record(s, u, action + e.code + ('（可换机）' if existing.status == 'eligible' else '（拒绝推荐）'))
    s.flush()
    return existing


def approve(s, req_id, u):
    req = s.get(MachineSwitchRequest, req_id)
    if not req:
        raise HTTPException(404, '换机评估不存在')
    if req.status == 'switched':
        raise HTTPException(409, '换机已生效，不可重复批准')
    if req.status != 'eligible':
        raise HTTPException(409, '仅可换机评估可由主管批准')

    e = s.query(Estimate).filter_by(id=req.estimate_id).with_for_update().one()
    snap = dict(req.original_snapshot)

    # Re-validate against live state: started estimates and lost commitments keep
    # their original machine. Every failure leaves the original commitment intact.
    if e.status != 'committed' or not e.slot_id:
        raise HTTPException(409, '原承诺已不成立，换机失败并保留原承诺')
    if e.slot_id != snap['original_slot_id']:
        raise HTTPException(409, '原机时承诺已发生变化，换机失败并保留原承诺')
    if s.scalar(select(TrialExecution.id).where(TrialExecution.estimate_id == e.id)):
        raise HTTPException(409, '估单已开工，保留原机台，换机失败')

    original_slot = s.query(MachineSlot).filter_by(id=snap['original_slot_id']).with_for_update().one()
    target_slot = s.query(MachineSlot).filter_by(id=req.target_slot_id).with_for_update().one()

    # Lock in slot-id order so concurrent approvals / commits cannot deadlock;
    # semantic references are resolved after the ordered locks are taken.
    first_id, second_id = sorted((original_slot.id, target_slot.id))
    s.query(MachineSlot).filter_by(id=first_id).with_for_update().one()
    s.query(MachineSlot).filter_by(id=second_id).with_for_update().one()
    original_slot = s.get(MachineSlot, snap['original_slot_id'])
    target_slot = s.get(MachineSlot, req.target_slot_id)

    reserve = round(req.conservative_hours, 2)
    if reserve > target_slot.capacity_hours - target_slot.reserved_hours + 1e-6:
        raise HTTPException(409, '目标时段余量不足以按保守工时预留，换机失败并保留原承诺')

    floor = round(e.predicted_hours * e.rate * 1.15, 2)
    if e.quote_amount < floor:
        raise HTTPException(409, f'报价 {e.quote_amount:.2f} 元已低于底价 {floor:.2f} 元，换机失败并保留原承诺')

    committed = round(snap['committed_hours'], 2)
    if original_slot.reserved_hours + 1e-6 < committed:
        raise HTTPException(409, '原机台预留数据异常，换机失败并保留原承诺')

    # Release old machine hours and occupy new machine hours in one transaction.
    original_slot.reserved_hours = round(original_slot.reserved_hours - committed, 2)
    target_slot.reserved_hours = round(target_slot.reserved_hours + reserve, 2)
    e.slot_id = target_slot.id
    # Quote, rate and predicted (regression) hours stay unchanged.
    req.status = 'switched'
    req.approved_by = u.email
    req.approved_at = datetime.now(timezone.utc).isoformat()
    record(
        s, u,
        f'主管批准换机 {e.code}: {snap["original_machine"]} 释放 {committed}h → '
        f'{target_slot.machine} 保守预留 {reserve}h（报价不变 ¥{e.quote_amount:.2f}）',
    )
    return req
