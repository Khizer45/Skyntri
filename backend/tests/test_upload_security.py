from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from tests.helpers import make_skin_closeup, to_bytes
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
            "analyses",
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
            "analyses",
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

@pytest.fixture(autouse=True)
def _private_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def test_spoofed_mime_type_is_rejected():
    # Text content claiming to be a JPEG must fail decoding.
    upload = create_upload_file("photo.jpg", b"not really an image" * 20, "image/jpeg")
    with pytest.raises(Exception) as exc_info:
        save_upload(upload, "analyses")
    assert exc_info.value.status_code == 400


def test_corrupt_image_is_rejected():
    data = to_bytes(make_skin_closeup())
    upload = create_upload_file("photo.jpg", data[: len(data) // 3], "image/jpeg")
    with pytest.raises(Exception) as exc_info:
        save_upload(upload, "analyses")
    assert exc_info.value.status_code == 400


def test_gif_and_svg_are_rejected():
    from PIL import Image

    gif = to_bytes(Image.new("RGB", (200, 200), (200, 150, 120)), "GIF")
    for name, content, ctype in [
        ("a.gif", gif, "image/gif"),
        ("a.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml"),
        ("a.png", gif, "image/png"),  # GIF bytes disguised as PNG
    ]:
        with pytest.raises(Exception) as exc_info:
            save_upload(create_upload_file(name, content, ctype), "analyses")
        assert exc_info.value.status_code == 400


def test_huge_dimensions_are_rejected(monkeypatch):
    from PIL import Image

    monkeypatch.setattr(settings, "max_image_side", 1000)
    big = to_bytes(Image.new("RGB", (1200, 300), (200, 150, 120)), "PNG")
    with pytest.raises(Exception) as exc_info:
        save_upload(create_upload_file("big.png", big, "image/png"), "analyses")
    assert exc_info.value.status_code == 400


def test_valid_image_gets_random_server_name_and_real_extension():
    # PNG bytes uploaded with a misleading filename keep a .png extension.
    data = to_bytes(make_skin_closeup(), "PNG")
    url = save_upload(create_upload_file("../../evil.jpg.exe", data, "image/png"), "analyses")

    assert url.startswith("/uploads/analyses/")
    assert url.endswith(".png")
    assert "evil" not in url
    stored = settings.upload_path / "analyses" / url.rsplit("/", 1)[1]
    assert stored.exists()
    # No temporary files are left behind.
    assert not [p for p in stored.parent.iterdir() if p.name.startswith(".tmp-")]
