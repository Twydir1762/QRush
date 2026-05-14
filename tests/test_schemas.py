import pytest
from pydantic import ValidationError

from app.database.schemas import FileContentResponse, FileUploadResponse
from datetime import datetime

""" Проверка валидации корректных данных """
# FileContentResponse
def test_file_content_valid():
    data = {"orig_name": "testfile.txt", "size": 1024}

    schema = FileContentResponse(**data)
    assert schema.orig_name == "testfile.txt"
    assert schema.size == 1024

# FileUploadResponse
def test_file_upload_valid():
    content_data = {"orig_name": "testfile.txt", "size": 1024}
    data = {
        "download_link": "test_url/test_content",
        "qr_code": "qr/test_content",
        "expired_at": datetime.now(),
        "content": [FileContentResponse(**content_data)]
    }

    schema = FileUploadResponse(**data)

    assert schema.content[0].orig_name == "testfile.txt"
    assert schema.download_link == data["download_link"]
    assert schema.qr_code == data["qr_code"]
    assert schema.expired_at == data["expired_at"]

""" Проверка валидации некорректных данных """
# FileContentResponse
@pytest.mark.parametrize(
    "data", [{"orig_name": "testfile.txt", "size": "очень много"}, {"orig_name": None, "size": 1024}]
)
def test_file_content_invalid(data):
    with pytest.raises(ValidationError):
        FileContentResponse(**data)

# FileUploadResponse
@pytest.mark.parametrize(
    "data",
    [
        # size у контента равен None
        {
            "download_link": "http://test/123",
            "qr_code": "http://test/qr/123",
            "expired_at": datetime.now(),
            "content": [{"orig_name": "file.txt", "size": None}]
        },
        # download_link равен None
        {
            "download_link": None,
            "qr_code": "http://test/qr/123",
            "expired_at": datetime.now(),
            "content": [{"orig_name": "file.txt", "size": 1024}]
        },
        # отсутствует expired_at
        {
            "download_link": "http://test/123",
            "qr_code": "http://test/qr/123",
            "content": [{"orig_name": "file.txt", "size": 1024}]
        },
    ]
)
def test_file_upload_invalid(data):
    with pytest.raises(ValidationError):
        FileContentResponse(**data)

