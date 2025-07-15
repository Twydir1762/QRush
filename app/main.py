from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api import base_router
from app.database import setup_database
from app.utils import clean_up_task, setup_uploads

# ====== Работа с FastAPI ======

# Создает ФОНОВЫЙ планировщик
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(current_app: FastAPI):
    # Перед запуском приложения
    await setup_database()
    await setup_uploads()

    scheduler.add_job(clean_up_task, "interval", minutes=1)
    scheduler.start()

    yield # <--- работа приложения

    # Завершение работы приложения
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(base_router)

# Монтируем статику
app.mount("/static", StaticFiles(directory="app/static"), name="static")








