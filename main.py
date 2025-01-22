from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import *
from pydantic import BaseModel
import httpx
from sqlalchemy.future import *

app = FastAPI()

# URL внешнего API
EXTERNAL_API_URL = "https://card.wb.ru/cards/v1/detail"

# Модель для валидации данных из запроса
class ProductRequest(BaseModel):
    artikul: int

# Создаём асинхронный движок и сессию
DATABASE_URL = "postgresql+asyncpg://postgres:123@localhost/botik"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Получение сессии базы данных
async def get_db():
    async with SessionLocal() as db:
        yield db

@app.post("/api/v1/products/")
async def get_product_details(request: ProductRequest, db: AsyncSession = Depends(get_db)):
    """
    Эндпоинт для получения данных о товаре с Wildberries по артикулу.
    Если продукт уже существует, обновляет его данные.
    """
    params = {
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,
        "spp": 30,
        "nm": request.artikul,
    }

    try:
        # Отправка запроса к внешнему API
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_URL, params=params)

        # Проверка ответа
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Ошибка при запросе к внешнему API")

        # Извлечение данных из ответа
        response_data = response.json()

        # Проверяем наличие данных о продуктах
        if "data" not in response_data or "products" not in response_data["data"]:
            raise HTTPException(status_code=404, detail="Товар не найден")

        # Берем первый продукт из списка
        product_data = response_data["data"]["products"][0]

        # Проверяем, есть ли продукт уже в базе данных
        result = await db.execute(
            select(Product).filter(Product.artikul == request.artikul)
        )
        existing_product = result.scalars().first()

        if existing_product:
            # Обновляем данные продукта
            existing_product.name = product_data.get("name")
            existing_product.sale_price = product_data.get("salePriceU") / 100  # Цена со скидкой
            existing_product.rating = product_data.get("reviewRating")
            existing_product.quantity = product_data.get("totalQuantity")
            await db.commit()
            await db.refresh(existing_product)
            return {
                "artikul": existing_product.artikul,
                "name": existing_product.name,
                "sale_price": existing_product.sale_price,
                "rating": existing_product.rating,
                "quantity": existing_product.quantity,
            }

        # Если продукт не найден, создаем новый
        product = Product(
            artikul=product_data.get("id"),
            name=product_data.get("name"),
            sale_price=product_data.get("salePriceU") / 100,  # Цена со скидкой
            rating=product_data.get("reviewRating"),
            quantity=product_data.get("totalQuantity"),
        )

        db.add(product)
        await db.commit()
        await db.refresh(product)

        return {
            "artikul": product.artikul,
            "name": product.name,
            "sale_price": product.sale_price,
            "rating": product.rating,
            "quantity": product.quantity,
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к внешнему API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")

@app.get("/api/v1/subscribe/{artikul}")
async def subscribe_to_product(artikul: int, db: AsyncSession = Depends(get_db)):
    """
    Эндпоинт для подписки на товар по артикулу.
    """
    try:
        # Используем существующую функцию get_product_details
        product_details = await get_product_details(ProductRequest(artikul=artikul), db)

        # Проверяем, есть ли уже подписка
        result = await db.execute(
            select(Subscription).filter(Subscription.product_artikul == artikul)
        )
        existing_subscription = result.scalars().first()

        if existing_subscription:
            raise HTTPException(status_code=400, detail="Вы уже подписаны на этот товар")

        # Создаем новую подписку
        subscription = Subscription(product_artikul=artikul)
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        return {
            "message": "Вы успешно подписались на товар",
            "artikul": artikul,
            "name": product_details["name"],  # Используем данные из функции
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")