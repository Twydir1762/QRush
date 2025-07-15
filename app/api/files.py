from fastapi import APIRouter
from fastapi import Request
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from fastapi import UploadFile, File, Form

from sqlalchemy import select

from typing import Annotated
from pydantic import Field

import os
import uuid
import io
import aiofiles
from datetime import datetime, timezone, timedelta
import asynczipstream

import qrcode
from qrcode.image.styledpil import StyledPilImage

from app.database import SessionDep
from app.models import FileModel
from app.config import MAX_FILE_SIZE
from app.utils import file_iter

router = APIRouter(tags=["📄Файлы"])

@router.get("/", include_in_schema=False)
def get_index():
    return FileResponse("app/static/index.html")

@router.get("/config", include_in_schema=False)
def get_config():
    return {
        "max_file_size": MAX_FILE_SIZE
    }

@router.get("/download/{file_id}", summary="Скачать файл")
async def download_file(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query) # Выполняем запрос

    db_result = result.scalars().first()

    if not db_result:
        # raise HTTPException(status_code=404, detail="File not found")
        return FileResponse("app/static/not_found.html")

    db_filename = str(db_result.filename)
    db_filepath = f"{file_id}_{db_filename}"
    filepath = os.path.join("uploads", db_filepath)

    if not filepath:
        # raise HTTPException(status_code=404, detail="Iternal Error: File corrupted or deleted")
        return FileResponse("app/static/not_found.html")

    return FileResponse(filepath, filename=db_filename)

@router.get("/qr/{file_id}", summary="Генерация QR")
async def generate_qr(file_id: str, request: Request):
    download_link = f"{str(request.base_url)}download/{file_id}"

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(download_link)

    qr_logo: bytes = qr.make_image(image_factory=StyledPilImage, embedded_image_path='app/static/main_cloud.png')

    with io.BytesIO() as output:
        qr_logo.save(output, format="PNG")
        qr_bytes = output.getvalue()

        # В тело ответа - QR
        response = Response(content=qr_bytes, media_type="image/png")

        # Добавляем ссылку в заголовок (в дополнение к QR)
        response.headers["Download-Link"] = download_link
        return response

@router.post("/upload", summary="Загрузить файлы")
async def upload_files(
        session: SessionDep, # В начале, чтобы fastapi не ругался
        uploaded_files: list[UploadFile] = File(...),
        avail_period: Annotated[int, Form(...), Field(ge=1, le=24)] = 1 # Сколько файл будет доступен (1-24 ч)
):

    # Генерируем уникальный id
    newfile_id = str(uuid.uuid4())

    if len(uploaded_files) > 1:

        filename = f"{uploaded_files[0].filename}.zip"
        newfile_path = os.path.join("uploads", f"{newfile_id}_{filename}")

        zipf = asynczipstream.ZipFile()

        for file in uploaded_files:
            zipf.write_iter(file.filename, file_iter(file))

        async with aiofiles.open(newfile_path, 'wb') as zip_buff:
            zip_files_size = 0

            async for data in zipf:
                # Проверяем размер всех файлов
                chunk_len = len(data)
                zip_files_size += chunk_len

                if zip_files_size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail=f"Размер файла не должен превышать "
                                                                f"{MAX_FILE_SIZE / 1048576} МБ")

                await zip_buff.write(data)
    else:
        uploaded_file = uploaded_files[0]

        # Оригинальные параметры файла
        filename = uploaded_files[0].filename

        newfile_path = os.path.join("uploads", f"{newfile_id}_{filename}")

        # Сохраняем файл (асинхронно)
        chunk_size = 1024 * 1024 # размер "чанка" - 1 мб

        try:
            async with aiofiles.open(newfile_path, "wb") as buff_f:
                total_size = 0
                while chunk := await uploaded_file.read(chunk_size):
                    # Проверка размера если обошли фронтенд
                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=413, detail=f"Размер файла не должен превышать "
                                                                    f"{MAX_FILE_SIZE / 1048576} МБ")
                    await buff_f.write(chunk)

        except Exception as e:
            if os.path.exists(newfile_path): # Удаляем недогруженный файл
                os.remove(newfile_path)

            if isinstance(e, HTTPException): # Если ошибка - HTTPException - значит наша, файл слишком большой
                raise e

            # Все остальные ошибки "оборачиваем" в 500-й статус и пробрасываем дальше
            raise HTTPException(status_code=500, detail=f"Unable to save file {filename}: {e}")

    # Формируем дату и время в utc
    upload_time = datetime.now(timezone.utc)
    expiration_time = upload_time + timedelta(hours=avail_period)

    # Коммитим в БД
    uploaded_file_db = FileModel(
        filename=filename, # Оригинальное имя
        file_id=newfile_id, # Уникальный id
        upload_time=upload_time, # Дата и время загрузки
        expiration_time=expiration_time, # Когда файл будет удален
    )
    session.add(uploaded_file_db)
    await session.commit() # только тут добавляем в бд

    return {
        "download_link": f"/download/{newfile_id}",
        "qr_code": f"/qr/{newfile_id}",
        "expired_at": expiration_time
    }

# Старая ручка "upload"
"""@router.post("/s_upload", summary="Загрузить файл")
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
            total_size = 0
            while chunk := await uploaded_file.read(chunk_size):
                # Проверка размера если обошли фронтенд
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail=f"Размер файла не должен превышать "
                                                                f"{MAX_FILE_SIZE} МБ")
                await buff_f.write(chunk)

    except Exception as e:
        if os.path.exists(newfile_path): # Удаляем недогруженный файл
            os.remove(newfile_path)

        if isinstance(e, HTTPException): # Если ошибка - HTTPException - значит наша, файл слишком большой
            raise e

        # Все остальные ошибки "оборачиваем" в 500-й статус и пробрасываем дальше
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
        "qr_code": f"/qr/{newfile_id}",
        "expired_at": expiration_time
    }"""