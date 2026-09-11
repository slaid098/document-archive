"""Stats zone: archive volume and saved space."""

from tortoise.functions import Sum

from app.db.models import DocumentVersion
from app.schemas.stats import ArchiveStats


async def archive_stats() -> ArchiveStats:
    """Logical volume (all versions), physical (one file per hash), saved."""
    logical_row = await DocumentVersion.annotate(logical=Sum("file_size")).values("logical")
    logical = logical_row[0]["logical"] or 0
    # Same hash always has the same file_size, so distinct pairs == unique files
    physical_rows = await DocumentVersion.all().distinct().values_list("sha256_hash", "file_size")
    physical = sum(size for _, size in physical_rows)
    return ArchiveStats(
        logical_bytes=logical,
        physical_bytes=physical,
        saved_bytes=logical - physical,
    )
