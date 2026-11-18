import {api,send} from './api.js';
import {store,refresh} from './store.js';
import {ROLES} from './constants.js';
import {esc} from './utils/format.js';
import {notify} from './components/common.js';
import * as moulds from './pages/moulds.js';
import * as estimates from './pages/estimates.js';
import * as evidence from './pages/evidence.js';
import * as schedule from './pages/schedule.js';
import * as executions from './pages/executions.js';
import * as reviews from './pages/reviews.js';
import * as maintenance from './pages/maintenance.js';
import * as materials from './pages/materials.js';
import * as deliveries from './pages/deliveries.js';
const pages={moulds,estimates,evidence,schedule,executions,reviews,maintenance,materials,deliveries};
const labels={moulds:'01 模具工艺档案',estimates:'02 试模估价编辑',evidence:'03 误差与工时解释',schedule:'04 试模机时排程',executions:'05 试模实绩采集',reviews:'06 工时偏差结算',maintenance:'07 模具保养停机',materials:'08 试模材料领耗',deliveries:'09 客户交付验收'};
let timer;
function login(){document.querySelector('#app').innerHTML=`<div class="login"><section class="loginhero"><div class="mono">RUIMO / TOOLING ENGINEERING<br>锐模工场 · 工艺估价室</div><div><div class="kicker">TRIAL HOURS / COST / CAPACITY</div><h1>每一次试模，<br>先算清机时。</h1><p>把模腔、滑块、材料与重量写进估算。<br>报价有底线，机台有余量，生产承诺有据可查。</p><div class="blueprint"><svg viewBox="0 0 650 145" fill="none" stroke="currentColor"><rect x="100" y="12" width="440" height="112"/><rect x="125" y="35" width="390" height="65"/>${Array.from({length:8},(_,i)=>`<circle cx="${160+i%4*100}" cy="${52+Math.floor(i/4)*32}" r="10"/>`).join('')}<path d="M65 12V124M55 12H85M55 124H85M100 135H540"/></svg></div></div><small class="mono">32 PEOPLE · 03 PRESSES · ENGINEERED COMMITMENTS</small></section><section class="loginform"><div class="kicker">WORKSHOP ACCESS</div><h2>进入估价与排程</h2><p class="muted">按岗位执行工艺录入和生产承诺。</p><form id="login"><label>工作邮箱</label><input type="email" name="email" value="estimator@ruimo.demo" required><label>口令</label><input type="password" name="password" value="Mould2026!" required><button class="primary">登录工作台</button><div class="error" id="login-error"></div></form><p class="note">演示：estimator / admin / viewer @ruimo.demo<br>统一口令：Mould2026!<br>观察员只读；负责人可以承诺机时。</p></section></div>`;document.querySelector('#login').onsubmit=async ev=>{ev.preventDefault();try{const p=Object.fromEntries(new FormData(ev.target)),r=await send('/auth/login',p);localStorage.setItem('mould-token',r.token);store.user=r.user;location.hash='#moulds';await draw()}catch(e){document.querySelector('#login-error').textContent=e.message}}}
async function draw(){clearTimeout(timer);if(!localStorage.getItem('mould-token'))return login();try{if(!store.user)store.user=await api('/me');await refresh();const key=location.hash.slice(1) in pages?location.hash.slice(1):'moulds';document.querySelector('#app').innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand">锐模<small>TRIAL ENGINEERING</small></div><nav class="nav">${Object.entries(labels).map(([k,v])=>`<a href="#${k}" class="${key===k?'active':''}">${v}</a>`).join('')}</nav><div class="sidefoot">锐模工场 / 工艺估价室<br><span class="mono">${esc(store.user.email)}</span><br>${esc(ROLES[store.user.role])}<br><button id="logout">退出岗位</button></div></aside><main class="main"><header class="topline"><span>RUIMO / 工程估价与产能承诺</span><span class="mono">2026.11 / LOCAL DEMO</span></header>${pages[key].render(store)}</main></div>`;document.querySelector('#logout').onclick=()=>{localStorage.removeItem('mould-token');store.user=null;login()};pages[key].bind(store,draw);if(store.estimates.some(x=>x.status==='calculating'))timer=setTimeout(draw,1200)}catch(e){notify(e.message);if(!document.querySelector('.shell'))login()}}
window.addEventListener('hashchange',draw);draw();
