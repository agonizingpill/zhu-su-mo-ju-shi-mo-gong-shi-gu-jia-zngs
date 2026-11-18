import {esc, number, money} from '../utils/format.js';
import {send} from '../api.js';
import {notify} from '../components/common.js';
import {SWITCH_STATES} from '../constants.js';

const switchBadge = x => `<span class="status ${esc(x.status)}">${esc(SWITCH_STATES[x.status] || x.status)}</span>`;

function interval(x) {
  if (x.saving_lower_hours == null) return '—';
  return `${number(x.saving_lower_hours)} ~ ${number(x.saving_upper_hours)} h`;
}

function evidenceBlock(x) {
  if (!x.evidence) return '';
  const ev = x.evidence;
  return `<details class="evidence"><summary>评估依据（${esc(ev.method)}）</summary>
    <div class="grid4">
      <div><small>可比签结样本</small><b class="mono">${ev.n_comparable} 条</b></div>
      <div><small>残差标准差</small><b class="mono">${number(ev.residual_std_hours)} h</b></div>
      <div><small>区间置信度</small><b class="mono">${Math.round(ev.interval_confidence * 100)}%</b></div>
      <div><small>回归自由度</small><b class="mono">${ev.residual_degrees_freedom}</b></div>
    </div>
    <h4>机台固定效应（小时，已扣除模具复杂度）</h4>
    <div class="chips">${Object.entries(ev.machine_effects_hours).map(([m, v]) => `<span class="chip">${esc(m)}：<b class="mono">${v > 0 ? '+' : ''}${number(v)} h</b> · ${ev.machine_sample_counts[m] || 0} 条</span>`).join('')}</div>
    <h4>工艺特征标准化系数</h4>
    <div class="chips">${Object.entries(ev.process_coefficients).map(([k, v]) => `<span class="chip">${esc(k)}：<b class="mono">${number(v)}</b></span>`).join('')}</div>
    <h4>参与回归的签结实绩（归一化距离 ≤ ${ev.comparable_radius}）</h4>
    <table class="mini"><thead><tr><th>估单</th><th>模具</th><th>机台</th><th>实际工时</th><th>距离</th></tr></thead><tbody>
    ${ev.comparable_samples.map(r => `<tr><td class="mono">${esc(r.estimate_code)}</td><td>${esc(r.mould_code)}</td><td class="mono">${esc(r.machine)}</td><td class="mono">${number(r.actual_hours)}</td><td class="mono">${number(r.distance)}</td></tr>`).join('')}
    </tbody></table></details>`;
}

function card(s, x) {
  const target = s.slots.find(z => z.id === x.target_slot_id);
  return `<article class="switch-card ${esc(x.status)}">
    <div class="switchhead">
      <div><b class="mono">${esc(x.estimate_code)}</b> <small>${esc(x.mould_code)}</small><br>
      <small>${esc(x.original_machine)} ${esc(x.original_start_hour || '')} → <b>${esc(x.target_machine)}</b> ${esc(x.target_start_hour || '')}</small></div>
      ${switchBadge(x)}
    </div>
    ${x.status === 'rejected' ? `<p class="reject">${esc(x.reject_reason || '缺可比样本，拒绝推荐')}</p>` : ''}
    ${x.status === 'pending' ? '<p class="muted">评估中断，可重试，重试不会新增申请。</p>' : ''}
    ${x.status !== 'pending' && x.target_hours != null ? `<div class="grid4">
      <div><small>原机台基线</small><b class="mono">${number(x.baseline_hours)} h</b></div>
      <div><small>目标机台估计</small><b class="mono">${number(x.target_hours)} h</b></div>
      <div><small>节时点估计 / 区间</small><b class="mono">${number(x.saving_hours)} h</b><small>90%：${interval(x)}</small></div>
      <div><small>可比样本</small><b class="mono">${x.comparable_count == null ? '—' : x.comparable_count + ' 条'}</b></div>
    </div>` : ''}
    ${x.status === 'eligible' ? `<div class="grid4">
      <div><small>报价（不变）</small><b class="mono">¥ ${money(x.quote_amount)}</b></div>
      <div><small>成本底价</small><b class="mono">¥ ${money(x.floor_amount)}</b></div>
      <div><small>目标时段余量</small><b class="mono">${number(x.target_available_hours)} h</b></div>
      <div><small>审批</small><b>${x.approved_by ? esc(x.approved_by) : '待主管批准'}</b></div>
    </div>` : ''}
    ${evidenceBlock(x)}
    <div class="actions">
      ${x.status === 'eligible' ? `<button class="primary" data-approve="${x.id}" ${s.user.role !== 'admin' ? 'disabled' : ''}>主管批准：按保守工时迁移预留</button>` : ''}
      ${x.status === 'rejected' ? `<button data-retry="${x.id}" ${s.user.role === 'viewer' ? 'disabled' : ''}>重试评估（不新增申请）</button>` : ''}
    </div>
  </article>`;
}

export function render(s) {
  const candidates = s.estimates.filter(e => e.status === 'committed');
  const startedIds = new Set(s.executions.map(x => x.estimate_id));
  const targetableSlots = s.slots;
  const groups = [
    ['pending', '待评估'],
    ['rejected', '拒绝推荐（缺可比样本或无稳定收益）'],
    ['eligible', '可换机（待主管批准）'],
    ['switched', '已换机（旧机时释放、新机时占用同时生效）'],
  ];
  return `<div class="heading"><div><div class="kicker">10 / MACHINE SWITCH</div><h1>已承诺未开工估单 · 换机评估</h1><p class="muted">用已签结实绩学习机台选择倾向并校正工艺差异；原估价回归与报价保留，缺可比样本即拒绝推荐。</p></div></div>
  <section class="panel paper"><h2>新建换机评估（可中断续跑，重试不新增申请）</h2>
    <form id="switch-form" class="inlineform">
      <label>已承诺未开工估单
        <select name="estimate_id" required>${candidates.map(e => `<option value="${e.id}">${esc(e.code)} · ${esc(s.moulds.find(m => m.id === e.mould_id)?.code || '')}${startedIds.has(e.id) ? '（已开工，禁止换机）' : ''}</option>`).join('')}</select>
      </label>
      <label>目标机台时段（跨机台）
        <select name="target_slot_id" required>${targetableSlots.map(z => `<option value="${z.id}">${esc(z.machine)} · ${esc(z.start_hour)} · 余量 ${number(z.capacity_hours - z.reserved_hours)}h</option>`).join('')}</select>
      </label>
      <button class="primary" ${s.user.role === 'viewer' ? 'disabled' : ''}>提交评估</button>
    </form>
    <p class="note">仅已承诺且未开工估单可评估；已开工估单保留原机台、不超售。批准时按目标工时 90% 区间上界保守预留，报价不变且仍须高于底价。</p>
  </section>
  ${groups.map(([key, title]) => {
    const rows = s.switches.filter(x => x.status === key);
    return `<section class="panel"><h2>${title} <span class="mono muted">${rows.length}</span></h2>${rows.map(x => card(s, x)).join('') || '<div class="empty">暂无记录</div>'}</section>`;
  }).join('')}`;
}

export function bind(s, reload) {
  const form = document.querySelector('#switch-form');
  if (form) form.onsubmit = async ev => {
    ev.preventDefault();
    const p = Object.fromEntries(new FormData(ev.target));
    try {
      await send('/machine-switches', {estimate_id: Number(p.estimate_id), target_slot_id: Number(p.target_slot_id)});
      notify('换机评估完成（拒绝或可换机均见依据）');
      await reload();
    } catch (e) { notify(e.message); }
  };
  document.querySelectorAll('[data-approve]').forEach(b => b.onclick = async () => {
    try {
      await send(`/machine-switches/${b.dataset.approve}/approve`);
      notify('换机已生效：旧机时释放与新机时占用同时完成，报价不变');
      await reload();
    } catch (e) { notify(e.message); }
  });
  document.querySelectorAll('[data-retry]').forEach(b => b.onclick = async () => {
    const row = s.switches.find(x => String(x.id) === b.dataset.retry);
    try {
      await send('/machine-switches', {estimate_id: row.estimate_id, target_slot_id: row.target_slot_id});
      notify('已在原申请上重新评估');
      await reload();
    } catch (e) { notify(e.message); }
  });
}
