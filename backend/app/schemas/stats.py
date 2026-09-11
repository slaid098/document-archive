"""Response schemas for the archive stats API."""

from pydantic import BaseModel


class ArchiveStats(BaseModel):
    """Byte totals behind the stats endpoint: logical, physical and saved by dedup."""

    logical_bytes: int
    physical_bytes: int
    saved_bytes: int
