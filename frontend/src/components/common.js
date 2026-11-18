import {esc,money,number} from '../utils/format.js';
import {STATES} from '../constants.js';
export const badge=e=>`<span class="status ${esc(e.status)}">${esc(STATES[e.status]||e.status)}</span>`;
export const mouldLabel=(s,id)=>{const m=s.moulds.find(x=>x.id===id);return m?esc(m.code+' · '+m.name):'#'+id};
export const evidenceStrip=e=>e?`<div class="ribbon"><div>估单 <strong class="mono">${esc(e.code)}</strong></div><div>预测总机时<strong class="mono">${number(e.predicted_hours)} h</strong></div><div>当前报价<strong class="mono">¥ ${money(e.quote_amount)}</strong></div><div>业务状态<strong>${badge(e)}</strong></div></div>`:'';
export function notify(message){const n=document.querySelector('#toast');n.textContent=message;n.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>n.classList.remove('show'),4200)}
export const empty=message=>`<div class="empty">${esc(message)}</div>`;
export const estimatePicker=s=>`<select id="estimate-picker">${s.estimates.map(e=>`<option value="${e.id}" ${e.id===Number(s.selected)?'selected':''}>${esc(e.code)} · ${esc(STATES[e.status])}</option>`).join('')}</select>`;
