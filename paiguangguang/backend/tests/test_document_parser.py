from __future__ import annotations

from app.services.document_parser import (
    DocumentParseError,
    DocumentParser,
    DocumentTooLargeError,
    EmptyDocumentError,
    ParsedDocument,
    UnsupportedDocumentTypeError,
)


def _build_pdf_bytes() -> bytes:
    objects: list[bytes] = []

    def add_object(body: str) -> int:
        objects.append(body.encode("utf-8"))
        return len(objects)

    catalog = add_object("<< /Type /Catalog /Pages 2 0 R >>\n")
    pages = add_object("<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>\n")
    page_1 = add_object(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>\n"
    )
    page_2 = add_object(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>\n"
    )
    font = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n")

    def make_stream(text: str) -> bytes:
        payload = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET\n".encode("utf-8")
        return f"<< /Length {len(payload)} >>\nstream\n".encode("utf-8") + payload + b"endstream\n"

    stream_1 = make_stream("First page from PDF")
    stream_2 = make_stream("Second page from PDF")
    objects.extend([stream_1, stream_2])

    header = b"%PDF-1.4\n"
    body = bytearray(header)
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n".encode("utf-8"))
        body.extend(obj)
        body.extend(b"endobj\n")

    xref_offset = len(body)
    xref = [b"xref\n", f"0 {len(objects) + 1}\n".encode("utf-8"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("utf-8"))
    xref.append(
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("utf-8")
        + b"startxref\n"
        + f"{xref_offset}\n".encode("utf-8")
        + b"%%EOF\n"
    )
    body.extend(b"".join(xref))
    return bytes(body)


def test_parser_normalizes_txt_and_markdown() -> None:
    parser = DocumentParser()

    txt = parser.parse("notes.txt", b"Line one\r\nLine two\rLine three\n")
    md = parser.parse("README.md", b"  # Heading\r\n\r\nParagraph text.  ")

    assert isinstance(txt, ParsedDocument)
    assert txt.file_extension == ".txt"
    assert txt.normalized_text == "Line one\nLine two\nLine three"
    assert txt.pages[0].page_number == 1
    assert txt.pages[0].text == "Line one\nLine two\nLine three"
    assert txt.source_metadata["source_type"] == "txt"

    assert md.file_extension == ".md"
    assert md.normalized_text == "# Heading\n\nParagraph text."
    assert md.pages[0].page_number == 1
    assert md.source_metadata["source_type"] == "markdown"


def test_parser_extracts_pdf_pages_and_text() -> None:
    parser = DocumentParser()
    parsed = parser.parse("slides.pdf", _build_pdf_bytes())

    assert parsed.file_extension == ".pdf"
    assert parsed.source_metadata["source_type"] == "pdf"
    assert parsed.source_metadata["page_count"] == 2
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert parsed.pages[0].text == "First page from PDF"
    assert parsed.pages[1].text == "Second page from PDF"
    assert "First page from PDF" in parsed.normalized_text
    assert "Second page from PDF" in parsed.normalized_text


def test_parser_rejects_unsupported_extension() -> None:
    parser = DocumentParser()

    try:
        parser.parse("archive.docx", b"content")
    except UnsupportedDocumentTypeError as exc:
        assert ".docx" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("UnsupportedDocumentTypeError was not raised")


def test_parser_rejects_empty_content() -> None:
    parser = DocumentParser()

    try:
        parser.parse("empty.txt", b"   \n\t  ")
    except EmptyDocumentError as exc:
        assert "empty" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("EmptyDocumentError was not raised")


def test_parser_rejects_oversized_file() -> None:
    parser = DocumentParser(max_file_size=16)

    try:
        parser.parse("too-big.txt", b"x" * 17)
    except DocumentTooLargeError as exc:
        assert "too-big.txt" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("DocumentTooLargeError was not raised")
