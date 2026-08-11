from __future__ import annotations

import re
from difflib import SequenceMatcher

from receipt_mvp.models import ExtractionMethod, FieldEvidence


def compact_label(value: str) -> str:
    return re.sub(r"[\s:/()·._-]", "", value).lower()


def label_matches(value: str, expected: str, threshold: float = 0.78) -> bool:
    left = compact_label(value)
    right = compact_label(expected)
    if left == right or right in left:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


def make_evidence(
    transaction_id: str,
    source_label: str,
    standard_path: str,
    raw_value,
    normalized_value,
    parser: str,
    method: ExtractionMethod,
    confidence: float | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    transform: str | None = None,
) -> FieldEvidence:
    return FieldEvidence(
        transaction_id=transaction_id,
        source_label=source_label,
        standard_path=standard_path,
        raw_value=raw_value,
        normalized_value=normalized_value,
        parser=parser,
        extraction_method=method,
        confidence=confidence,
        bbox=bbox,
        transform=transform,
    )

