"""Upload validation zone: extension whitelist, magic bytes, text decoding.

Anything not listed in the whitelist (app/schemas/validation.py) is rejected.
The client's extension and MIME are never trusted alone — the file's own head
bytes decide.
"""

import codecs
from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException, status

from app.schemas.validation import ALLOWED_SPECS, TypeSpec

# Enough to cover every signature; the first streamed chunk fills it.
HEAD_LEN = 16

_BY_EXTENSION = {ext: spec for spec in ALLOWED_SPECS for ext in spec.extensions}
_ALLOWED_LIST = ", ".join(sorted(_BY_EXTENSION))


def verify_extension(filename: str) -> TypeSpec:
    spec = _BY_EXTENSION.get(Path(filename).suffix.lower())
    if spec is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"неподдерживаемый тип файла. Разрешены: {_ALLOWED_LIST}",
        )
    return spec


def verify_content_type(spec: TypeSpec, content_type: str | None) -> None:
    """Soft check only: clients can lie about MIME, verify_head is the real gate."""
    if (
        content_type
        and content_type not in spec.mimes
        and content_type != "application/octet-stream"
    ):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"тип содержимого '{content_type}' не совпадает с расширением файла",
        )


def verify_head(spec: TypeSpec, head: bytes) -> None:
    """Match the file's leading bytes against the declared type's signature."""
    if spec.signature is not None and not head.startswith(spec.signature):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "содержимое файла не соответствует заявленному типу (проверка magic bytes)",
        )


def make_text_guard() -> Callable[[bytes], None]:
    """Incremental UTF-8 decoder: chunks may split multibyte characters."""
    decoder = codecs.getincrementaldecoder("utf-8")()

    def guard(chunk: bytes, final: bool = False) -> None:
        try:
            decoder.decode(chunk, final)
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "текстовый файл не является корректным UTF-8",
            ) from exc

    return guard
