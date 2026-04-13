from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, Annotated
from datetime import datetime

class FileBase(BaseModel):
    filename: str
    size: int

class FileContentResponse(BaseModel):
    orig_name: str
    size: int

    model_config = ConfigDict(from_attributes=True)

class FileDataResponse(FileBase):
    upload_time: datetime
    expiration_time: datetime
    content: list[FileContentResponse]

    model_config = ConfigDict(from_attributes=True)

class FileUploadResponse(BaseModel):
    download_link: str
    qr_code: str
    expired_at: datetime
    content: list[FileContentResponse]

    model_config = ConfigDict(from_attributes=True)
