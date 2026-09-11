"""Test setup: dedicated Postgres (docker-compose.test.yml), storage under app_data/tests."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.environ.setdefault(
    "DATABASE_URL",
    "postgres://archive_test:archive_test@localhost:5433/archive_test",
)
os.environ["REDIS_URL"] = ""  # cache disabled in tests
os.environ["STORAGE_DIR"] = str(BACKEND_DIR.parent / "app_data" / "tests" / "storage")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import Response  # noqa: E402
from main import app  # noqa: E402
from tortoise import Tortoise  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client: TestClient) -> None:
    """Every test starts with empty tables — tests are order-independent.

    The truncate runs on the app's own loop via the TestClient portal:
    the asyncpg pool is bound to that loop.
    """

    async def _truncate() -> None:
        conn = Tortoise.get_connection("default")
        await conn.execute_script("TRUNCATE document_versions, documents RESTART IDENTITY CASCADE")

    # The portal is present for the whole `with TestClient(...)` block.
    assert client.portal is not None
    client.portal.call(_truncate)


MIME_BY_EXT: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


@pytest.fixture
def upload(client: TestClient) -> Callable[..., Response]:
    def _upload(url: str, filename: str, content: bytes, **fields: str) -> Response:
        ext = Path(filename).suffix.lower()
        files = {"file": (filename, content, MIME_BY_EXT.get(ext, "application/octet-stream"))}
        return client.post(url, files=files, data=fields)

    return _upload
