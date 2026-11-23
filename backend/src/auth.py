import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Header
from .config import JWT_SECRET, JWT_ALGORITHM
from .db import one

def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def issue_token(user: dict) -> str:
    payload = {"sub": str(user["id"]), "email": user["email"], "role": user["role"], "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="需要登录")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="登录已失效")
    user = one("SELECT id,email,full_name,role FROM users WHERE id=%s", (int(payload["sub"]),))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

def require_roles(*roles):
    def checker(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="当前角色无权执行该动作")
        return user
    return checker

def same_password(actual: str, expected: str) -> bool:
    return hmac.compare_digest(password_hash(actual), expected)
