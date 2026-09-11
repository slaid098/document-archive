"""Upload validation: extension whitelist, magic bytes, size limit, text decoding."""

from collections.abc import Callable

from app.config import settings
from fastapi.testclient import TestClient
from httpx import Response

Upload = Callable[..., Response]

PDF_HEAD = b"%PDF-1.4\n"
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04"


def test_rejects_disallowed_extension(upload: Upload) -> None:
    r = upload("/api/v1/documents/upload", "setup.exe", EXE, title="X")
    assert r.status_code == 415
    assert "Разрешены" in r.json()["detail"]


def test_rejects_renamed_executable(upload: Upload) -> None:
    # extension says pdf, magic bytes say MZ executable
    r = upload("/api/v1/documents/upload", "invoice.pdf", EXE + b"Z" * 500, title="X")
    assert r.status_code == 415


def test_rejects_content_type_mismatch(client: TestClient) -> None:
    files = {"file": ("doc.pdf", PDF_HEAD + b"body", "application/x-msdownload")}
    r = client.post("/api/v1/documents/upload", files=files, data={"title": "X"})
    assert r.status_code == 415


def test_rejects_oversized_file(client: TestClient, upload: Upload, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    r = upload("/api/v1/documents/upload", "big.pdf", PDF_HEAD + b"Z" * 1000, title="X")
    assert r.status_code == 413


def test_rejects_invalid_utf8_text(upload: Upload) -> None:
    r = upload("/api/v1/documents/upload", "notes.md", b"# Title\n\xff\xfe", title="X")
    assert r.status_code == 415


def test_accepts_text_formats(client: TestClient, upload: Upload) -> None:
    md = "# План\n\n- пункт один\n- пункт два\n".encode()
    r = upload("/api/v1/documents/upload", "notes.md", md, title="X")
    assert r.status_code == 201
    r = upload("/api/v1/documents/upload", "dump.txt", "просто текст".encode(), title="Y")
    assert r.status_code == 201
    assert len(client.get("/api/v1/documents").json()["documents"]) == 2


def test_accepts_ooxml_and_images(upload: Upload) -> None:
    r = upload("/api/v1/documents/upload", "table.xlsx", b"PK\x03\x04" + b"Z" * 100, title="X")
    assert r.status_code == 201
    r = upload("/api/v1/documents/upload", "scan.png", b"\x89PNG\r\n\x1a\n" + b"Z" * 100, title="Y")
    assert r.status_code == 201


def test_rejected_upload_leaves_no_document(client: TestClient, upload: Upload) -> None:
    upload("/api/v1/documents/upload", "setup.exe", EXE, title="X")
    assert client.get("/api/v1/documents").json()["documents"] == []
