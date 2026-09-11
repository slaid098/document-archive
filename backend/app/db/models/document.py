"""Document domain models."""

# pyright: reportIncompatibleVariableOverride=false
# Nested Tortoise Meta is the ORM convention.

from tortoise import fields
from tortoise.models import Model


class Document(Model):
    """Logical document: a title-numbered folder of immutable versions."""

    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=255, description="Document title")
    document_number = fields.CharField(
        max_length=64, description="Registration number, e.g. DOG-2026/01"
    )
    is_deleted = fields.BooleanField(default=False, description="Soft delete flag")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    versions: fields.ReverseRelation["DocumentVersion"]

    class Meta:
        table = "documents"
        ordering = ["-created_at"]


class DocumentVersion(Model):
    """Immutable stored file belonging to a document, deduplicated by SHA-256."""

    id = fields.IntField(primary_key=True)
    document: fields.ForeignKeyRelation[Document] = fields.ForeignKeyField(
        "models.Document", related_name="versions", on_delete=fields.CASCADE
    )
    # Runtime FK id attribute, annotated for static type checkers
    document_id: int
    version_number = fields.IntField(description="Sequential version number: 1, 2, 3...")
    file_name = fields.CharField(max_length=255, description="Original uploaded file name")
    file_path = fields.CharField(max_length=500, description="Local path of the stored file")
    file_size = fields.BigIntField(description="File size in bytes")
    sha256_hash = fields.CharField(max_length=64, db_index=True, description="SHA-256 for dedup")
    comment = fields.CharField(max_length=255, null=True, description="Version comment")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "document_versions"
        unique_together = (("document", "version_number"),)
