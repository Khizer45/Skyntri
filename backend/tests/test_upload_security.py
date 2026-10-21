from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.services.uploads import (
    MAX_FILE_SIZE_BYTES,
    save_upload,
)


def create_upload_file(
    filename: str,
    content: bytes,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers(
            {
                "content-type": content_type,
            }
        ),
    )


def test_unsupported_file_type_is_rejected():
    upload = create_upload_file(
        filename="test.exe",
        content=b"fake executable content",
        content_type="application/octet-stream",
    )

    with pytest.raises(Exception) as exc_info:
        save_upload(
            upload,
            "security_test_uploads",
        )

    assert exc_info.value.status_code == 400


def test_oversized_file_is_rejected():
    # Create a file slightly larger than the 10 MB limit.
    oversized_content = b"x" * (
        MAX_FILE_SIZE_BYTES + 1
    )

    upload = create_upload_file(
        filename="large.jpg",
        content=oversized_content,
        content_type="image/jpeg",
    )

    with pytest.raises(Exception) as exc_info:
        save_upload(
            upload,
            "security_test_uploads",
        )

    assert exc_info.value.status_code == 400
    assert "10MB" in str(exc_info.value.detail)


def test_path_traversal_upload_destination_is_rejected():
    upload = create_upload_file(
        filename="test.jpg",
        content=b"fake image content",
        content_type="image/jpeg",
    )

    with pytest.raises(Exception) as exc_info:
        save_upload(
            upload,
            "../malicious",
        )

    assert exc_info.value.status_code == 400