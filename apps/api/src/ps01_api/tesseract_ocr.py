"""Bounded native OCR adapter retaining canonical line coordinates."""

import csv
import io
import os
import subprocess

from .ingestion import IngestionError


class TesseractOCR:
    def predict(self, source):
        pixels = None
        if not isinstance(source, str):
            import pymupdf

            height, width, channels = source.shape
            if channels != 3:
                raise IngestionError("OCR expects RGB pixels")
            pixels = pymupdf.Pixmap(pymupdf.csRGB, width, height, source.tobytes(), False).tobytes(
                "png"
            )
        try:
            result = subprocess.run(
                ["tesseract", source if pixels is None else "stdin", "stdout", "-l", "eng", "tsv"],
                input=pixels,
                capture_output=True,
                timeout=30,
                check=True,
                env=os.environ | {"OMP_THREAD_LIMIT": "1"},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise IngestionError("OCR is unavailable or exceeded its 30-second page limit") from exc
        if len(result.stdout) > 2_000_000:
            raise IngestionError("OCR output exceeds the bounded size limit")
        lines = {}
        try:
            for word in csv.DictReader(io.StringIO(result.stdout.decode("utf-8")), delimiter="\t"):
                if word["level"] != "5" or not word["text"].strip():
                    continue
                key = tuple(word[k] for k in ("page_num", "block_num", "par_num", "line_num"))
                x, y, w, h = (int(word[k]) for k in ("left", "top", "width", "height"))
                lines.setdefault(key, []).append(
                    (word["text"], x, y, x + w, y + h, float(word["conf"]) / 100)
                )
        except (KeyError, ValueError, UnicodeError) as exc:
            raise IngestionError("OCR returned malformed coordinates") from exc
        texts, boxes, scores = [], [], []
        for words in lines.values():
            x0, y0 = min(w[1] for w in words), min(w[2] for w in words)
            x1, y1 = max(w[3] for w in words), max(w[4] for w in words)
            texts.append(" ".join(w[0] for w in words))
            boxes.append([x0, y0, x1, y1])
            scores.append(sum(w[5] for w in words) / len(words))
        return [{"rec_texts": texts, "rec_boxes": boxes, "rec_scores": scores}]
