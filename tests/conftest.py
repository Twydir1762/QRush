import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database.models import Base
from app.database import db

# БД в оперативной памяти (без сохранения)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(autouse=True)
async def test_session():
    # До теста
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}) # Тестовый движок

    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Тестовая фабрика сессий
    async_test_session = async_sessionmaker(engine, expire_on_commit=False)

    original_session = db.new_session
    db.new_session = async_test_session

    session = async_test_session()  # Новая тестовая сессия

    yield session # Тест

    db.new_session = original_session # Восстановление оригинальной сессии
    await session.close()

    # После теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Очистка тестовой БД

    await engine.dispose()

# Подменяет папку uploads на временную
@pytest.fixture
def mock_uploads(tmp_path, monkeypatch):
    # Создание временной папки "uploads"
    fake_uploads = tmp_path / "uploads"
    fake_uploads.mkdir()

    # Подмена реальной папки uploads на временную
    monkeypatch.setattr("app.config.UPLOADS_DIR", fake_uploads)
    monkeypatch.setattr("app.utils.UPLOADS_DIR", fake_uploads)
    monkeypatch.setattr("app.api.files.UPLOADS_DIR", fake_uploads)

    return fake_uploads

