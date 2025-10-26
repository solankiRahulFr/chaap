from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from models import models
from schemas import schemas
from curd import curd
from api import auth
from db import engine, get_db, AsyncSessionLocal
from core.config import setting
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from ws_manager import WebSocketManager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from typing import Dict, Optional, Any
from api.auth import decode_token
import json
from fastapi.staticfiles import StaticFiles
from api import ui
from curd.curd import get_user_by_username
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(title="chaap", lifespan=lifespan)

origins = ["*"] 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    """Return all users except the currently logged-in one."""
    users = await db.execute(
        models.User.__table__.select().where(models.User.id != current_user.id)
    )
    result = users.fetchall()
    return [{"id": row.id, "username": row.username} for row in result]

app.mount('/static', StaticFiles(directory='static'), name='static')
app.include_router(ui.router)

manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    """
    Expected connection:
    ws://host/ws?token=<JWT>
    Token must contain 'sub' or 'user_id' claim with user id.
    """
    # Accept the connection first (so we can return 401-like close if invalid)
    await websocket.accept()
    if not token:
        await websocket.close(code=4401)  # custom close code for unauthorized
        return

    # verify token and get user
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4401)
        return

    user_name = payload.get("sub") or payload.get("user_id")
    if user_name is None:
        await websocket.close(code=4401)
        return
    user_details = await get_user_by_username(db, user_name)
    user_id=user_details.id


    # register connection
    await manager.connect(user_id, websocket)

    # deliver undelivered messages

    undelivered = await manager.fetch_undelivered(db, user_id)
    delivered_ids = []
    for msg in undelivered:
        try:
            await websocket.send_json({
                "type": "message",
                "id": msg.id,
                "sender_id": msg.sender_id,
                "recipient_id": msg.recipient_id,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            })
            delivered_ids.append(msg.id)
        except Exception:
            # unable to deliver — leave as undelivered
            pass
    if delivered_ids:
        await manager.mark_delivered(db, delivered_ids)

    try:
        while True:
            data = await websocket.receive_text()
            # expecting JSON payload with recipient_id and content
            try:
                payload = json.loads(data)
                recipient_id = int(payload["recipient_id"])
                content = str(payload["content"])
            except Exception:
                # invalid payload; notify client
                await websocket.send_json({"type": "error", "message": "invalid payload, expected JSON with recipient_id and content"})
                continue

            # persist message, attempt immediate delivery
            is_delivered = False
            # if recipient is connected, send first then mark delivered
            if manager.is_connected(recipient_id):
                success = await manager.send_json(recipient_id, {
                    "type": "message",
                    "sender_id": user_id,
                    "recipient_id": recipient_id,
                    "content": content,
                })
                is_delivered = success

            msg = await manager.save_message(db, sender_id=user_id, recipient_id=recipient_id, content=content, delivered=is_delivered)

            # ack to sender with stored message id and delivered flag
            await websocket.send_json({
                "type": "ack",
                "message_id": msg.id,
                "delivered": is_delivered
            })

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception:
        await manager.disconnect(user_id)
        try:
            await websocket.close()
        except Exception:
            pass

from sqlalchemy.future import select

@app.get("/messages/{user_id}")
async def get_chat_with_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    stmt = select(models.Message).where(
        ((models.Message.sender_id == current_user.id) & (models.Message.recipient_id == user_id))
        | ((models.Message.sender_id == user_id) & (models.Message.recipient_id == current_user.id))
    ).order_by(models.Message.created_at)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "content": m.content,
            "timestamp": m.created_at.isoformat(),
        }
        for m in messages
    ]

@app.get("/online-users")
async def get_online_users(db=Depends(get_db)):
    online_ids = manager.get_online_users()
    stmt = select(models.User).where(models.User.id.in_(online_ids))
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username} for u in users]