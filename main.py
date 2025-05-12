from fastapi import FastAPI
from fastapi import Depends
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.responses import Response
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException

from sqlalchemy import select
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase

from typing import Annotated
from pydantic import Field

import uuid
import os.path
import io

import aiofiles
import qrcode
from qrcode.image.styledpil import StyledPilImage

from datetime import datetime, timezone, timedelta

# ====== Работа с бд ======

engine = create_async_engine('sqlite+aiosqlite:///files_metadata.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

# Генератор сессий
async def get_session():
    async with new_session() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# ====== Модели для алхимии ======

class Base(DeclarativeBase):
    pass

class FileModel(Base):
    __tablename__ = 'files_metadata'

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(unique=True, index=True)
    filename: Mapped[str] = mapped_column()
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiration_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

# ====== Работа с FastAPI ======

app = FastAPI()

# Монтируем статику
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def get_index():
    return FileResponse("static/index.html")

@app.get("/download/{file_id}", tags=["📄Файлы"], summary="Скачать файл")
async def download_file(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query) # Выполняем запрос

    db_result = result.scalars().first()

    if not db_result:
        raise HTTPException(status_code=404, detail="File not found")

    db_filename = str(db_result.filename)
    db_filepath = f"{file_id}_{db_filename}"
    filepath = os.path.join("uploads", db_filepath)

    if not filepath:
        raise HTTPException(status_code=404, detail="Iternal Error: File corrupted or deleted")

    return FileResponse(filepath, filename=db_filename)

@app.get("/get_all", tags=["⚙️Тестирование"], summary="Получить все из БД")
async def get_file(session: SessionDep):
    query = select(FileModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.get("/delete/{file_id}", tags=["⚙️Тестирование"], summary="Удалить файл по id")
async def delete_file(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query)  # Выполняем запрос

    db_result = result.scalars().first()

    if not db_result:
        raise HTTPException(status_code=404, detail="File not found")

    db_filename = str(db_result.filename)
    db_filepath = f"{file_id}_{db_filename}"
    filepath = os.path.join("uploads", db_filepath)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found in storage")

    # Сначала удаляем с диска
    try:
        os.remove(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to delete file: {e}")

    # Теперь удаляем с БД
    await session.delete(db_result)
    await session.commit()

    return {"Success": True}

@app.get("/qr/{file_id}", tags=["📄Файлы"], summary="Генерация QR")
async def generate_qr(file_id: str, request: Request):
    download_link = f"{str(request.base_url)}download/{file_id}"

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(download_link)

    qr_logo: bytes = qr.make_image(image_factory=StyledPilImage, embedded_image_path='cloud-icon.png')

    with io.BytesIO() as output:
        qr_logo.save(output, format="PNG")
        qr_bytes = output.getvalue()

        # В тело ответа - QR
        response = Response(content=qr_bytes, media_type="image/png")

        # Добавляем ссылку в заголовок (в дополнение к QR)
        response.headers["Download-Link"] = download_link
        return response

@app.post("/upload", tags=["📄Файлы"], summary="Загрузить файл")
async def upload_file(
        session: SessionDep, # В начале, чтобы fastapi не ругался
        uploaded_file: UploadFile = File(...),
        avail_period: Annotated[int, Form(...), Field(ge=1, le=24)] = 1 # Сколько файл будет доступен (1-24 ч)
):
    # Оригинальные параметры файла
    filename = uploaded_file.filename

    # Генерируем уникальный id
    newfile_id = str(uuid.uuid4())

    # Сохраняем файл (асинхронно)
    chunk_size = 1024 * 1024 # размер "чанка" - 1 мб

    newfile_path = os.path.join("uploads", f"{newfile_id}_{filename}")
    try:
        async with aiofiles.open(newfile_path, "wb") as buff_f:
            while chunk := await uploaded_file.read(chunk_size):
                await buff_f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to save file {filename}: {e}")

    # Формируем дату и время в utc
    upload_time = datetime.now(timezone.utc)
    expiration_time = upload_time + timedelta(hours=avail_period)

    # Коммитим в БД
    uploaded_file = FileModel(
        filename=filename, # Оригинальное имя
        file_id=newfile_id, # Уникальный id
        upload_time=upload_time, # Дата и время загрузки
        expiration_time=expiration_time, # Когда файл будет удален
    )
    session.add(uploaded_file)
    await session.commit() # только тут добавляем в бд

    return {
        "download_link": f"/download/{newfile_id}",
        "qr_code": f"/qr/{newfile_id}"
    }

@app.post("/setup_db", tags=["⚙️Тестирование"], summary="Стереть все файлы и пересоздать БД")
async def setup_db():
    # Удаляем файлы из uploads
    for filename in os.listdir("uploads"):
        file_path = os.path.join("uploads", filename)
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unable to erase files: {e}")

    # Пересоздаем таблицы в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"Success": True}
