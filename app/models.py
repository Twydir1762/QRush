from sqlalchemy import DateTime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase

from datetime import datetime


# ====== Модели для алхимии ======

class Base(DeclarativeBase):
    pass

class FileModel(Base):
    __tablename__ = 'files_metadata'

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(unique=True, index=True)
    filename: Mapped[str] = mapped_column()
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiration_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)