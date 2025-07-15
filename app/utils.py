from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

import os
from datetime import datetime, timezone
from pathlib import Path

from app.database import new_session
from app.models import FileModel

# Cоздать папки uploads если её нет
async def setup_uploads():
    root_folder = Path(__file__).resolve().parent.parent
    uploads_folder = root_folder / "uploads"
    if not uploads_folder.exists():
        uploads_folder.mkdir(exist_ok=True)

# Обертка для чистой функции удаления файлов (создаем задачу, даем сессию для планировщика)
async def clean_up_task():
    async with new_session() as session:
        await cleaning(session)

# Функция для очистки "просроченных" файлов
async def cleaning(session: AsyncSession):
    query = select(FileModel).where(FileModel.expiration_time < datetime.now(timezone.utc))
    result = await session.execute(query)  # Выполняем запрос

    expired_files = result.scalars().all()

    # Список всех истекших id
    expired_ids = []

    # Если нашли "просроченные" файлы
    for file in expired_files:
        db_filename = str(file.filename)
        db_filepath = f"{file.file_id}_{db_filename}"
        filepath = os.path.join("uploads", db_filepath)

        # Сначала удаляем с диска
        if not os.path.exists(filepath):
            continue

        try:
            os.remove(filepath)
            expired_ids.append(file.file_id)
        except Exception as e:
            pass # Тут надо бы логировать ошибку

    # Теперь пачкой удаляем с БД
    if expired_ids:
        delete_query = delete(FileModel).where(FileModel.file_id.in_(expired_ids))
        await session.execute(delete_query)
        await session.commit()

    return {
        "Success": True,
        "Deleted": str(len(expired_ids))
    }

async def file_iter(file):
    # Читаем по 256 кб
    while chunk := await file.read(256 * 1024):
        yield chunk