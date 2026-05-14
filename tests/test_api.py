import pytest
from httpx import AsyncClient, ASGITransport
import os

from datetime import datetime, timedelta, timezone

from app.main import app
from app.config import MAX_FILE_SIZE
from app.database.models import FileModel

""" ------------ Позитивные тесты ------------ """
# Конфиг возвращает значение
@pytest.mark.asyncio
async def test_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/config")

    assert response.json() == {"max_file_size": MAX_FILE_SIZE}

""" Загрузка файлов """
# Загрузка разного количества файлов
@pytest.mark.parametrize("files_num", [1, 3])
@pytest.mark.asyncio
async def test_upload_files_nums(files_num, mock_uploads):
    files = [("uploaded_files", (f"test_file_{i}.txt", b"1" * 100)) for i in range(1, files_num + 1)]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)

    assert res.status_code == 200
    assert len(res.json()['content']) == files_num # В архиве столько, сколько загружалось
    assert len(os.listdir(mock_uploads)) == 1 # Файл/Архив появился на диске
    # file_id корректный
    assert res.json()['download_link'].split('/')[-1] == res.json()['qr_code'].split('/')[-1]

# Загрузка файлов с разным сроком хранения
@pytest.mark.parametrize("avail_period", [1, 12, 24])
@pytest.mark.asyncio
async def test_upload_files_period(avail_period, mock_uploads):
    files = [("uploaded_files", (f"test_file.txt", b"1" * 100))]
    metadata = {"avail_period": avail_period}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)

    assert res.status_code == 200
    assert len(os.listdir(mock_uploads)) == 1  # Файл/Архив появился на диске

# Отсутствует время хранение (значение по умолчанию)
@pytest.mark.asyncio
@pytest.mark.parametrize("avail_period", [None, ""])
async def test_default_exp_time(avail_period, mock_uploads):
    files = [("uploaded_files", ("test_file.txt", b"1" * 100))]
    metadata = {"avail_period": avail_period}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        now = datetime.now(timezone.utc)
        res = await client.post("/upload", files=files, data=metadata)

    expected_time = now + timedelta(hours=1)
    expired_at = datetime.fromisoformat(res.json()['expired_at'])

    assert res.status_code == 200
    assert abs(expired_at - expected_time).total_seconds() < 10 # Запас времени на тест
    assert len(os.listdir(mock_uploads)) == 1

""" Скачивание файлов """
# Проверка страницы скачивания
@pytest.mark.asyncio
async def test_download_page_success(mock_uploads):
    # Загрузка файла
    files = [("uploaded_files", (f"test_file.txt", b"HelloWorld"))]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)
        # Скачивание файла
        download_res = await client.get(res.json()["download_link"])

    assert download_res.status_code == 200
    assert "download.js" in download_res.text

# Скачивание файла
@pytest.mark.asyncio
async def test_download_file_success(mock_uploads):
    # Загрузка файла
    files = [("uploaded_files", (f"test_file.txt", b"HelloWorld"))]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)
        # Скачивание файла
        download_res = await client.get(res.json()["download_link"] + "/file")

    assert download_res.status_code == 200
    assert download_res.content == b"HelloWorld"

""" Удаление файлов """
# Удаление существующего файла
@pytest.mark.asyncio
async def test_delete_file_success(mock_uploads):
    # Загрузка файла
    files = [("uploaded_files", (f"test_file.txt", b"HelloWorld"))]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata) # Загрузка файла
        file_id = res.json()['download_link'].split('/')[-1]
        res_check = await client.get(f"/file/{file_id}") # Проверка информации о файле из БД

        db_filename = f"{file_id}_test_file.txt"
        os_filepath = os.path.join(mock_uploads, db_filename)
        assert os.path.exists(os_filepath) # Файл существует на диске
        assert res_check.json()['filename'] == "test_file.txt" # Файл существует в БД

        res_del = await client.delete(f"/file/{file_id}")
        assert res_del.status_code == 200
        assert res_del.json() == {"Success": True}

        res_check = await client.get(f"/file/{file_id}")
        assert not os.path.exists(os_filepath)  # Файл больше не существует на диске
        assert res_check.status_code == 404 # Файл больше не существует в БД

""" Утилиты """
# Генерация QR-кода
@pytest.mark.asyncio
async def test_qr_generate_success(mock_uploads):
    # Загрузка файла
    files = [("uploaded_files", (f"test_file.txt", b"HelloWorld"))]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)
        # Генерация QR-кода
        qr_url = res.json()["qr_code"]

        # Получение изображения QR-кода
        qr_res = await client.get(qr_url)

    assert qr_res.status_code == 200
    assert qr_res.headers['content-type'] == 'image/png'

""" ------------ Негативные тесты ------------ """
""" Загрузка файлов """
# Слишком большой файл
@pytest.mark.asyncio
async def test_file_too_large(mock_uploads):
    metadata = {"avail_period": 12}
    large_content = b"0" * (MAX_FILE_SIZE + 1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = [("uploaded_files", ("large_file.txt", large_content))]
        res = await client.post("/upload", files=files, data=metadata)

    assert res.status_code == 413
    assert len(os.listdir(mock_uploads)) == 0  # Невалидный файл не загружен на диск

# Невалидное время хранение файла
@pytest.mark.asyncio
@pytest.mark.parametrize("avail_period", [0, -1, 100, "много"])
async def test_invalid_exp_time(avail_period, mock_uploads):
    metadata = {"avail_period": avail_period}
    files = [("uploaded_files", ("test_file.txt", b"1" * 100))]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata)

    assert res.status_code == 422
    assert len(os.listdir(mock_uploads)) == 0  # Невалидный файл не загружен на диск

""" Скачивание файлов """
# Проверка страницы скачивания
@pytest.mark.asyncio
async def test_download_page_not_found(mock_uploads, test_session):
    now = datetime.now(timezone.utc)

    # Создание файла с истекшим сроком хранения
    # Запись на диск
    file_id = "1234567_expired"
    file_path = os.path.join(mock_uploads, f"{file_id}_file.txt")
    with open(file_path, "wb") as f:
        f.write(b"HelloWorldExpired")

    # Запись в БД
    file = FileModel(
        file_id=file_id,
        filename='test_expired.txt',
        size=50,
        upload_time=now - timedelta(hours=4),
        expiration_time=now - timedelta(hours=3)
    )

    test_session.add(file)
    await test_session.commit()

    # Скачивание файла
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        download_res = await client.get(f"/download/{file_id}")

    assert "Файл не найден" in download_res.text

# Скачивание файла с истекшим сроком хранения
@pytest.mark.asyncio
async def test_download_invalid_file(mock_uploads, test_session):
    now = datetime.now()

    # Создание файла с истекшим сроком хранения
    # Запись на диск
    file_id = "1234567_expired"
    file_path = os.path.join(mock_uploads, f"{file_id}_file.txt")
    with open(file_path, "wb") as f:
        f.write(b"HelloWorldExpired")

    # Запись в БД
    file = FileModel(
        file_id=file_id,
        filename='test_expired.txt',
        size=50,
        upload_time=now - timedelta(hours=4),
        expiration_time=now - timedelta(hours=3)
    )

    test_session.add(file)
    await test_session.commit()

    # Скачивание файла
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        download_res = await client.get(f"/download/{file_id}/file")

    assert download_res.status_code == 404

""" Удаление файлов """
# Удаление несуществующего файла
@pytest.mark.asyncio
async def test_delete_invalid_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.delete("/file/1234567_dont_exits")

        assert res.status_code == 404

# Удаление несуществующего файла на диске при наличии записи в БД
@pytest.mark.asyncio
async def test_delete_ghost_file(mock_uploads):
    # Загрузка файла
    files = [("uploaded_files", (f"test_file.txt", b"HelloWorld"))]
    metadata = {"avail_period": 12}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/upload", files=files, data=metadata) # Загрузка файла
        file_id = res.json()['download_link'].split('/')[-1]
        res_check = await client.get(f"/file/{file_id}") # Проверка информации о файле из БД

        db_filename = f"{file_id}_test_file.txt"
        os_filepath = os.path.join(mock_uploads, db_filename)
        assert os.path.exists(os_filepath) # Файл существует на диске
        assert res_check.json()['filename'] == "test_file.txt" # Файл существует в БД

        # Удаление файла физически
        os.remove(os_filepath)

        res_del = await client.delete(f"/file/{file_id}")
        assert res_del.status_code == 404

        # Проверка удаления записи из БД
        res_check = await client.get(f"/file/{file_id}")
        assert res_check.status_code == 404

""" Утилиты """
# Генерация QR-кода с несуществующим id файла
@pytest.mark.asyncio
async def test_qr_invalid_generation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        qr_res = await client.get(f"/qr/1234567_not_exist")

    assert qr_res.status_code == 404