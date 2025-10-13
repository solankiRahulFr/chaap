from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import setting
from curd.curd import get_user_by_username
from db import get_db
from jose import jwt

security = HTTPBearer()

def create_access_token(subject: str, expires_delta:timedelta| None):
    now = datetime.now()
    expire = now + (expires_delta or timedelta(minutes=setting.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp":int(expire.timestamp())
    }
    token= jwt.encode(payload, setting.SECRET_KEY, algorithm=setting.ALGORITHM)
    return token


def decode_token(token:str):
    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tokn expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    

async def get_current_user(credentials : HTTPAuthorizationCredentials = Depends(security), db:AsyncSession =Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail= "Invalid token payload")
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user