"""Internal DTOs returned by the storage service."""

from dataclasses import dataclass


@dataclass
class StoredFile:
    """Result of store_or_dedupe: where the content lives on disk."""

    path: str
    size: int
    deduplicated: bool
