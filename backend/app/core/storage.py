import os
import uuid

from fastapi import HTTPException, UploadFile

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


MAX_IMAGE_BYTES = 4 * 1024 * 1024


def image_mime_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP image.")


def save_image(file: UploadFile) -> str:
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Images must be 4 MiB or smaller.")
    mime = image_mime_type(data)
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[mime]
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as destination:
        destination.write(data)

    return file_path


def read_image(image_url: str) -> bytes:
    with open(image_url, "rb") as source:
        return source.read()
