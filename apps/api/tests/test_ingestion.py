from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from ps01_api.ingestion import (
    IngestionError,
    extract_image_ocr,
    extract_pdf,
    split_text,
    structured_record_candidates,
)


class FakeOcrResult:
    json = {
        "res": {
            "rec_texts": ["Acme invoice INV-2048", "Total USD 48,000"],
            "rec_boxes": [[10, 20, 220, 48], [10, 70, 180, 98]],
            "rec_scores": [0.99, 0.97],
        }
    }


class FakeOcrEngine:
    def __init__(self) -> None:
        self.inputs: list[object] = []

    def predict(self, source: object) -> list[FakeOcrResult]:
        self.inputs.append(source)
        return [FakeOcrResult()]


def make_pdf(path: Path, text: str | None) -> None:
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def make_png_header(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + width.to_bytes(4, "big") + height.to_bytes(4, "big")


def make_jpeg_header(width: int, height: int) -> bytes:
    return (
        b"\xff\xd8\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )


def test_split_text_preserves_all_content_and_bounds_chunks() -> None:
    text = "alpha " * 1_000
    chunks = split_text(text, max_chars=80)
    assert " ".join(chunks).split() == text.split()
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_pdf_extraction_preserves_page_provenance(tmp_path: Path) -> None:
    pdf_path = tmp_path / "contract.pdf"
    make_pdf(pdf_path, "Acme payment terms are Net 30 days from invoice date.")

    chunks = extract_pdf(pdf_path, "contract-2026")

    assert len(chunks) == 1
    assert chunks[0].source_type == "pdf"
    assert chunks[0].page_number == 1
    assert chunks[0].source_id == "contract-2026"
    assert "Net 30" in chunks[0].content


def test_scanned_pdf_page_uses_ocr_and_keeps_page_and_region(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    make_pdf(pdf_path, None)
    engine = FakeOcrEngine()

    chunks = extract_pdf(pdf_path, "scan-invoice", ocr_engine=engine)

    assert len(engine.inputs) == 1
    assert len(chunks) == 2
    assert chunks[0].source_type == "pdf"
    assert chunks[0].page_number == 1
    assert chunks[0].image_id == "scan-invoice#page-1"
    assert chunks[0].ocr_region == {
        "x_min": 10.0,
        "y_min": 20.0,
        "x_max": 220.0,
        "y_max": 48.0,
        "confidence": 0.99,
    }


def test_image_ocr_keeps_image_id_and_regions(tmp_path: Path) -> None:
    image_path = tmp_path / "invoice.png"
    image_path.write_bytes(make_png_header(100, 80) + b"synthetic image bytes")
    engine = FakeOcrEngine()

    chunks = extract_image_ocr(image_path, "image-invoice-2048", engine=engine)

    assert len(chunks) == 2
    assert chunks[0].source_type == "image_ocr"
    assert chunks[0].image_id == "image-invoice-2048"
    assert chunks[0].source_id == "image-invoice-2048"
    assert chunks[1].chunk_index == 1


def test_image_rejects_excessive_pixel_count_before_ocr(tmp_path: Path) -> None:
    image_path = tmp_path / "oversized.png"
    image_path.write_bytes(make_png_header(5_000, 5_000))
    engine = FakeOcrEngine()

    with pytest.raises(IngestionError, match="pixels"):
        extract_image_ocr(image_path, "oversized", engine=engine)

    assert engine.inputs == []


def test_jpeg_header_dimensions_are_read_before_ocr(tmp_path: Path) -> None:
    image_path = tmp_path / "invoice.jpg"
    image_path.write_bytes(make_jpeg_header(100, 80))
    engine = FakeOcrEngine()

    chunks = extract_image_ocr(image_path, "jpeg-invoice", engine=engine)

    assert len(chunks) == 2
    assert len(engine.inputs) == 1


def test_image_rejects_a_mismatched_file_signature(tmp_path: Path) -> None:
    image_path = tmp_path / "invoice.png"
    image_path.write_bytes(b"not a PNG")

    with pytest.raises(IngestionError, match="PNG signature"):
        extract_image_ocr(image_path, "image-invoice-2048", engine=FakeOcrEngine())


def test_structured_records_are_canonical_and_preserve_row_id() -> None:
    chunks = structured_record_candidates(
        table_name="invoices",
        row_id="INV-2048",
        source_name="Invoice INV-2048",
        fields={"customer": "Acme", "amount": 48_000, "status": "unpaid"},
    )

    assert len(chunks) == 1
    assert chunks[0].source_type == "structured"
    assert chunks[0].source_id == "invoices"
    assert chunks[0].row_id == "INV-2048"
    assert chunks[0].content.endswith('{"amount":48000,"customer":"Acme","status":"unpaid"}')


def test_structured_source_can_keep_document_id_separate_from_table_name() -> None:
    chunks = structured_record_candidates(
        table_name="invoices",
        row_id="INV-2048",
        source_name="Invoice INV-2048",
        fields={"status": "unpaid"},
        source_id="nova-finance-records",
    )

    assert chunks[0].source_id == "nova-finance-records"
    assert chunks[0].metadata == {"table": "invoices"}


def test_structured_record_large_fields_are_chunked_without_dropping_data() -> None:
    description = "Payment detail " * 300
    chunks = structured_record_candidates(
        table_name="invoices",
        row_id="INV-2048",
        source_name="Invoice INV-2048",
        fields={"description": description},
    )

    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.row_id == "INV-2048" for chunk in chunks)
    assert "Payment detail" in " ".join(chunk.content for chunk in chunks)
