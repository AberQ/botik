from sqlalchemy import *
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *

from main import *
from models import *

DATABASE_URL = "postgresql+asyncpg://postgres:123@localhost/botik"

# Базовый класс
Base = declarative_base()

# Асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Асинхронная сессия
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with SessionLocal() as db:
        yield db

# Модель для валидации данных из запроса
class ProductRequest(BaseModel):
    artikul: int