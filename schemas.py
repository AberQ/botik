from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# Схема для продукта (базовая)
class ProductBase(BaseModel):
    artikul: int = Field(..., example=123456789)
    name: str = Field(..., example="Пример товара")
    sale_price: Optional[float] = Field(None, example=99.99)
    rating: Optional[float] = Field(None, example=4.5)
    quantity: Optional[int] = Field(None, example=100)

# Схема для создания продукта
class ProductCreate(ProductBase):
    pass  # Используем те же поля, что и в ProductBase

# Схема для обновления продукта
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Обновлённый товар")
    sale_price: Optional[float] = Field(None, example=150.00)
    rating: Optional[float] = Field(None, example=5.0)
    quantity: Optional[int] = Field(None, example=50)

# Схема для ответа о продукте
class ProductResponse(ProductBase):
    id: int

    class Config:
        orm_mode = True  # Позволяет Pydantic работать с объектами SQLAlchemy


# Схема для подписки (базовая)
class SubscriptionBase(BaseModel):
    product_artikul: int = Field(..., example=123456789)
    subscribe_date: Optional[datetime] = Field(None, example="2025-01-23T12:34:56")
    active: Optional[bool] = Field(True, example=True)

# Схема для создания подписки
class SubscriptionCreate(SubscriptionBase):
    pass  # Используем те же поля, что и в SubscriptionBase

# Схема для обновления подписки
class SubscriptionUpdate(BaseModel):
    active: Optional[bool] = Field(None, example=False)

# Схема для ответа о подписке
class SubscriptionResponse(SubscriptionBase):
    id: int
    product: Optional[ProductResponse]  # Вложенный объект продукта

    class Config:
        orm_mode = True
