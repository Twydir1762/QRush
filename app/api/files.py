from fastapi import APIRouter
from fastapi import Request
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from fastapi import UploadFile, File, Form

from sqlalchemy import select
from sqlalchemy.orm import selectinload

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

from app.database.db import SessionDep
from app.database.models import FileModel, FileContent
from app.database.schemas import FileDataResponse, FileUploadResponse
from app.config import MAX_FILE_SIZE, UPLOADS_DIR
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

@router.get("/file/{file_id}", summary="Информация о файле", response_model=FileDataResponse)
async def get_file_info(file_id: str, session: SessionDep):
    query = (select(FileModel).where(FileModel.file_id == file_id).options(selectinload(FileModel.content)))
    result = await session.execute(query)
    file_data = result.scalars().first()

    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    return file_data

@router.get("/download/{file_id}/file", summary="Скачать файл")
async def download_file(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query)
    db_result = result.scalars().first()

    if not db_result or db_result.expiration_time.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="File not found")

    db_filename = str(db_result.filename)
    db_filepath = f"{file_id}_{db_filename}"
    filepath = os.path.join(UPLOADS_DIR, db_filepath)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(filepath, filename=db_filename)

@router.get("/download/{file_id}", summary="Страница скачивания файла")
async def download_page(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query)
    db_result = result.scalars().first()

    if not db_result or db_result.expiration_time.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return FileResponse("app/static/not_found.html")

    return FileResponse("app/static/download.html")

@router.get("/qr/{file_id}", summary="Генерация QR")
async def generate_qr(file_id: str, request: Request, session: SessionDep):
    # Проверка на то что file_id валиден, чтобы не генерировать невалидные QR-коды (не нагружать CPU)
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query)
    file_data = result.scalars().first()

    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    # Генерация QR
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

@router.post("/upload", summary="Загрузить файлы", response_model=FileUploadResponse)
async def upload_files(
    session: SessionDep, # В начале, чтобы fastapi не ругался
    uploaded_files: list[UploadFile] = File(...),
    avail_period: Annotated[int, Form(...), Field(ge=1, le=24)] = 1 # Сколько файл будет доступен (1-24 ч)
):
    # Генерируем уникальный id
    newfile_id = str(uuid.uuid4())
    file_size = 0

    # Дата и время в utc
    upload_time = datetime.now(timezone.utc)
    expiration_time = upload_time + timedelta(hours=avail_period)

    if len(uploaded_files) > 1:

        filename = f"uploads_{upload_time.strftime('%d_%m_%Y')}.zip"
        newfile_path = os.path.join(UPLOADS_DIR, f"{newfile_id}_{filename}")

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
                    raise HTTPException(status_code=413, detail=f"The file size must not exceed "
                                                                f"{MAX_FILE_SIZE / 1048576} MB")
                await zip_buff.write(data)
            file_size = zip_files_size
    else:
        uploaded_file = uploaded_files[0]
        # Оригинальные параметры файла
        filename = uploaded_files[0].filename
        newfile_path = os.path.join(UPLOADS_DIR, f"{newfile_id}_{filename}")
        # Сохранение файла
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

                file_size = total_size

        except Exception as e:
            if os.path.exists(newfile_path): # Удаляем недогруженный файл
                os.remove(newfile_path)

            if isinstance(e, HTTPException): # Если ошибка - HTTPException - значит наша, файл слишком большой
                raise e

            # Все остальные ошибки -> 500-й статус и проброс дальше
            raise HTTPException(status_code=500, detail=f"Unable to save file {filename}: {e}")

    # Сохранение в БД
    uploaded_file_db = FileModel(
        filename=filename, # Оригинальное имя
        file_id=newfile_id, # Уникальный id
        size=file_size, # (Общий) размер
        upload_time=upload_time, # Дата и время загрузки
        expiration_time=expiration_time, # Когда файл будет удален
    )

    # Содержимое архива (или просто файл)
    for file_content in uploaded_files:
        content_item = FileContent(
            orig_name=file_content.filename,
            size=file_content.size if file_content.size else 0
        )
        uploaded_file_db.content.append(content_item)

    session.add(uploaded_file_db)
    await session.commit() # только тут добавляем в бд

    await session.refresh(uploaded_file_db, attribute_names=['content'])

    return {
        "download_link": f"/download/{newfile_id}",
        "qr_code": f"/qr/{newfile_id}",
        "expired_at": expiration_time,
        "content": uploaded_file_db.content
    }

@router.delete("/file/{file_id}", summary="Удалить файл по id")
async def delete_file(file_id: str, session: SessionDep):
    query = select(FileModel).where(FileModel.file_id == file_id)
    result = await session.execute(query)

    db_result = result.scalars().first()

    if not db_result:
        raise HTTPException(status_code=404, detail="File not found")

    db_filename = str(db_result.filename)
    db_filepath = f"{file_id}_{db_filename}"
    filepath = os.path.join(UPLOADS_DIR, db_filepath)

    if not os.path.exists(filepath):
        # Файла нет на диске, но есть в БД - мусор
        await session.delete(db_result)
        await session.commit()
        raise HTTPException(status_code=404, detail="File not found in storage. Deleted ghosty DB entry")

    # Сначала удаляем с диска
    try:
        os.remove(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to delete file: {e}")

    # Теперь с БД
    await session.delete(db_result)
    await session.commit()

    return {"Success": True}

