# ws_manager.py
import asyncio
from typing import Dict, Optional, List
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Message
from sqlalchemy import select, update, insert

class Connection:
    def __init__(self, user_id: int, websocket: WebSocket):
        self.user_id = user_id
        self.websocket = websocket

class WebSocketManager:
    def __init__(self):
        # mapping user_id -> WebSocket (single connection per user; extend to list for multi-tabs)
        self.active: Dict[int, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket):
        async with self.lock:
            self.active[user_id] = websocket

    async def disconnect(self, user_id: int):
        async with self.lock:
            self.active.pop(user_id, None)

    def is_connected(self, user_id: int) -> bool:
        return user_id in self.active

    def get_ws(self, user_id: int) -> Optional[WebSocket]:
        return self.active.get(user_id)
    
    def get_online_users(self) -> List[int]:
        """Return a list of currently connected user IDs"""
        return list(self.active.keys())

    async def send_json(self, recipient_id: int, payload: dict):
        ws = self.get_ws(recipient_id)
        if ws:
            try:
                await ws.send_json(payload)
                return True
            except Exception:
                # remove if there's an error delivering
                await self.disconnect(recipient_id)
        return False

    async def broadcast(self, payload: dict):
        async with self.lock:
            conns = list(self.active.items())
        for _user_id, ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                # swallow; will be cleaned on read/write
                pass

    # persistence helpers
    async def save_message(self, db: AsyncSession, sender_id: int, recipient_id: int, content: str, delivered: bool):
        msg = Message(sender_id=sender_id, recipient_id=recipient_id, content=content, delivered=delivered)
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def fetch_undelivered(self, db: AsyncSession, user_id: int):
        stmt = select(Message).where(Message.recipient_id == user_id, Message.delivered == False).order_by(Message.created_at)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def mark_delivered(self, db: AsyncSession, message_ids: list[int]):
        if not message_ids:
            return
        stmt = update(Message).where(Message.id.in_(message_ids)).values(delivered=True)
        await db.execute(stmt)
        await db.commit()
