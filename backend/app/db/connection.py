"""Single source of the Tortoise ORM connection config."""

from app.config import settings

TORTOISE_ORM_CONFIG = {
    "connections": {"default": settings.database_url},
    "apps": {"models": {"models": ["app.db.models"], "default_connection": "default"}},
}
