from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from receipt_mvp.models import PageExtraction, Platform


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Platform
    document_type: str | None = None
    confidence: float = Field(ge=0, le=1)
    matched_markers: list[str]


class DocumentClassifier:
    COUPANG_MARKERS = ("결제정보", "구매정보", "이용상점정보", "과세금액", "합계금액")
    NAVER_MARKERS = ("판매자 정보", "가맹점 정보", "승인금액", "공급가액", "합계")

    def classify(self, page: PageExtraction) -> ClassificationResult:
        text = page.raw_text.replace("\u3000", " ")
        coupang = [marker for marker in self.COUPANG_MARKERS if marker in text]
        naver = [marker for marker in self.NAVER_MARKERS if marker in text]
        if len(coupang) >= 3 and all(marker in coupang for marker in ("결제정보", "구매정보")):
            return ClassificationResult(
                platform=Platform.COUPANG,
                document_type="CARD_RECEIPT",
                confidence=min(1.0, 0.55 + len(coupang) * 0.09),
                matched_markers=coupang,
            )
        title = None
        if "통합 카드 영수증" in text or "통합카드영수증" in text.replace(" ", ""):
            title = "INTEGRATED_CARD_RECEIPT"
        elif "카드 영수증" in text or "카드영수증" in text.replace(" ", ""):
            title = "CARD_RECEIPT"
        if len(naver) >= 3 or (title and len(naver) >= 2):
            return ClassificationResult(
                platform=Platform.NAVER,
                document_type=title or "CARD_RECEIPT",
                confidence=min(1.0, 0.52 + len(naver) * 0.09 + (0.08 if title else 0)),
                matched_markers=([title] if title else []) + naver,
            )
        if text.strip():
            return ClassificationResult(
                platform=Platform.GENERIC,
                document_type="GENERIC_RECEIPT",
                confidence=0.35,
                matched_markers=[],
            )
        return ClassificationResult(
            platform=Platform.UNKNOWN,
            document_type=None,
            confidence=0.0,
            matched_markers=[],
        )

