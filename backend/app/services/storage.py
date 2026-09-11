"""Storage zone: streaming SHA-256 and content-addressed file storage with dedup."""

import hashlib
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status
from loguru import logger

from app.config import settings
from app.db.models import DocumentVersion
from app.schemas.storage import StoredFile
from app.schemas.validation import TypeSpec
from app.services import validation


async def inspect_upload(upload: UploadFile, spec: TypeSpec) -> tuple[str, int]:
    """One streaming pass: hash the upload while enforcing the size limit,
    the head signature and (for text types) UTF-8 decoding. Returns (sha256, size).
    """
    hasher = hashlib.sha256()
    text_guard = validation.make_text_guard() if spec.text else None
    head = b""
    size = 0
    await upload.seek(0)
    while chunk := await upload.read(settings.chunk_size):
        size += len(chunk)
        _enforce_size_limit(size)
        if len(head) < validation.HEAD_LEN:
            head = _extend_head(head, chunk)
            validation.verify_head(spec, head)  # early reject, don't read on
        if text_guard is not None:
            text_guard(chunk)
        hasher.update(chunk)
    if text_guard is not None:
        text_guard(b"", final=True)  # flush catches a truncated tail
    validation.verify_head(spec, head)  # covers files shorter than HEAD_LEN
    return hasher.hexdigest(), size


def _enforce_size_limit(size: int) -> None:
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"файл слишком большой: лимит {settings.max_upload_bytes} байт",
        )


def _extend_head(head: bytes, chunk: bytes) -> bytes:
    """Grow the head buffer up to HEAD_LEN bytes from the current chunk."""
    return head + chunk[: validation.HEAD_LEN - len(head)]


async def store_or_dedupe(upload: UploadFile, sha256: str) -> StoredFile:
    """Write the file unless an identical hash already exists (reuse the stored path)."""
    await upload.seek(0)  # the stream sits at EOF after hashing
    existing = await DocumentVersion.filter(sha256_hash=sha256).first()
    if existing:
        logger.bind(sha256=sha256, saved_bytes=existing.file_size).info("dedup hit")
        return StoredFile(existing.file_path, existing.file_size, True)

    suffix = Path(upload.filename or "").suffix[:10]  # guard against junk in names
    path = str(Path(settings.storage_dir) / f"{sha256}{suffix}")
    size = 0
    async with aiofiles.open(path, "wb") as out:
        while chunk := await upload.read(settings.chunk_size):
            await out.write(chunk)
            size += len(chunk)
    logger.bind(sha256=sha256, size=size).info("stored file")
    return StoredFile(path, size, deduplicated=False)
