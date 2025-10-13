from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from models import models
from schemas import schemas
from curd import curd
from api import auth
from db import engine, get_db
from core.config import setting
from contextlib import asynccontextmanager
from datetime import datetime, timedelta


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(title="chaap", lifespan=lifespan)

@app.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await curd.get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist")
    user = await curd.create_user(db, user_in.username, user_in.password)
    return user


@app.post("/login", response_model=schemas.Token)
async def login(user_in: schemas.UserCreate, db:AsyncSession = Depends(get_db)):
    user= await curd.get_user_by_username(db, user_in.username)
    if not user or not curd.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth.create_access_token(subject=user.username, expires_delta= timedelta(60))
    return {"access_token":token, "token_type": "bearer"}


@app.get("/user", response_model=schemas.UserOut)
async def read_user(current_user=Depends(auth.get_current_user)):
    return current_user