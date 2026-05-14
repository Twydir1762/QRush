import pytest
from datetime import datetime, timedelta, timezone
import os

from app.utils import cleaning
from app.database.models import FileModel

# Функция удаления файлов с истекшим сроком хранения
@pytest.mark.asyncio
async def test_cleaning_expired_files(mock_uploads, test_session):
    now = datetime.now(timezone.utc)

    # Создание файлов с истекшим сроком хранения
    # Запись на диск
    for file_id in range(3):
        file_path = os.path.join(mock_uploads, f"{file_id}_test_expired.txt")
        with open(file_path, "wb") as f:
            f.write(b"HelloWorldExpired")

        # Запись в БД
        file = FileModel(
            file_id=file_id,
            filename='test_expired.txt',
            size=50,
            upload_time=now - timedelta(hours=10),
            expiration_time=now - timedelta(hours=10 - file_id)
        )

        test_session.add(file)

    file_path = os.path.join(mock_uploads, f"1234567_fresh_file.txt")
    with open(file_path, "wb") as f:
        f.write(b"HelloWorldFresh")

    # Создание файла с актуальным сроком хранения
    file = FileModel(
        file_id=1234567,
        filename='fresh_file.txt',
        size=50,
        upload_time=now,
        expiration_time=now + timedelta(hours=12)
    )
    test_session.add(file)
    await test_session.commit()

    res = await cleaning(test_session)

    assert res["Deleted"] == '3'
    assert len(os.listdir(mock_uploads)) == 1 # Только 1 файл остался на диске