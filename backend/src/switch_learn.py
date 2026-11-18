"""Learn machine preference and correct process differences from signed trials.

Only *signed* cost reviews feed the pool, so every row is a finished, accepted
shop-floor actual. A mould-complexity vector explains process difficulty while a
machine fixed effect captures how each press performs on comparable work; the
machine effect is exactly the "big machine only looks fast because it gets the
easy moulds" correction requested by the business.
"""
import numpy as np
from sqlalchemy import select
from .models import Mould, Estimate, MachineSlot
from .execution_models import TrialExecution, CostReview
from .constants import (
    SWITCH_MIN_TOTAL, SWITCH_MIN_PER_MACHINE, SWITCH_INTERVAL_ALPHA,
    SWITCH_COMPARABLE_RADIUS,
)

STEEL_CODE = {'P20': 0, 'H13': 1, 'S136': 2}
FEATURE_NAMES = ['模腔', '滑块', '重量', '钢材']


def _t_critical(df, alpha=SWITCH_INTERVAL_ALPHA):
    # Two-sided (1-alpha) t quantile. scipy ships with scikit-learn; keep a
    # normal fallback so the module never hard-fails in a thin environment.
    try:
        from scipy.stats import t as t_dist
        return float(t_dist.ppf(1 - alpha / 2, df))
    except Exception:
        return 1.6449


def mould_vector(mould):
    return np.array([mould.cavities, mould.slides, mould.weight_kg, STEEL_CODE[mould.steel]], dtype=float)


def load_signed_samples(s):
    """One comparable row per signed trial: mould features, press used, actual hours."""
    rows = s.scalars(
        select(TrialExecution)
        .join(CostReview, CostReview.execution_id == TrialExecution.id)
        .where(CostReview.status == 'signed')
        .order_by(TrialExecution.id)
    ).all()
    out = []
    for x in rows:
        e = s.get(Estimate, x.estimate_id)
        if not e or not e.slot_id:
            continue
        slot = s.get(MachineSlot, e.slot_id)
        mould = s.get(Mould, e.mould_id)
        if not slot or not mould or not x.actual_hours:
            continue
        out.append({
            'estimate_code': e.code,
            'machine': slot.machine,
            'actual_hours': float(x.actual_hours),
            'features': mould_vector(mould),
            'mould_code': mould.code,
        })
    return out


def evaluate_switch(s, mould, original_machine, target_machine):
    """Return (status, reason, payload). Pure read-only statistics."""
    samples = load_signed_samples(s)
    target_vec = mould_vector(mould)
    if len(samples) < SWITCH_MIN_TOTAL:
        return 'rejected', f'已签结实绩仅 {len(samples)} 条，少于最低可比样本 {SWITCH_MIN_TOTAL} 条，拒绝推荐', None

    feat = np.vstack([r['features'] for r in samples])
    mean, std = feat.mean(axis=0), feat.std(axis=0)
    std[std == 0] = 1.0

    def z(v):
        return (v - mean) / std

    target_z = z(target_vec)
    distances = np.linalg.norm((feat - mean) / std - target_z, axis=1)
    comparable = [r for r, d in zip(samples, distances) if d <= SWITCH_COMPARABLE_RADIUS]
    counts = {}
    for r in comparable:
        counts[r['machine']] = counts.get(r['machine'], 0) + 1

    if len(comparable) < SWITCH_MIN_TOTAL:
        return 'rejected', (
            f'与本模工艺特征相近（归一化距离 ≤ {SWITCH_COMPARABLE_RADIUS}）的签结实绩仅 '
            f'{len(comparable)} 条，少于 {SWITCH_MIN_TOTAL} 条，缺可比样本，拒绝推荐'
        ), None
    if counts.get(original_machine, 0) < SWITCH_MIN_PER_MACHINE:
        return 'rejected', f'原机台 {original_machine} 可比签结样本仅 {counts.get(original_machine, 0)} 条，无法校正原机台工艺差异，拒绝推荐', None
    if counts.get(target_machine, 0) < SWITCH_MIN_PER_MACHINE:
        return 'rejected', f'目标机台 {target_machine} 可比签结样本仅 {counts.get(target_machine, 0)} 条，无法学习该机台倾向，拒绝推荐', None

    machines = sorted({r['machine'] for r in comparable})
    if original_machine not in machines or target_machine not in machines:
        return 'rejected', '可比样本未覆盖原机台或目标机台，拒绝推荐', None

    # Design: intercept + standardized process features + machine fixed effects
    # (first machine dropped; its level is absorbed by the intercept).
    base_machine = machines[0]
    design, y = [], []
    for r in comparable:
        row = [1.0, *z(r['features'])]
        row += [1.0 if r['machine'] == m else 0.0 for m in machines[1:]]
        design.append(row)
    X = np.array(design)
    y = np.array([r['actual_hours'] for r in comparable])
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, p = X.shape
    df = n - rank
    if df <= 0:
        return 'rejected', '可比样本自由度不足，回归不可识别，拒绝推荐', None
    sigma2 = float(resid @ resid / df)
    pinv = np.linalg.pinv(X)

    def design_row(machine):
        row = [1.0, *target_z]
        row += [1.0 if machine == m else 0.0 for m in machines[1:]]
        return np.array(row)

    def predict_with_interval(machine):
        x0 = design_row(machine)
        point = float(x0 @ beta)
        se = float(np.sqrt(sigma2 * (pinv.T @ x0) @ (pinv.T @ x0)))
        tcrit = _t_critical(df)
        return point, max(0.0, point - tcrit * se), point + tcrit * se

    base_point, _, _ = predict_with_interval(original_machine)
    target_point, target_lo, target_hi = predict_with_interval(target_machine)

    d = design_row(original_machine) - design_row(target_machine)
    saving = float(d @ beta)
    saving_se = float(np.sqrt(sigma2 * (pinv.T @ d) @ (pinv.T @ d)))
    tcrit = _t_critical(df)
    saving_lo, saving_hi = saving - tcrit * saving_se, saving + tcrit * saving_se

    machine_effects = {base_machine: 0.0}
    for m, coef in zip(machines[1:], beta[5:]):
        machine_effects[m] = float(coef)

    evidence = {
        'method': '工艺特征标准化 + 机台固定效应 OLS，机台效应已扣除模具复杂度差异',
        'feature_names': FEATURE_NAMES,
        'feature_mean': [round(float(v), 3) for v in mean],
        'feature_std': [round(float(v), 3) for v in std],
        'comparable_radius': SWITCH_COMPARABLE_RADIUS,
        'interval_confidence': 1 - SWITCH_INTERVAL_ALPHA,
        'n_comparable': n,
        'rank': int(rank),
        'residual_degrees_freedom': int(df),
        'residual_std_hours': round(float(np.sqrt(sigma2)), 3),
        'process_coefficients': {name: round(float(v), 4) for name, v in zip(FEATURE_NAMES, beta[1:5])},
        'machine_effects_hours': {m: round(v, 4) for m, v in machine_effects.items()},
        'machine_sample_counts': counts,
        'comparable_samples': [
            {
                'estimate_code': r['estimate_code'], 'mould_code': r['mould_code'],
                'machine': r['machine'], 'actual_hours': round(r['actual_hours'], 2),
                'distance': round(float(dist), 3),
            }
            for r, dist in zip(samples, distances) if dist <= SWITCH_COMPARABLE_RADIUS
        ],
    }
    payload = {
        'comparable_count': n,
        'machine_sample_counts': counts,
        'baseline_hours': round(max(0.5, base_point), 2),
        'target_hours': round(max(0.5, target_point), 2),
        'target_lower_hours': round(max(0.5, target_lo), 2),
        'target_upper_hours': round(max(0.5, target_hi), 2),
        'saving_hours': round(saving, 2),
        'saving_lower_hours': round(saving_lo, 2),
        'saving_upper_hours': round(saving_hi, 2),
        'evidence': evidence,
    }
    if saving_lo <= 0:
        return 'rejected', (
            f'换机节时点估计 {saving:.2f}h，90% 区间 [{saving_lo:.2f}, {saving_hi:.2f}]h '
            '不含稳定正向收益，拒绝推荐'
        ), payload
    return 'eligible', None, payload
