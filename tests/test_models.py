import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from app.database.models import FileModel, FileContent

@pytest.mark.asyncio
async def test_file_model(test_session):
    now = datetime.now(timezone.utc)

    # Файл (архив/одиночный)
    file = FileModel(
        file_id='1234567',
        filename='test_file',
        size=5120,
        upload_time=now,
        expiration_time=now + timedelta(hours=1),
    )

    # Содержимое (content)
    file.content.append(
        FileContent(orig_name='test_file_content', size=1024)
    )

    test_session.add(file)
    await test_session.commit()

    res = await test_session.execute(
        select(FileModel).where(FileModel.file_id == '1234567')
    )
    db_file = res.scalar_one()

    assert len(db_file.content) == 1
    assert db_file.content[0].orig_name == 'test_file_content'

@pytest.mark.asyncio
async def test_unique_constrains(test_session):
    now = datetime.now(timezone.utc)

    file1 = FileModel(
        file_id='1234',
        filename='test_file_1',
        size=1024,
        upload_time=now,
        expiration_time=now + timedelta(hours=1),
    )

    test_session.add(file1)
    await test_session.commit()

    file2 = FileModel(
        file_id='1234',
        filename='test_file_2',
        size=1024,
        upload_time=now,
        expiration_time=now + timedelta(hours=1),
    )

    test_session.add(file2)

    # ошибка - 2 одинаковых id
    with pytest.raises(IntegrityError):
        await test_session.commit()

@pytest.mark.asyncio
async def test_cascade_del(test_session):
    now = datetime.now(timezone.utc)

    file = FileModel(
        file_id='1234',
        filename='test_file',
        size=1024,
        upload_time=now,
        expiration_time=now + timedelta(hours=1),
    )

    file.content.append(FileContent(orig_name='test_file_content', size=512))

    test_session.add(file)
    await test_session.commit()

    # Дочерняя таблица (контент) имеет 1 запись (test_file_content)
    content_res = await test_session.execute(select(FileContent))
    assert len(content_res.scalars().all()) == 1

    # Удаление родительской записи (test_file)
    await test_session.delete(file)
    await test_session.commit()

    # Дочерняя таблица пуста
    content_res = await test_session.execute(select(FileContent))
    assert len(content_res.scalars().all()) == 0
