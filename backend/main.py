"""Thin entrypoint: app wiring only. Routes live in api, business logic in services."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.api import api_router
from app.config import settings, setup_logging
from app.db.connection import TORTOISE_ORM_CONFIG
from app.services.cache import cache
from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await _enshure_storage_path()

    async with RegisterTortoise(
        app=fastapi_app,
        config=TORTOISE_ORM_CONFIG,
        generate_schemas=True,  # dev; production uses Aerich
    ):
        yield
    await cache.close()


async def _enshure_storage_path() -> None:
    path = Path(settings.storage_dir)
    await asyncio.to_thread(path.mkdir, exist_ok=True)


app = FastAPI(title="Document Archive", version="1.0.0", lifespan=lifespan)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
