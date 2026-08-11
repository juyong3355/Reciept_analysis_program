from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw

from receipt_mvp.config.settings import Settings
from receipt_mvp.extractors import DocumentExtractor, FileLoader
from receipt_mvp.models import ExtractionMethod, OcrToken
from receipt_mvp.ocr.base import OcrAdapter, OcrResult


class FakeOcrAdapter(OcrAdapter):
    def is_available(self) -> bool:
        return True

    def extract(self, image_path: str | Path) -> OcrResult:
        return OcrResult(
            text="통합 카드 영수증\n판매자 정보\n가맹점 정보\n승인금액",
            tokens=[OcrToken(text="통합 카드 영수증", confidence=0.98)],
            confidence=0.98,
        )


def test_text_pdf_uses_direct_extraction(tmp_path: Path) -> None:
    path = tmp_path / "text.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PAYMENT PURCHASE MERCHANT " * 12)
    document.save(path)
    document.close()
    settings = Settings(text_min_characters=20, readable_character_ratio=0.8, source_marker_min_count=0)
    result = DocumentExtractor(tmp_path / "temp", FakeOcrAdapter(), settings).extract(
        FileLoader(settings).describe(path)
    )
    assert len(result) == 1
    assert result[0].method == ExtractionMethod.PDF_TEXT
    assert "PAYMENT" in result[0].raw_text


def test_image_pdf_uses_ocr(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    image = Image.new("RGB", (600, 800), "white")
    ImageDraw.Draw(image).text((40, 40), "receipt", fill="black")
    image.save(image_path)
    pdf_path = tmp_path / "image.pdf"
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    page.insert_image(page.rect, filename=str(image_path))
    document.save(pdf_path)
    document.close()
    result = DocumentExtractor(tmp_path / "temp", FakeOcrAdapter()).extract(
        FileLoader().describe(pdf_path)
    )
    assert result[0].method == ExtractionMethod.OCR
    assert result[0].confidence == 0.98
    assert Path(result[0].image_path).is_file()


def test_image_input_uses_ocr(tmp_path: Path) -> None:
    image_path = tmp_path / "receipt.jpg"
    Image.new("RGB", (300, 400), "white").save(image_path)
    result = DocumentExtractor(tmp_path / "temp", FakeOcrAdapter()).extract(
        FileLoader().describe(image_path)
    )
    assert result[0].method == ExtractionMethod.OCR
