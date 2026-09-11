"""Cache zone: Redis cache-aside for the active documents list."""

import redis.asyncio as aioredis
from loguru import logger
from pydantic import TypeAdapter, ValidationError

from app.config import settings
from app.schemas.documents import DocumentRead

_DOCUMENTS = TypeAdapter(list[DocumentRead])


class Cache:
    """Holds the Redis client, the cache key and the TTL."""

    def __init__(self, url: str, key: str, ttl: int) -> None:
        self._key = key
        self._ttl = ttl
        self._client = None
        self._log = logger.bind(cache_key=key)
        if url:
            self._client = aioredis.from_url(url, decode_responses=True)

    async def get_documents(self) -> list[DocumentRead] | None:
        if self._client is None:
            return None
        if cached := await self._client.get(self._key):
            try:
                self._log.info("cache hit")
                return _DOCUMENTS.validate_json(cached)
            except ValidationError:
                # Schema changed or payload corrupted: treat as a miss, not a 500.
                self._log.warning("stale cached payload, invalidating")
                await self.invalidate()
        self._log.info("cache miss")
        return None

    async def put_documents(self, documents: list[DocumentRead]) -> None:
        if self._client is not None:
            await self._client.set(self._key, _DOCUMENTS.dump_json(documents), ex=self._ttl)

    async def invalidate(self) -> None:
        if self._client is not None:
            await self._client.delete(self._key)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


cache = Cache(settings.redis_url, settings.cache_key, settings.cache_ttl)
