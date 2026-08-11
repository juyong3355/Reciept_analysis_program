from __future__ import annotations

from receipt_mvp.classifiers import ClassificationResult
from receipt_mvp.models import Amounts, LineItem, PageExtraction, Party, PaymentInfo, Platform, Transaction
from receipt_mvp.normalizers import normalize_business_number, normalize_datetime, normalize_money, normalize_text
from receipt_mvp.parsers.base import ParseResult, ReceiptParser
from receipt_mvp.parsers.common import make_evidence


class CoupangParser(ReceiptParser):
    name = "CoupangParser/1.0"
    LABELS = {
        "카드종류",
        "거래종류",
        "할부개월",
        "카드번호",
        "거래일시",
        "승인번호",
        "주문번호",
        "상품명",
        "과세금액",
        "비과세금액",
        "부가세",
        "합계금액",
        "판매자상호",
        "판매자 사업자등록번호",
        "판매자주소",
    }
    SECTION_HEADERS = {"결제정보", "구매정보", "이용상점정보"}

    def parse(self, page: PageExtraction, classification: ClassificationResult) -> ParseResult:
        if classification.platform != Platform.COUPANG:
            raise ValueError("CoupangParser에는 쿠팡 문서만 전달할 수 있습니다.")
        values = self._collect_values(page.raw_text)
        transaction = Transaction(
            occurred_at=normalize_datetime(values.get("거래일시")),
            order_number=normalize_text(values.get("주문번호")),
            approval_number=normalize_text(values.get("승인번호")),
            evidence_type="신용카드 매출전표",
            payment=PaymentInfo(
                card_issuer=normalize_text(values.get("카드종류")),
                masked_card_number=normalize_text(values.get("카드번호")),
                installment=normalize_text(values.get("할부개월")),
                payment_method=normalize_text(values.get("거래종류")),
            ),
            items=[LineItem(name=normalize_text(values.get("상품명")))] if values.get("상품명") else [],
            seller=Party(
                name=normalize_text(values.get("판매자상호")),
                business_registration_number=normalize_business_number(values.get("판매자 사업자등록번호")),
                address=normalize_text(values.get("판매자주소")),
            ),
            amounts=Amounts(
                taxable_amount_raw=normalize_money(values.get("과세금액")),
                tax_exempt_amount=normalize_money(values.get("비과세금액")),
                vat_amount=normalize_money(values.get("부가세")),
                total_amount=normalize_money(values.get("합계금액")),
            ),
            confidence=classification.confidence,
        )
        amounts = transaction.amounts
        if all(
            value is not None
            for value in (
                amounts.taxable_amount_raw,
                amounts.tax_exempt_amount,
                amounts.vat_amount,
                amounts.total_amount,
            )
        ) and abs(
            amounts.taxable_amount_raw
            + amounts.tax_exempt_amount
            + amounts.vat_amount
            - amounts.total_amount
        ) <= 1:
            amounts.supply_amount = amounts.taxable_amount_raw

        evidence: list = []
        mapping = {
            "카드종류": ("payment.card_issuer", transaction.payment.card_issuer, None),
            "거래종류": ("payment.payment_method", transaction.payment.payment_method, None),
            "할부개월": ("payment.installment", transaction.payment.installment, None),
            "카드번호": ("payment.masked_card_number", transaction.payment.masked_card_number, None),
            "거래일시": ("occurred_at", transaction.occurred_at, "parse_datetime"),
            "승인번호": ("approval_number", transaction.approval_number, None),
            "주문번호": ("order_number", transaction.order_number, None),
            "상품명": ("items[0].name", transaction.items[0].name if transaction.items else None, "join_lines"),
            "과세금액": ("amounts.taxable_amount_raw", amounts.taxable_amount_raw, "parse_krw"),
            "비과세금액": ("amounts.tax_exempt_amount", amounts.tax_exempt_amount, "parse_krw"),
            "부가세": ("amounts.vat_amount", amounts.vat_amount, "parse_krw"),
            "합계금액": ("amounts.total_amount", amounts.total_amount, "parse_krw"),
            "판매자상호": ("seller.name", transaction.seller.name, None),
            "판매자 사업자등록번호": (
                "seller.business_registration_number",
                transaction.seller.business_registration_number,
                "digits_only",
            ),
            "판매자주소": ("seller.address", transaction.seller.address, "join_lines"),
        }
        for label, (path, normalized, transform) in mapping.items():
            if label in values:
                evidence.append(
                    make_evidence(
                        transaction.transaction_id,
                        label,
                        path,
                        values[label],
                        normalized,
                        self.name,
                        page.method,
                        confidence=1.0,
                        transform=transform,
                    )
                )
        if amounts.supply_amount is not None:
            evidence.append(
                make_evidence(
                    transaction.transaction_id,
                    "과세금액",
                    "amounts.supply_amount",
                    values.get("과세금액"),
                    amounts.supply_amount,
                    self.name,
                    page.method,
                    confidence=1.0,
                    transform="coupang_taxable_amount_promotion_after_amount_validation",
                )
            )
        return ParseResult(transactions=[transaction], field_evidence=evidence, parser_name=self.name)

    def _collect_values(self, text: str) -> dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        values: dict[str, str] = {}
        index = 0
        while index < len(lines):
            label = lines[index]
            if label not in self.LABELS:
                index += 1
                continue
            index += 1
            collected: list[str] = []
            while index < len(lines):
                next_line = lines[index]
                if next_line in self.LABELS or next_line in self.SECTION_HEADERS:
                    break
                if next_line.startswith("위 신용카드 매출전표"):
                    break
                collected.append(next_line)
                index += 1
            values[label] = " ".join(collected).strip()
        return values

