from fastapi import APIRouter

from app.api.files import router as file_router

# Создаем общий роутер
base_router = APIRouter()

base_router.include_router(file_router)
