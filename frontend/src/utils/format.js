export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const money=x=>Number(x||0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
export const number=x=>x==null?'—':Number(x).toFixed(2);
export const formData=form=>Object.fromEntries(new FormData(form));
