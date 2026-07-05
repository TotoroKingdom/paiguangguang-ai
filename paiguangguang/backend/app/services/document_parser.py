from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.core.config import get_settings


DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {".pdf"}


class DocumentParseError(ValueError):
    pass


class UnsupportedDocumentTypeError(DocumentParseError):
    pass


class EmptyDocumentError(DocumentParseError):
    pass


class DocumentTooLargeError(DocumentParseError):
    pass


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    source_name: str
    file_extension: str
    normalized_text: str
    pages: list[ParsedPage] = field(default_factory=list)
    source_metadata: dict[str, object] = field(default_factory=dict)
    size_bytes: int = 0


class DocumentParser:
    def __init__(self, *, max_file_size: int | None = None) -> None:
        settings = get_settings()
        self.max_file_size = max_file_size if max_file_size is not None else settings.document_max_file_size_bytes

    def parse(self, file_name: str, content: bytes) -> ParsedDocument:
        if len(content) > self.max_file_size:
            raise DocumentTooLargeError(
                f"{file_name} exceeds the maximum file size of {self.max_file_size} bytes"
            )

        suffix = Path(file_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise UnsupportedDocumentTypeError(f"Unsupported document type: {suffix or '<none>'}")

        if suffix == ".pdf":
            return self._parse_pdf(file_name, content)
        return self._parse_text_like(file_name, suffix, content)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    def _build_result(
        self,
        *,
        file_name: str,
        suffix: str,
        pages: list[ParsedPage],
    ) -> ParsedDocument:
        normalized_pages = [
            ParsedPage(page_number=page.page_number, text=self._normalize_text(page.text))
            for page in pages
        ]
        normalized_text = self._normalize_text("\n\n".join(page.text for page in normalized_pages if page.text))
        if not normalized_text:
            raise EmptyDocumentError(f"{file_name} does not contain any extractable text")

        source_type = "markdown" if suffix in {".md", ".markdown"} else "txt" if suffix == ".txt" else "pdf"
        return ParsedDocument(
            source_name=file_name,
            file_extension=suffix,
            normalized_text=normalized_text,
            pages=normalized_pages,
            source_metadata={
                "source_type": source_type,
                "file_name": file_name,
                "file_extension": suffix,
                "page_count": len(normalized_pages) if normalized_pages else 1,
            },
            size_bytes=0,
        )

    def _parse_text_like(self, file_name: str, suffix: str, content: bytes) -> ParsedDocument:
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentParseError(f"Failed to decode {file_name} as UTF-8 text") from exc

        result = self._build_result(
            file_name=file_name,
            suffix=suffix,
            pages=[ParsedPage(page_number=1, text=decoded)],
        )
        return ParsedDocument(
            source_name=result.source_name,
            file_extension=result.file_extension,
            normalized_text=result.normalized_text,
            pages=result.pages,
            source_metadata=result.source_metadata,
            size_bytes=len(content),
        )

    def _parse_pdf(self, file_name: str, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:  # pragma: no cover - pypdf error shape varies
            raise DocumentParseError(f"Failed to parse PDF document {file_name}") from exc

        pages: list[ParsedPage] = []
        for page_number, page in enumerate(reader.pages, start=1):
            extracted_text = page.extract_text() or ""
            pages.append(ParsedPage(page_number=page_number, text=extracted_text))

        result = self._build_result(file_name=file_name, suffix=".pdf", pages=pages)
        return ParsedDocument(
            source_name=result.source_name,
            file_extension=result.file_extension,
            normalized_text=result.normalized_text,
            pages=result.pages,
            source_metadata=result.source_metadata,
            size_bytes=len(content),
        )
