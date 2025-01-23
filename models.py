from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, Numeric, String)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from database import Base



# Модель Product
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    artikul = Column(BigInteger, unique=True, index=True, nullable=False)  # BigInteger для больших чисел
    name = Column(String, nullable=False)
    sale_price = Column(Numeric(10, 2))  # Для точных значений цены
    rating = Column(Numeric(3, 2))  # Ограничиваем точность для рейтинга
    quantity = Column(Integer)

    # Отношения с подписками
    subscriptions = relationship("Subscription", back_populates="product")

# Модель Subscription
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    product_artikul = Column(BigInteger, ForeignKey("products.artikul"), nullable=False)  # Связь по артикулу
    subscribe_date = Column(DateTime, default=datetime.utcnow)  # Дата подписки
    active = Column(Boolean, default=True)  # Статус подписки

    # Связь с продуктом
    product = relationship("Product", back_populates="subscriptions")


