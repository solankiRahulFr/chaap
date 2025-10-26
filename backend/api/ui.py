from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

router = APIRouter()

static_dir = Path(__file__).resolve().parent.parent / "static"

@router.get("/", response_class=HTMLResponse)
async def get_index():
    with open(static_dir / "chat.html") as f:
        return f.read()
