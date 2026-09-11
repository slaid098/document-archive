"""Documents API routes (v1). Handlers are thin: unpack payload -> await service."""

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from app.schemas.documents import (
    DocumentDetail,
    DocumentListParams,
    DocumentsList,
    UploadResponse,
    VersionUploadResponse,
)
from app.services import documents as documents_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    status_code=201,
    summary="Upload a new document",
)
async def upload_document(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    document_number: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    return await documents_service.upload_document(title, document_number, file)


@router.post(
    "/{document_id}/versions",
    status_code=201,
    summary="Add a new version",
)
async def upload_new_version(
    document_id: int,
    file: Annotated[UploadFile, File()],
    comment: Annotated[str | None, Form()] = None,
) -> VersionUploadResponse:
    return await documents_service.add_version(document_id, comment, file)


@router.get("", summary="List documents")
async def list_documents(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_deleted: Annotated[bool, Query()] = False,
) -> DocumentsList:
    return await documents_service.list_documents(
        DocumentListParams(limit=limit, offset=offset),
        include_deleted,
    )


@router.get(
    "/{document_id}",
    summary="Document detail with full version history",
)
async def get_document(document_id: int) -> DocumentDetail:
    return await documents_service.get_document_detail(document_id)


@router.get(
    "/{document_id}/versions/{version_number}/download",
    summary="Download a stored version",
)
async def download_version(document_id: int, version_number: int) -> FileResponse:
    file_path, file_name = await documents_service.get_version_file_path(
        document_id,
        version_number,
    )
    return FileResponse(file_path, filename=file_name, media_type="application/octet-stream")


@router.delete("/{document_id}", summary="Soft delete (archive) a document")
async def delete_document(document_id: int) -> dict[str, str]:
    await documents_service.archive_document(document_id)
    return {"status": "archived"}
