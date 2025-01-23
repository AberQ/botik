
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from fastapi import Depends, FastAPI, HTTPException, APIRouter
from models import Product, Subscription
import httpx
from sqlalchemy import *
from database import get_db, ProductRequest, SessionLocal, async_session
from schemas import ProductResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

router = APIRouter()
BASE_URL = "http://localhost:8000"


# URL внешнего API
EXTERNAL_API_URL = "https://card.wb.ru/cards/v1/detail"
@router.post("/api/v1/products/", response_model=ProductResponse)
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
            raise HTTPException(
                status_code=response.status_code, 
                detail="Ошибка при запросе к внешнему API"
            )

        # Проверяем, есть ли данные о товарах в ответе
        try:
            response_data = response.json()
        except ValueError:
            raise HTTPException(
                status_code=500, 
                detail="Некорректный ответ от внешнего API"
            )

        # Проверка структуры данных в ответе
        products = response_data.get("data", {}).get("products", [])
        if not products:
            raise HTTPException(
                status_code=404, 
                detail="Товар не найден"
            )

        product_data = products[0]

        # Проверяем, есть ли продукт уже в базе данных
        result = await db.execute(
            select(Product).filter(Product.artikul == request.artikul)
        )
        existing_product = result.scalars().first()

        if existing_product:
            existing_product.name = product_data.get("name")
            existing_product.sale_price = product_data.get("salePriceU") / 100
            existing_product.rating = product_data.get("reviewRating")
            existing_product.quantity = product_data.get("totalQuantity")
            await db.commit()
            await db.refresh(existing_product)
            return existing_product

        # Если продукта нет в базе данных, создаем новый
        product = Product(
            artikul=product_data.get("id"),
            name=product_data.get("name"),
            sale_price=product_data.get("salePriceU") / 100,
            rating=product_data.get("reviewRating"),
            quantity=product_data.get("totalQuantity"),
        )

        db.add(product)
        await db.commit()
        await db.refresh(product)

        return product

    except HTTPException as e:
        # Пробрасываем HTTPException, чтобы сохранить код и сообщение
        raise e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка подключения к внешнему API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Произошла ошибка: {str(e)}"
        )
    

    
@router.get("/api/v1/subscribe/{artikul}")
async def subscribe_to_product(artikul: int, db: AsyncSession = Depends(get_db)):
    """
    Эндпоинт для подписки на товар по артикулу.
    """
    try:
        # Получаем детали продукта
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
            "artikul": product_details.artikul,
            "name": product_details.name,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")


async def update_product_details():
    async with async_session() as db:  # Используем правильное создание сессии
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
                        # Парсим ответ
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
                            await db.commit()
                            print(f"Информация о товаре с артикулом {artikul} успешно обновлена.")
                        else:
                            print(f"Нет изменений для товара с артикулом {artikul}.")
                    else:
                        print(f"Ошибка при запросе данных для товара с артикулом {artikul}. Статус: {response.status_code}")
                else:
                    print(f"Товар с артикулом {artikul} не найден.")
            except Exception as e:
                print(f"Ошибка при обновлении товара с артикулом {artikul}: {e}")