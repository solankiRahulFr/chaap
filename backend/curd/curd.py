# app/crud.py
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import User
from jose import jwt
import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

async def get_user_by_username(db: AsyncSession, username: str):
    q = select(User).where(User.username == username)
    result = await db.execute(q)
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, password: str):
    hashed = hash_password(password)
    user = User(username=username, hashed_password=hashed)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        await db.rollback()
        raise
