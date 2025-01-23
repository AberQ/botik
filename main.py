
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from routers.products import router
from routers.subscribes import update_product_details
app = FastAPI()

app.include_router(router)




scheduler = AsyncIOScheduler()


# Создаём асинхронный движок и сессию
DATABASE_URL = "postgresql+asyncpg://postgres:123@localhost/botik"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)







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