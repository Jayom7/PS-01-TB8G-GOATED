from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SourceType = Literal["pdf", "image_ocr", "structured"]
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_OCR_REGIONS = 1_000
MAX_CHUNK_CHARS = 1_200
MAX_PAGE_PIXELS = 16_000_000
MAX_IMAGE_PIXELS = 16_000_000


class IngestionError(ValueError):
    """A source is invalid, unsupported, or exceeds a bounded parser limit."""


@dataclass(frozen=True)
class ChunkCandidate:
    source_type: SourceType
    source_name: str
    source_id: str
    content: str
    chunk_index: int
    page_number: int | None = None
    row_id: str | None = None
    image_id: str | None = None
    ocr_region: dict[str, int | float] | None = None
    metadata: dict[str, Any] | None = None


def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    while len(normalized) > max_chars:
        boundary = normalized.rfind(" ", 0, max_chars + 1)
        if boundary < max_chars // 2:
            boundary = max_chars
        chunks.append(normalized[:boundary].strip())
        normalized = normalized[boundary:].strip()
    if normalized:
        chunks.append(normalized)
    return chunks


def extract_pdf(
    path: Path,
    source_id: str,
    *,
    ocr_engine: Any | None = None,
) -> list[ChunkCandidate]:
    _check_file_size(path)
    if path.suffix.lower() != ".pdf":
        raise IngestionError("Expected a PDF source")
    if not path.read_bytes().startswith(b"%PDF-"):
        raise IngestionError("Source does not have a PDF signature")
    if not source_id.strip():
        raise IngestionError("PDF source ID is required")
    try:
        import pymupdf
    except ImportError as exc:
        raise IngestionError("Install the ingestion extra to parse PDFs") from exc

    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise IngestionError("The PDF could not be opened") from exc
    if document.is_encrypted:
        document.close()
        raise IngestionError("Encrypted PDFs are not supported")
    if len(document) > MAX_PDF_PAGES:
        document.close()
        raise IngestionError(f"PDF exceeds the {MAX_PDF_PAGES}-page limit")

    candidates: list[ChunkCandidate] = []
    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            text = page.get_text("text", sort=True)
            chunks = split_text(text)
            if chunks:
                for chunk in chunks:
                    candidates.append(
                        ChunkCandidate(
                            source_type="pdf",
                            source_name=path.name,
                            source_id=source_id,
                            content=chunk,
                            chunk_index=len(candidates),
                            page_number=page_number,
                        )
                    )
                continue

            if ocr_engine is None:
                ocr_engine = _create_ocr_engine()
            rect = page.rect
            scale = min(2.0, math.sqrt(MAX_PAGE_PIXELS / max(rect.width * rect.height, 1)))
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            try:
                import numpy
            except ImportError as exc:
                raise IngestionError("Install the ingestion extra to run PaddleOCR") from exc
            pixels = numpy.frombuffer(pixmap.samples, dtype=numpy.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            try:
                result = ocr_engine.predict(pixels)
            except Exception as exc:
                raise IngestionError("Scanned PDF page OCR failed") from exc
            candidates.extend(
                _ocr_candidates(
                    result,
                    source_type="pdf",
                    source_name=path.name,
                    source_id=source_id,
                    page_number=page_number,
                    image_id=f"{source_id}#page-{page_number}",
                )
            )
    finally:
        document.close()
    return candidates


def extract_image_ocr(
    path: Path,
    source_id: str,
    *,
    engine: Any | None = None,
) -> list[ChunkCandidate]:
    _check_file_size(path)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise IngestionError("Supported image formats are PNG and JPEG")
    with path.open("rb") as source_file:
        header = source_file.read(8)
    if path.suffix.lower() == ".png" and header != b"\x89PNG\r\n\x1a\n":
        raise IngestionError("Source does not have a PNG signature")
    if path.suffix.lower() in {".jpg", ".jpeg"} and header[:2] != b"\xff\xd8":
        raise IngestionError("Source does not have a JPEG signature")
    if not source_id.strip():
        raise IngestionError("Image source ID is required")
    width, height = _image_dimensions(path)
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise IngestionError(f"Image dimensions must not exceed {MAX_IMAGE_PIXELS:,} pixels")
    if engine is None:
        engine = _create_ocr_engine()

    try:
        results = engine.predict(str(path))
    except Exception as exc:
        raise IngestionError("Image OCR failed") from exc
    return _ocr_candidates(
        results,
        source_type="image_ocr",
        source_name=path.name,
        source_id=source_id,
        image_id=source_id,
    )


def _image_dimensions(path: Path) -> tuple[int, int]:
    """Read raster dimensions from headers without decoding image pixels."""
    try:
        with path.open("rb") as source_file:
            signature = source_file.read(8)
            if signature == b"\x89PNG\r\n\x1a\n":
                source_file.seek(16)
                dimensions = source_file.read(8)
                if len(dimensions) == 8:
                    return int.from_bytes(dimensions[:4], "big"), int.from_bytes(
                        dimensions[4:], "big"
                    )
                raise IngestionError("PNG dimensions are missing")

            if signature[:2] != b"\xff\xd8":
                raise IngestionError("Source is not a supported PNG or JPEG")
            source_file.seek(2)

            while marker := source_file.read(1):
                if marker != b"\xff":
                    continue
                while (marker := source_file.read(1)) == b"\xff":
                    pass
                if not marker:
                    break
                code = marker[0]
                if code in {0xD8, 0xD9} or 0xD0 <= code <= 0xD7 or code == 0x01:
                    continue
                segment_length_bytes = source_file.read(2)
                if len(segment_length_bytes) != 2:
                    break
                segment_length = int.from_bytes(segment_length_bytes, "big")
                if segment_length < 2:
                    break
                if code in {
                    0xC0,
                    0xC1,
                    0xC2,
                    0xC3,
                    0xC5,
                    0xC6,
                    0xC7,
                    0xC9,
                    0xCA,
                    0xCB,
                    0xCD,
                    0xCE,
                    0xCF,
                }:
                    dimensions = source_file.read(5)
                    if len(dimensions) == 5:
                        height = int.from_bytes(dimensions[1:3], "big")
                        width = int.from_bytes(dimensions[3:5], "big")
                        return width, height
                    break
                source_file.seek(segment_length - 2, 1)
    except OSError as exc:
        raise IngestionError("Image dimensions could not be read") from exc
    raise IngestionError("Image dimensions are missing or malformed")


def _ocr_candidates(
    results: Any,
    *,
    source_type: Literal["pdf", "image_ocr"],
    source_name: str,
    source_id: str,
    page_number: int | None = None,
    image_id: str | None = None,
    start_index: int = 0,
) -> list[ChunkCandidate]:
    candidates: list[ChunkCandidate] = []
    for result in results:
        payload = _ocr_payload(result)
        texts = payload.get("rec_texts", [])
        boxes = payload.get("rec_boxes", [])
        scores = payload.get("rec_scores", [])
        if not isinstance(texts, list) or not isinstance(boxes, list):
            raise IngestionError("OCR returned malformed text or region data")
        if len(texts) != len(boxes) or (scores and len(scores) != len(texts)):
            raise IngestionError("OCR text and region counts did not match")
        if len(candidates) + len(texts) > MAX_OCR_REGIONS:
            raise IngestionError(f"Image exceeds the {MAX_OCR_REGIONS}-region limit")
        normalized_scores = scores if scores else [None] * len(texts)
        for text, box, score in zip(texts, boxes, normalized_scores, strict=True):
            if not isinstance(text, str) or not text.strip():
                continue
            coordinates = _region_coordinates(box)
            if score is not None:
                coordinates["confidence"] = float(score)
            candidates.append(
                ChunkCandidate(
                    source_type=source_type,
                    source_name=source_name,
                    source_id=source_id,
                    content=text.strip(),
                    chunk_index=start_index + len(candidates),
                    page_number=page_number,
                    image_id=image_id,
                    ocr_region=coordinates,
                )
            )
    return candidates


def structured_record_candidates(
    *,
    table_name: str,
    row_id: str,
    source_name: str,
    fields: dict[str, str | int | float | bool | None],
    source_id: str | None = None,
    chunk_index: int = 0,
) -> list[ChunkCandidate]:
    if not table_name.strip() or not row_id.strip() or not source_name.strip():
        raise IngestionError("Structured sources require table, row, and source names")
    if not fields:
        raise IngestionError("Structured source must contain at least one field")
    if any(
        value is not None and not isinstance(value, (str, int, float, bool))
        for value in fields.values()
    ):
        raise IngestionError("Structured fields must be scalar values")
    if any(isinstance(value, float) and not math.isfinite(value) for value in fields.values()):
        raise IngestionError("Structured numeric fields must be finite")
    canonical_fields = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    text_chunks = split_text(f"table: {table_name}; row: {row_id}; data: {canonical_fields}")
    return [
        ChunkCandidate(
            source_type="structured",
            source_name=source_name,
            source_id=source_id or table_name,
            content=chunk,
            chunk_index=chunk_index + offset,
            row_id=row_id,
            metadata={"table": table_name},
        )
        for offset, chunk in enumerate(text_chunks)
    ]


def _check_file_size(path: Path) -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise IngestionError("Source file is unavailable") from exc
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise IngestionError(f"Source must be between 1 byte and {MAX_SOURCE_BYTES} bytes")


def _create_ocr_engine() -> Any:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise IngestionError("Install the ingestion extra to run PaddleOCR") from exc
    try:
        return PaddleOCR(
            lang="en",
            engine="onnxruntime",
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except Exception as exc:
        raise IngestionError("PaddleOCR could not initialize") from exc


def _ocr_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "json", None)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError as exc:
            raise IngestionError("OCR returned invalid JSON") from exc
    if isinstance(payload, dict) and isinstance(payload.get("res"), dict):
        payload = payload["res"]
    if not isinstance(payload, dict):
        raise IngestionError("OCR returned malformed result data")
    return payload


def _region_coordinates(box: Any) -> dict[str, int | float]:
    if hasattr(box, "tolist"):
        box = box.tolist()
    if not isinstance(box, (list, tuple)):
        raise IngestionError("OCR returned malformed region coordinates")
    if len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        x_min, y_min, x_max, y_max = box
    elif len(box) == 4 and all(
        isinstance(point, (list, tuple)) and len(point) == 2 for point in box
    ):
        x_values = [point[0] for point in box]
        y_values = [point[1] for point in box]
        x_min, y_min, x_max, y_max = min(x_values), min(y_values), max(x_values), max(y_values)
    else:
        raise IngestionError("OCR returned malformed region coordinates")
    if not all(math.isfinite(float(value)) for value in (x_min, y_min, x_max, y_max)):
        raise IngestionError("OCR returned non-finite region coordinates")
    return {
        "x_min": float(x_min),
        "y_min": float(y_min),
        "x_max": float(x_max),
        "y_max": float(y_max),
    }
