import os, hashlib, hmac, secrets, time
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy import select
from .db import db_session
from .models import User
bearer=HTTPBearer()
SECRET=os.getenv('JWT_SECRET','local-mould-demo-change-me')
def hash_password(p):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),120000).hex()
def verify(p,h):
    salt,digest=h.split(':')
    return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),120000).hex(),digest)
def token(user): return jwt.encode({'sub':str(user.id),'exp':int(time.time())+28800},SECRET,algorithm='HS256')
def current(auth=Depends(bearer),s=Depends(db_session)):
    try:
        uid=int(jwt.decode(auth.credentials,SECRET,algorithms=['HS256'])['sub'])
        u=s.get(User,uid)
        if not u: raise ValueError()
        return u
    except Exception: raise HTTPException(401,'登录已过期，请重新登录')
def writers(u=Depends(current)):
    if u.role not in ('admin','estimator'): raise HTTPException(403,'观察员不能修改估价和排程')
    return u
def admin(u=Depends(current)):
    if u.role!='admin': raise HTTPException(403,'仅车间负责人可执行此操作')
    return u
