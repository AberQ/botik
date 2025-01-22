from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import *
from pydantic import BaseModel
import httpx
from sqlalchemy.future import *
import asyncio
from apscheduler.schedulers.background import *

from apscheduler.schedulers.asyncio import AsyncIOScheduler

BASE_URL = "http://localhost:8000"
app = FastAPI()

# URL внешнего API
EXTERNAL_API_URL = "https://card.wb.ru/cards/v1/detail"



scheduler = AsyncIOScheduler()
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
    
async def update_product_details():
    async with SessionLocal() as db:
        # Получаем все артикула товаров, на которые есть подписки
        result = await db.execute(select(Subscription.product_artikul).filter(Subscription.active == True))
        artikuls = result.scalars().all()

        for artikul in artikuls:
            try:
                # Получаем товар из базы данных
                product_query = await db.execute(select(Product).filter(Product.artikul == artikul))
                product = product_query.scalar()

                if product:
                    # Получаем информацию о товаре с помощью эндпоинта
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "http://127.0.0.1:8000/api/v1/products/",  # URL вашего эндпоинта
                            json={"artikul": product.artikul}
                        )

                    if response.status_code == 200:
                        # Парсим ответ, например, если возвращаемые данные есть
                        product_details = response.json()
                        new_name = product_details.get("name", product.name)
                        new_price = product_details.get("sale_price", product.sale_price)
                        
                        # Проверяем изменения в товаре
                        updated = False
                        
                        if product.name != new_name:
                            product.name = new_name
                            updated = True
                        
                        if product.sale_price != new_price:
                            product.sale_price = new_price
                            updated = True

                        # Если товар изменен, сохраняем изменения в базе данных
                        if updated:
                            await db.commit()  # Сохраняем изменения в базе данных
                            print(f"Информация о товаре с артикулом {artikul} успешно обновлена.")
                        else:
                            print(f"Нет изменений для товара с артикулом {artikul}.")
                    else:
                        print(f"Ошибка при запросе данных для товара с артикулом {artikul}. Статус: {response.status_code}")
                else:
                    print(f"Товар с артикулом {artikul} не найден.")
            except Exception as e:
                print(f"Ошибка при обновлении товара с артикулом {artikul}: {e}")
# Запуск планировщика
def start_scheduler():
    scheduler.add_job(update_product_details, 'interval', seconds=1800)
    scheduler.start()

@app.on_event("startup")
async def on_startup():
    # Запускаем планировщик при старте приложения
    start_scheduler()

@app.on_event("shutdown")
async def on_shutdown():
    # Останавливаем планировщик при завершении работы приложения
    scheduler.shutdown()