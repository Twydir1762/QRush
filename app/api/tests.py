from fastapi import APIRouter
from fastapi import HTTPException

from sqlalchemy import select

import os

from app.database import SessionDep, engine
from app.models import Base, FileModel
from app.utils import cleaning


router = APIRouter(tags=["⚙️Тестирование"])

# @router.get("/get_all", summary="Получить все из БД")
# async def get_file(session: SessionDep):
#     query = select(FileModel)
#     result = await session.execute(query)
#     return result.scalars().all()
#
# @router.post("/delete/{file_id}", summary="Удалить файл по id")
# async def delete_file(file_id: str, session: SessionDep):
#     query = select(FileModel).where(FileModel.file_id == file_id)
#     result = await session.execute(query)  # Выполняем запрос
#
#     db_result = result.scalars().first()
#
#     if not db_result:
#         raise HTTPException(status_code=404, detail="File not found")
#
#     db_filename = str(db_result.filename)
#     db_filepath = f"{file_id}_{db_filename}"
#     filepath = os.path.join("uploads", db_filepath)
#
#     if not os.path.exists(filepath):
#         raise HTTPException(status_code=404, detail="File not found in storage")
#
#     # Сначала удаляем с диска
#     try:
#         os.remove(filepath)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Unable to delete file: {e}")
#
#     # Теперь удаляем с БД
#     await session.delete(db_result)
#     await session.commit()
#
#     return {"Success": True}
#
# @router.post("/setup_db", summary="Удалить все файлы и пересоздать БД")
# async def setup_db():
#     # Удаляем файлы из uploads
#     for filename in os.listdir("uploads"):
#         file_path = os.path.join("uploads", filename)
#         try:
#             os.remove(file_path)
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Unable to erase files: {e}")
#
#     # Пересоздаем таблицы в БД
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#         await conn.run_sync(Base.metadata.create_all)
#     return {"Success": True}
#
# @router.post("/clean_up", summary='Удалить все "просроченные" файлы')
# async def clean_up(session: SessionDep):
#     res = await cleaning(session)
#     return res
