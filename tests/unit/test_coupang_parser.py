from receipt_mvp.classifiers import DocumentClassifier
from receipt_mvp.models import ExtractionMethod, PageExtraction
from receipt_mvp.parsers import CoupangParser


SYNTHETIC = """결제정보
카드종류
합성카드
거래종류
신용거래
할부개월
일시불
카드번호
1234******5678
거래일시
2026/01/02 03:04:05
승인번호
SYN-001
구매정보
주문번호
ORDER-001
상품명
합성 사무용품
두 번째 줄
과세금액
10,000원
비과세금액
0원
부가세
1,000원
합계금액
11,000원
이용상점정보
판매자상호
합성상점
판매자 사업자등록번호
123-45-67890
판매자주소
합성시 합성구
"""


def test_coupang_parser_maps_and_promotes_taxable_amount() -> None:
    page = PageExtraction(
        source_path="synthetic.pdf",
        page_number=1,
        method=ExtractionMethod.PDF_TEXT,
        raw_text=SYNTHETIC,
    )
    result = CoupangParser().parse(page, DocumentClassifier().classify(page))
    transaction = result.transactions[0]
    assert transaction.amounts.supply_amount == 10000
    assert transaction.amounts.tax_exempt_amount == 0
    assert transaction.items[0].name == "합성 사무용품 두 번째 줄"
    assert transaction.seller.business_registration_number == "1234567890"
    assert any(item.standard_path == "amounts.supply_amount" for item in result.field_evidence)


def test_coupang_parser_does_not_promote_invalid_amounts() -> None:
    page = PageExtraction(
        source_path="synthetic.pdf",
        page_number=1,
        method=ExtractionMethod.PDF_TEXT,
        raw_text=SYNTHETIC.replace("11,000원", "12,000원"),
    )
    transaction = CoupangParser().parse(page, DocumentClassifier().classify(page)).transactions[0]
    assert transaction.amounts.taxable_amount_raw == 10000
    assert transaction.amounts.supply_amount is None

