# Document Archive

Demo project: a document archive — upload with SHA-256 deduplication, versioning, Redis cache-aside, soft delete.

## Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, Tortoise ORM · PostgreSQL 15 · Redis 7
- Frontend: React 19 + TypeScript + Vite, Tailwind CSS
- Infra: Docker Compose (nginx proxies `/api`), uv (deps pinned in `uv.lock`), pytest + ruff

## Run

```bash
docker compose up --build
```

UI: http://localhost:80 · Swagger: http://localhost:8000/docs

On the server CI deploys via SSH after a green push to `main`: images are pulled from GHCR, then `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` (app on host port 8080).

Local dev:

```bash
cd backend && uv sync && uv run uvicorn main:app --reload
cd ../frontend && npm install && npm run dev   # vite proxies /api to :8000
```

## Tests

```bash
docker compose -f docker-compose.test.yml up -d --wait
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
```

CI (GitHub Actions): ruff + pytest + frontend build; on `main` images are pushed to GHCR and the server pulls them.

## Architecture

```
Browser ──▶ nginx (:80) ──▶ FastAPI (:8000) ──▶ app_data/storage/{sha256}.ext
                                │      │
                             Redis   PostgreSQL
```

- Upload validation: whitelist (`.pdf`, `.docx/.xlsx/.pptx`, `.txt/.md`, `.jpg/.png`) + magic bytes + UTF-8 check + 25 MB limit (`MAX_UPLOAD_BYTES`) — enforced in the same streaming pass as the SHA-256 hashing.
- Deduplication: identical content is stored once (`app_data/storage/{sha256}.ext`); new versions reuse the stored file.
- Cache: Redis cache-aside for the default document list (TTL 60 s), invalidated on every mutation.
- The DB schema is generated on startup.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/documents/upload` | New document: multipart (`file`, `title`, `document_number?`) -> 201 + dedup status |
| POST | `/api/v1/documents/{id}/versions` | New version: multipart (`file`, `comment?`) -> 201 |
| GET | `/api/v1/documents` | List (`limit`, `offset`, `include_deleted?`), served from Redis |
| GET | `/api/v1/documents/{id}` | Card with full version history |
| GET | `/api/v1/documents/{id}/versions/{v}/download` | File via `FileResponse` |
| DELETE | `/api/v1/documents/{id}` | Soft delete -> `{"status": "archived"}` |
| GET | `/api/v1/stats` | Archive volume and saved space |