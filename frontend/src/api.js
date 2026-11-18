export async function api(path,options={}){
 const token=localStorage.getItem('mould-token');
 const res=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{}),...options.headers}});
 const data=await res.json();
 if(!res.ok){if(res.status===401){localStorage.removeItem('mould-token');location.hash='';location.reload()}throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail))}return data;
}
export const send=(path,data={},method='POST')=>api(path,{method,body:JSON.stringify(data)});
