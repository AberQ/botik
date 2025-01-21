from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()


EXTERNAL_API_URL = "https://card.wb.ru/cards/v1/detail"


class ProductRequest(BaseModel):
    artikul: int


@app.post("/api/v1/products/")
async def get_product_details(request: ProductRequest):
    """
    Эндпоинт для получения данных о товаре с Wildberries по артикулу.
    """
    params = {
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,
        "spp": 30,
        "nm": request.artikul,
    }

    try:
       
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_URL, params=params)

      
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Ошибка при запросе к внешнему API")

     
        response_data = response.json()

      
        if "data" not in response_data or "products" not in response_data["data"]:
            raise HTTPException(status_code=404, detail="Товар не найден")

      
        product = response_data["data"]["products"][0]

       
        formatted_data = {
            "name": product.get("name"),
            "artikul": product.get("id"),
            "sale_price": product.get("salePriceU") / 100, 
            "rating": product.get("rating"),
            "quantity": product.get("totalQuantity"),
        }

        return {"state": "success", "product": formatted_data}

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к внешнему API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")
