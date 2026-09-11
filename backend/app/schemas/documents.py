"""Request and response schemas for the documents API."""

from pydantic import BaseModel, Field


class VersionRead(BaseModel):
    """Single stored version of a document as returned by the API."""

    id: int
    version_number: int
    file_name: str
    file_size: int
    sha256_hash: str
    comment: str | None
    created_at: str
    download_url: str


class DocumentRead(BaseModel):
    """Document summary row used in list and upload responses."""

    id: int
    title: str
    document_number: str
    is_deleted: bool
    created_at: str
    updated_at: str
    version_count: int
    current_version: VersionRead | None


class DocumentDetail(DocumentRead):
    """Document summary plus the full list of its versions."""

    versions: list[VersionRead]


class UploadResponse(BaseModel):
    """Result of creating a document with its first version."""

    document: DocumentRead | None = None
    version: VersionRead
    deduplicated: bool
    bytes_saved: int


class VersionUploadResponse(BaseModel):
    """Result of adding a version to an existing document."""

    version: VersionRead
    deduplicated: bool
    bytes_saved: int


class DocumentsList(BaseModel):
    """Paginated page of documents plus whether it came from the cache."""

    documents: list[DocumentRead]
    cached: bool


class DocumentListParams(BaseModel):
    """Pagination bounds accepted by the list endpoint."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
