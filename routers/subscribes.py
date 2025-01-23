
from sqlalchemy import *
from fastapi import Depends, FastAPI, HTTPException, APIRouter
from models import *
import httpx
from sqlalchemy import *
from main import *
from database import get_db, ProductRequest
from .products import get_product_details, router


@router.get("/api/v1/subscribe/{artikul}")
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