from __future__ import annotations

from receipt_mvp.classifiers import DocumentClassifier
from receipt_mvp.models import ExtractionMethod, OcrToken, PageExtraction
from receipt_mvp.parsers import NaverParser


def token(text: str, x: float, y: float, confidence: float = 0.98) -> OcrToken:
    return OcrToken(text=text, bbox=(x, y, x + 220, y + 35), confidence=confidence)


def test_naver_parser_keeps_seller_and_merchant_separate() -> None:
    tokens = [
        token("통합 카드 영수증", 500, 20),
        token("카드사/승인번호", 100, 100), token("합성카드 / APPROVAL-2", 700, 100),
        token("결제일자", 100, 160), token("2026-01-02 03:04:05", 700, 160),
        token("상품명", 100, 220), token("합성 상품", 700, 220),
        token("판매자 정보", 100, 320),
        token("판매자상호", 100, 380), token("합성판매자", 700, 380),
        token("사업자등록번호", 100, 440), token("123-45-67890", 700, 440),
        token("가맹점 정보", 100, 600),
        token("가맹점명", 100, 660), token("합성결제가맹점", 700, 660),
        token("사업자등록번호", 100, 720), token("111-22-33333", 700, 720),
        token("금액", 100, 840),
        token("승인금액", 100, 900), token("22,000", 700, 900),
        token("공급가액", 100, 960), token("20,000", 700, 960),
        token("부가세액", 100, 1020), token("2,000", 700, 1020),
        token("봉사료", 100, 1080), token("0", 700, 1080),
        token("합계", 100, 1140), token("22,000", 700, 1140),
    ]
    page = PageExtraction(
        source_path="synthetic.pdf",
        page_number=1,
        method=ExtractionMethod.OCR,
        raw_text="\n".join(item.text for item in tokens),
        tokens=tokens,
        confidence=0.98,
    )
    result = NaverParser().parse(page, DocumentClassifier().classify(page))
    transaction = result.transactions[0]
    assert transaction.seller.name == "합성판매자"
    assert transaction.merchant.name == "합성결제가맹점"
    assert transaction.seller.business_registration_number == "1234567890"
    assert transaction.merchant.business_registration_number == "1112233333"
    assert transaction.amounts.tax_exempt_amount is None
    assert transaction.amounts.approved_amount == 22000

