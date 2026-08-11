from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    supported_extensions: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png")
    text_min_characters: int = 80
    readable_character_ratio: float = 0.85
    source_marker_min_count: int = 3
    general_confidence_threshold: float = 0.85
    critical_confidence_threshold: float = 0.90
    amount_tolerance_krw: int = 1
    pdf_render_dpi: int = 180
    ocr_image_scale: float = 1.0
    max_preview_width: int = 1000
    max_preview_height: int = 1400


DEFAULT_SETTINGS = Settings()
