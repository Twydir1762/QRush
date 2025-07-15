from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from fastapi import Depends

from typing import Annotated
from pathlib import Path

from app.models import Base

# ====== Работа с бд ======

engine = create_async_engine('sqlite+aiosqlite:///files_metadata.db')

new_session = async_sessionmaker(engine, expire_on_commit=False)

# Генератор сессий
async def get_session():
    async with new_session() as session:
        yield session

# Создать файл БД если его нет
async def setup_database():
    root_folder = Path(__file__).resolve().parent.parent.parent
    database_file = root_folder / "files_metadata.db"
    if not database_file.exists():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

SessionDep = Annotated[AsyncSession, Depends(get_session)]



