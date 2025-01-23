from asyncio import run, create_task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from routers.products import router, update_product_details
from database import SessionLocal, engine, init_db
app = FastAPI()

app.include_router(router)



scheduler = AsyncIOScheduler()


def update_product_details_wrapper():
    create_task(update_product_details())

def start_scheduler():
    scheduler.add_job(update_product_details_wrapper, 'interval', seconds=1800)
    scheduler.start()

@app.on_event("startup")
async def on_startup():
    # Инициализируем базу данных
    await init_db()

    # Запускаем планировщик при старте приложения
    start_scheduler()

@app.on_event("shutdown")
async def on_shutdown():
    # Останавливаем планировщик при завершении работы приложения
    scheduler.shutdown()