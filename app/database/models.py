from sqlalchemy import DateTime, ForeignKey

from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy import BigInteger

from datetime import datetime


# ====== Модели для алхимии ======

class Base(DeclarativeBase):
    pass

class FileModel(Base):
    __tablename__ = 'files_metadata'

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(unique=True, index=True)
    filename: Mapped[str] = mapped_column()
    size: Mapped[int] = mapped_column(BigInteger, default=0) # БАЙТЫ
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiration_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    content: Mapped[list["FileContent"]] = relationship(back_populates="parent_metadata", cascade="all, delete-orphan")

class FileContent(Base):
    __tablename__ = 'files_content'

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey('files_metadata.id'))
    orig_name: Mapped[str] = mapped_column()
    size: Mapped[int] = mapped_column(BigInteger, default=0)

    parent_metadata: Mapped["FileModel"] = relationship(back_populates="content")