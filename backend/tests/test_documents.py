"""API tests against a real Postgres. Every test prepares its own data."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx import Response

# Content carries a valid PDF head — uploads must pass the magic bytes check.
PDF_HEAD = b"%PDF-1.4\n"
FIRST = PDF_HEAD + b"A" * 1000
SECOND = PDF_HEAD + b"B" * 2000

Upload = Callable[..., Response]


def _upload_doc(
    upload: Upload,
    title: str = "Contract",
    number: str = "DOG-2026/01",
    content: bytes = FIRST,
    filename: str = "doc.pdf",
) -> Response:
    return upload(
        "/api/v1/documents/upload", filename, content, title=title, document_number=number
    )


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_creates_document_v1(upload: Upload) -> None:
    r = _upload_doc(upload)
    assert r.status_code == 201
    data = r.json()
    assert data["document"]["document_number"] == "DOG-2026/01"
    assert data["version"]["version_number"] == 1
    assert data["deduplicated"] is False
    assert data["bytes_saved"] == 0


def test_upload_dedup_reuses_stored_file(client: TestClient, upload: Upload) -> None:
    first = _upload_doc(upload).json()
    r = upload("/api/v1/documents/upload", "copy.pdf", FIRST, title="Copy of contract")
    data = r.json()
    assert data["deduplicated"] is True
    assert data["bytes_saved"] == len(FIRST)
    detail = client.get(f"/api/v1/documents/{first['document']['id']}").json()
    assert data["version"]["sha256_hash"] == detail["versions"][0]["sha256_hash"]


def test_add_version_increments_number(upload: Upload) -> None:
    _upload_doc(upload)
    r = upload("/api/v1/documents/1/versions", "doc_v2.pdf", SECOND, comment="Legal review fixes")
    data = r.json()
    assert r.status_code == 201
    assert data["version"]["version_number"] == 2
    assert data["deduplicated"] is False


def test_add_version_dedup_inside_same_document(upload: Upload) -> None:
    _upload_doc(upload)
    upload("/api/v1/documents/1/versions", "doc_v2.pdf", SECOND)
    r = upload("/api/v1/documents/1/versions", "copy_v2.pdf", SECOND)
    data = r.json()
    assert data["deduplicated"] is True
    assert data["bytes_saved"] == len(SECOND)
    assert data["version"]["version_number"] == 3


def test_list_pagination_and_soft_delete(client: TestClient, upload: Upload) -> None:
    _upload_doc(upload, title="Doc one")
    _upload_doc(upload, title="Doc two", content=SECOND)
    assert len(client.get("/api/v1/documents").json()["documents"]) == 2
    # pagination: non-default params bypass the cache and slice the list
    assert len(client.get("/api/v1/documents", params={"limit": 1}).json()["documents"]) == 1

    assert client.delete("/api/v1/documents/2").json() == {"status": "archived"}
    assert len(client.get("/api/v1/documents").json()["documents"]) == 1
    deleted = client.get("/api/v1/documents", params={"include_deleted": True}).json()
    assert len(deleted["documents"]) == 2
    # versions of an archived document are not accepted
    r = client.post(
        "/api/v1/documents/2/versions", files={"file": ("x.pdf", b"X", "application/pdf")}
    )
    assert r.status_code == 404


def test_document_detail_full_history(client: TestClient, upload: Upload) -> None:
    _upload_doc(upload)
    upload("/api/v1/documents/1/versions", "doc_v2.pdf", SECOND)
    upload("/api/v1/documents/1/versions", "doc_v3.pdf", PDF_HEAD + b"C" * 500)
    detail = client.get("/api/v1/documents/1").json()
    assert [v["version_number"] for v in detail["versions"]] == [3, 2, 1]


def test_download(client: TestClient, upload: Upload) -> None:
    _upload_doc(upload)
    upload("/api/v1/documents/1/versions", "doc_v2.pdf", SECOND)
    r = client.get("/api/v1/documents/1/versions/2/download")
    assert r.status_code == 200
    assert r.content == SECOND
    assert r.headers["content-disposition"].startswith("attachment")


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/documents/999").status_code == 404
    assert client.get("/api/v1/documents/999/versions/1/download").status_code == 404
    assert client.delete("/api/v1/documents/999").status_code == 404


def test_stats_counts_deduplicated_correctly(client: TestClient, upload: Upload) -> None:
    _upload_doc(upload)
    _upload_doc(upload, title="Copy", content=FIRST)  # dedup
    upload("/api/v1/documents/1/versions", "doc_v2.pdf", SECOND)
    upload("/api/v1/documents/1/versions", "copy_v2.pdf", SECOND)  # dedup
    r = client.get("/api/v1/stats")
    # logical: FIRST + FIRST + SECOND + SECOND; physical: FIRST + SECOND
    logical = 2 * len(FIRST) + 2 * len(SECOND)
    physical = len(FIRST) + len(SECOND)
    assert r.json() == {
        "logical_bytes": logical,
        "physical_bytes": physical,
        "saved_bytes": logical - physical,
    }
