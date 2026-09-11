"""Application settings, loaded from environment variables.

Env vars are read once at import; `.env` is supported for local runs.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgres://archive:archive@db:5432/archive"
    # Empty string disables the cache (used by tests).
    redis_url: str = ""
    storage_dir: str = "/app/app_data/storage"

    cache_key: str = "archive:documents:active"
    cache_ttl: int = 60
    chunk_size: int = 1024 * 1024  # 1 MB
    # Uploads above this size are rejected during streaming (413).
    max_upload_bytes: int = 25 * 1024 * 1024

    # Root level for the whole app; unknown values fail fast at startup.
    log_level: str = "INFO"


settings = Settings()
