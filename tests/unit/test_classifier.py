from receipt_mvp.classifiers import DocumentClassifier
from receipt_mvp.models import ExtractionMethod, PageExtraction, Platform


def extraction(text: str) -> PageExtraction:
    return PageExtraction(source_path="synthetic", page_number=1, method=ExtractionMethod.PDF_TEXT, raw_text=text)


def test_classifies_coupang() -> None:
    result = DocumentClassifier().classify(
        extraction("결제정보\n구매정보\n이용상점정보\n과세금액\n합계금액")
    )
    assert result.platform == Platform.COUPANG


def test_classifies_naver() -> None:
    result = DocumentClassifier().classify(
        extraction("통합 카드 영수증\n판매자 정보\n가맹점 정보\n승인금액\n공급가액")
    )
    assert result.platform == Platform.NAVER
    assert result.document_type == "INTEGRATED_CARD_RECEIPT"

