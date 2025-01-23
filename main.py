from asyncio import create_task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from routers.products import router, update_product_details
from database import init_db

app = FastAPI()

app.include_router(router)

scheduler = AsyncIOScheduler()

async def update_product_details_wrapper():
    # Создаем асинхронную задачу для обновления данных
    create_task(update_product_details())

def start_scheduler():
    # Добавляем задачу в планировщик с интервалом 30 секунд
    scheduler.add_job(update_product_details_wrapper, 'interval', seconds=30)
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
