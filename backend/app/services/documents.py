"""Documents zone: documents, versions, listing, download, soft delete."""

from typing import Any

from fastapi import HTTPException, UploadFile, status
from loguru import logger

from app.db.models import Document, DocumentVersion
from app.schemas.documents import (
    DocumentDetail,
    DocumentListParams,
    DocumentRead,
    DocumentsList,
    UploadResponse,
    VersionRead,
    VersionUploadResponse,
)
from app.services import validation
from app.services.cache import cache
from app.services.storage import inspect_upload, store_or_dedupe

# Only the default slice of the active list is cached; any other limit/offset
# goes past the cache. Deliberate trade-off, documented in the README.
_DEFAULT_PARAMS = DocumentListParams()


def _to_version_read(version: DocumentVersion) -> VersionRead:
    return VersionRead(
        id=version.id,
        version_number=version.version_number,
        file_name=version.file_name,
        file_size=version.file_size,
        sha256_hash=version.sha256_hash,
        comment=version.comment,
        created_at=version.created_at.isoformat(),
        download_url=(
            f"/api/v1/documents/{version.document_id}/versions/{version.version_number}/download"
        ),
    )


def _to_document_read(document: Document) -> DocumentRead:
    versions = sorted(document.versions, key=lambda v: -v.version_number)
    latest = versions[0] if versions else None
    return DocumentRead(
        id=document.id,
        title=document.title,
        document_number=document.document_number,
        is_deleted=document.is_deleted,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        version_count=len(versions),
        current_version=_to_version_read(latest) if latest else None,
    )


def _to_document_detail(document: Document) -> DocumentDetail:
    latest_first = sorted(document.versions, key=lambda v: -v.version_number)
    return DocumentDetail(
        **_to_document_read(document).model_dump(),
        versions=[_to_version_read(v) for v in latest_first],
    )


async def upload_document(
    title: str,
    document_number: str | None,
    upload: UploadFile,
) -> UploadResponse:
    sha256 = await _validate_and_hash(upload)  # rejects before a document row exists
    document = await Document.create(title=title, document_number=document_number or "")
    version, deduplicated, bytes_saved = await _create_version(document, upload, None, sha256)
    await document.fetch_related("versions")
    await cache.invalidate()
    return UploadResponse(
        document=_to_document_read(document),
        version=_to_version_read(version),
        deduplicated=deduplicated,
        bytes_saved=bytes_saved,
    )


async def add_version(
    document_id: int,
    comment: str | None,
    upload: UploadFile,
) -> VersionUploadResponse:
    document = await _get_document_or_404(document_id, only_active=True)
    sha256 = await _validate_and_hash(upload)
    version, deduplicated, bytes_saved = await _create_version(document, upload, comment, sha256)
    await document.save()  # auto_now bumps updated_at
    await cache.invalidate()
    return VersionUploadResponse(
        version=_to_version_read(version),
        deduplicated=deduplicated,
        bytes_saved=bytes_saved,
    )


async def list_documents(
    params: DocumentListParams,
    include_deleted: bool = False,
) -> DocumentsList:
    default_slice = params.model_dump() == _DEFAULT_PARAMS.model_dump()
    if not include_deleted and default_slice:
        if (cached := await cache.get_documents()) is not None:
            return DocumentsList(documents=cached, cached=True)

    query = Document.all().prefetch_related("versions").offset(params.offset).limit(params.limit)
    if not include_deleted:
        query = query.filter(is_deleted=False)
    documents = [_to_document_read(doc) for doc in await query]

    if not include_deleted and default_slice:
        await cache.put_documents(documents)
    return DocumentsList(documents=documents, cached=False)


async def get_document_detail(document_id: int) -> DocumentDetail:
    document = await _get_document_or_404(document_id)
    await document.fetch_related("versions")
    return _to_document_detail(document)


async def get_version_file_path(document_id: int, version_number: int) -> tuple[str, str]:
    """Returns (file_path, file_name) of a stored version."""
    version = await DocumentVersion.get_or_none(
        document_id=document_id,
        version_number=version_number,
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "version or file not found")
    return version.file_path, version.file_name


async def archive_document(document_id: int) -> None:
    document = await _get_document_or_404(document_id, only_active=True)
    document.is_deleted = True
    await document.save()
    await cache.invalidate()
    logger.bind(document_id=document_id).info("document archived")


async def _get_document_or_404(
    document_id: int,
    only_active: bool = False,
) -> Document:
    filters: dict[str, Any] = {"id": document_id}
    if only_active:
        filters["is_deleted"] = False
    document = await Document.get_or_none(**filters)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    return document


async def _validate_and_hash(upload: UploadFile) -> str:
    """Extension + content type checks, then one streaming pass that verifies
    the head signature, the size limit and the sha256. Returns the sha256."""
    spec = validation.verify_extension(upload.filename or "")
    validation.verify_content_type(spec, upload.content_type)
    sha256, _ = await inspect_upload(upload, spec)
    return sha256


async def _create_version(
    document: Document,
    upload: UploadFile,
    comment: str | None,
    sha256: str,
) -> tuple[DocumentVersion, bool, int]:
    """Store/dedupe -> version row.

    Returns (version, deduplicated, bytes_saved).
    """
    stored = await store_or_dedupe(upload, sha256)

    last_version = (
        await DocumentVersion.filter(document=document).order_by("-version_number").first()
    )
    version = await DocumentVersion.create(
        document=document,
        version_number=(last_version.version_number + 1) if last_version else 1,
        file_name=upload.filename or "unnamed",
        file_path=stored.path,
        file_size=stored.size,
        sha256_hash=sha256,
        comment=comment,
    )
    return version, stored.deduplicated, stored.size if stored.deduplicated else 0
