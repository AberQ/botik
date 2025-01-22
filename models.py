from sqlalchemy import *
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
from datetime import *
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


# Модель Product
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    artikul = Column(BigInteger, unique=True, index=True, nullable=False)  # Используем BigInteger для больших чисел
    name = Column(String, nullable=False)
    sale_price = Column(Numeric(10, 2))  # Для точных значений цены
    rating = Column(Numeric(3, 2))  # Ограничиваем точность для рейтинга
    quantity = Column(Integer)

# Пример создания таблиц (асинхронно)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    product_artikul = Column(BigInteger, ForeignKey("products.artikul"), nullable=False)  # Связь по артикулу
    subscribe_date = Column(DateTime, default=datetime.utcnow)  # Дата подписки
    active = Column(Boolean, default=True)  # Статус подписки

    # Связь с продуктом
    product = relationship("Product", backref="subscriptions")

