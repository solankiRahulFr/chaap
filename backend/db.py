from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import setting

if not setting.DATABASE_URL:
    raise RuntimeError("DB URL is not set or valid")

engine = create_async_engine(setting.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
 