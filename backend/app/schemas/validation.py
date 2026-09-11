"""Upload whitelist: allowed extensions, MIME types and magic byte signatures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TypeSpec:
    extensions: tuple[str, ...]
    mimes: tuple[str, ...]
    # None -> text formats, checked by decoding the stream as UTF-8 instead.
    signature: bytes | None
    text: bool = False


PDF = TypeSpec((".pdf",), ("application/pdf",), b"%PDF-")
OOXML = TypeSpec(
    (".docx", ".xlsx", ".pptx"),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    b"PK\x03\x04",
)
JPG = TypeSpec((".jpg", ".jpeg"), ("image/jpeg",), b"\xff\xd8\xff")
PNG = TypeSpec((".png",), ("image/png",), b"\x89PNG\r\n\x1a\n")
TEXT = TypeSpec((".txt", ".md"), ("text/plain", "text/markdown"), None, text=True)

ALLOWED_SPECS = (PDF, OOXML, JPG, PNG, TEXT)
