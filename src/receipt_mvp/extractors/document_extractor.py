from __future__ import annotations

import logging
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageOps

from receipt_mvp.config.settings import DEFAULT_SETTINGS, Settings
from receipt_mvp.extractors.file_loader import FileDescriptor
from receipt_mvp.models import ExtractionMethod, OcrToken, PageExtraction
from receipt_mvp.ocr.base import OcrAdapter, OcrUnavailableError, UnavailableOcrAdapter
from receipt_mvp.ocr.preprocess import preprocess_for_ocr


LOGGER = logging.getLogger(__name__)
SOURCE_MARKERS = (
    "결제정보",
    "구매정보",
    "이용상점정보",
    "카드 영수증",
    "통합 카드 영수증",
    "판매자 정보",
    "가맹점 정보",
    "승인금액",
)


class DocumentExtractor:
    def __init__(
        self,
        temp_dir: str | Path,
        ocr_adapter: OcrAdapter | None = None,
        settings: Settings = DEFAULT_SETTINGS,
    ) -> None:
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_adapter = ocr_adapter or UnavailableOcrAdapter()
        self.settings = settings

    def extract(self, descriptor: FileDescriptor) -> list[PageExtraction]:
        if descriptor.suffix == ".pdf":
            return self._extract_pdf(descriptor)
        return [self._extract_image(descriptor, 1)]

    def _extract_pdf(self, descriptor: FileDescriptor) -> list[PageExtraction]:
        results: list[PageExtraction] = []
        try:
            document = fitz.open(descriptor.path)
        except Exception as error:
            return [self._failed(descriptor.path, 1, ExtractionMethod.PDF_TEXT, "PDF_OPEN_FAILED", error)]
        try:
            for page_index in range(document.page_count):
                page_number = page_index + 1
                try:
                    page = document.load_page(page_index)
                    text = page.get_text("text") or ""
                    words = page.get_text("words") or []
                    if self._has_usable_text(text):
                        tokens = [
                            OcrToken(
                                text=str(word[4]),
                                bbox=(float(word[0]), float(word[1]), float(word[2]), float(word[3])),
                                confidence=1.0,
                                line_id=f"{int(word[5])}:{int(word[6])}",
                            )
                            for word in words
                            if len(word) >= 7 and str(word[4]).strip()
                        ]
                        results.append(
                            PageExtraction(
                                source_path=descriptor.path,
                                page_number=page_number,
                                method=ExtractionMethod.PDF_TEXT,
                                raw_text=text,
                                tokens=tokens,
                                confidence=1.0,
                                width=max(1, round(page.rect.width)),
                                height=max(1, round(page.rect.height)),
                            )
                        )
                    else:
                        rendered = self._render_page(page, descriptor.sha256, page_number)
                        results.append(self._ocr_image(descriptor.path, page_number, rendered))
                except Exception as error:
                    LOGGER.exception("페이지 추출 실패: file=%s page=%s", descriptor.name, page_number)
                    results.append(
                        self._failed(
                            descriptor.path,
                            page_number,
                            ExtractionMethod.PDF_TEXT,
                            "PAGE_EXTRACTION_FAILED",
                            error,
                        )
                    )
        finally:
            document.close()
        return results

    def _extract_image(self, descriptor: FileDescriptor, page_number: int) -> PageExtraction:
        try:
            image_dir = self.temp_dir / descriptor.sha256
            image_dir.mkdir(parents=True, exist_ok=True)
            normalized = image_dir / f"page-{page_number:04d}.png"
            with Image.open(descriptor.path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.save(normalized, format="PNG", optimize=True)
            return self._ocr_image(descriptor.path, page_number, normalized)
        except Exception as error:
            return self._failed(
                descriptor.path,
                page_number,
                ExtractionMethod.IMAGE,
                "IMAGE_OPEN_FAILED",
                error,
            )

    def _render_page(self, page: fitz.Page, sha256: str, page_number: int) -> Path:
        page_dir = self.temp_dir / sha256
        page_dir.mkdir(parents=True, exist_ok=True)
        output = page_dir / f"page-{page_number:04d}.png"
        pixmap = page.get_pixmap(dpi=self.settings.pdf_render_dpi, alpha=False)
        pixmap.save(output)
        return output

    def _ocr_image(self, source_path: str, page_number: int, rendered: Path) -> PageExtraction:
        processed = rendered.with_name(f"{rendered.stem}-ocr.png")
        try:
            preprocess_for_ocr(rendered, processed, self.settings.ocr_image_scale)
            result = self.ocr_adapter.extract(processed)
            with Image.open(rendered) as image:
                width, height = image.size
            return PageExtraction(
                source_path=source_path,
                page_number=page_number,
                method=ExtractionMethod.OCR,
                raw_text=result.text,
                tokens=result.tokens,
                confidence=result.confidence,
                image_path=str(rendered),
                width=width,
                height=height,
                render_dpi=self.settings.pdf_render_dpi,
            )
        except OcrUnavailableError as error:
            return self._failed(
                source_path,
                page_number,
                ExtractionMethod.OCR,
                "OCR_NOT_AVAILABLE",
                error,
                image_path=str(rendered),
            )
        except Exception as error:
            LOGGER.exception("OCR 실패: page=%s", page_number)
            return self._failed(
                source_path,
                page_number,
                ExtractionMethod.OCR,
                "OCR_FAILED",
                error,
                image_path=str(rendered),
            )

    def _has_usable_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text)
        if len(normalized) < self.settings.text_min_characters:
            return False
        readable = sum(
            character.isalnum() or "가" <= character <= "힣" or character in ",.-_/()[]"
            for character in normalized
        )
        ratio = readable / max(1, len(normalized))
        marker_count = sum(marker in text for marker in SOURCE_MARKERS)
        return (
            ratio >= self.settings.readable_character_ratio
            and marker_count >= self.settings.source_marker_min_count
        )

    @staticmethod
    def _failed(
        source_path: str,
        page_number: int,
        method: ExtractionMethod,
        code: str,
        error: Exception,
        image_path: str | None = None,
    ) -> PageExtraction:
        return PageExtraction(
            source_path=source_path,
            page_number=page_number,
            method=method,
            image_path=image_path,
            error_code=code,
            error_message=str(error),
        )
