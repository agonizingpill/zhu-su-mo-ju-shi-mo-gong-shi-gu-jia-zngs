import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class RequestTrace(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        rid=uuid.uuid4().hex[:12]
        response=await call_next(request)
        response.headers['X-Request-ID']=rid
        return response
class BurstGuard(BaseHTTPMiddleware):
    def __init__(self,app): super().__init__(app); self.hits={}
    async def dispatch(self,request,call_next):
        if request.url.path=='/health': return await call_next(request)
        key=request.client.host; now=time.monotonic()
        hits=[t for t in self.hits.get(key,[]) if now-t<60]
        if len(hits)>240: return JSONResponse({'detail':'请求过密，请稍后重试'},429)
        self.hits[key]=hits+[now]
        return await call_next(request)
