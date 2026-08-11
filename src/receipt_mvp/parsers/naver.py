from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from receipt_mvp.classifiers import ClassificationResult
from receipt_mvp.models import Amounts, LineItem, OcrToken, PageExtraction, Party, PaymentInfo, Platform, Transaction
from receipt_mvp.normalizers import normalize_business_number, normalize_datetime, normalize_money, normalize_text
from receipt_mvp.parsers.base import ParseResult, ReceiptParser
from receipt_mvp.parsers.common import label_matches, make_evidence


@dataclass(slots=True)
class LocatedValue:
    label: str
    raw_value: str | None
    confidence: float | None
    bbox: tuple[float, float, float, float] | None


class NaverParser(ReceiptParser):
    name = "NaverParser/1.0"
    LABELS = (
        "카드사/승인번호",
        "카드번호(유효기간)",
        "거래종류/할부",
        "결제일자",
        "상품명",
        "상품 주문번호",
        "판매자상호",
        "대표자명",
        "사업자등록번호",
        "전화번호",
        "사업장주소",
        "가맹점명",
        "가맹점번호",
        "주소",
        "승인금액",
        "공급가액",
        "부가세액",
        "봉사료",
        "합계",
    )
    HEADERS = ("판매자 정보", "가맹점 정보", "금액")

    def parse(self, page: PageExtraction, classification: ClassificationResult) -> ParseResult:
        if classification.platform != Platform.NAVER:
            raise ValueError("NaverParser에는 네이버 문서만 전달할 수 있습니다.")
        located = self._extract_values(page)
        payment_part = located.get("카드사/승인번호")
        issuer, approval = self._split_pair(payment_part.raw_value if payment_part else None)
        trade_part = located.get("거래종류/할부")
        payment_method, installment = self._split_pair(trade_part.raw_value if trade_part else None)
        transaction = Transaction(
            occurred_at=normalize_datetime(self._raw(located, "결제일자")),
            order_number=normalize_text(self._raw(located, "상품 주문번호")),
            approval_number=normalize_text(approval),
            evidence_type="신용카드 매출전표",
            payment=PaymentInfo(
                card_issuer=normalize_text(issuer),
                masked_card_number=self._card_only(self._raw(located, "카드번호(유효기간)")),
                payment_method=normalize_text(payment_method),
                installment=normalize_text(installment),
            ),
            items=[LineItem(name=normalize_text(self._raw(located, "상품명")))]
            if self._raw(located, "상품명")
            else [],
            seller=Party(
                name=normalize_text(self._raw(located, "판매자상호", "seller")),
                representative_name=normalize_text(self._raw(located, "대표자명", "seller")),
                business_registration_number=normalize_business_number(
                    self._raw(located, "사업자등록번호", "seller")
                ),
                phone_number=normalize_text(self._raw(located, "전화번호", "seller")),
                address=normalize_text(self._raw(located, "사업장주소", "seller")),
            ),
            merchant=Party(
                name=normalize_text(self._raw(located, "가맹점명", "merchant")),
                representative_name=normalize_text(self._raw(located, "대표자명", "merchant")),
                merchant_number=normalize_text(self._raw(located, "가맹점번호", "merchant")),
                business_registration_number=normalize_business_number(
                    self._raw(located, "사업자등록번호", "merchant")
                ),
                address=normalize_text(self._raw(located, "주소", "merchant")),
            ),
            amounts=Amounts(
                supply_amount=normalize_money(self._raw(located, "공급가액")),
                tax_exempt_amount=None,
                vat_amount=normalize_money(self._raw(located, "부가세액")),
                service_charge=normalize_money(self._raw(located, "봉사료")),
                approved_amount=normalize_money(self._raw(located, "승인금액")),
                total_amount=normalize_money(self._raw(located, "합계")),
            ),
            confidence=self._transaction_confidence(located, classification.confidence),
        )
        evidence = self._make_evidence(page, transaction, located)
        return ParseResult(transactions=[transaction], field_evidence=evidence, parser_name=self.name)

    def _extract_values(self, page: PageExtraction) -> dict[str, LocatedValue]:
        if not page.tokens:
            return self._extract_from_lines(page.raw_text)
        tokens = [token for token in page.tokens if token.text.strip()]
        tokens.sort(key=lambda token: self._sort_key(token))
        headings = self._heading_positions(tokens)
        values: dict[str, LocatedValue] = {}
        for index, token in enumerate(tokens):
            label = self._canonical_label(token.text)
            if not label:
                continue
            section = self._section_for_token(token, headings)
            key = self._key(label, section)
            value_token = self._nearest_value_token(token, tokens, index)
            values[key] = LocatedValue(
                label=label,
                raw_value=value_token.text.strip() if value_token else None,
                confidence=self._combine_confidence(token, value_token),
                bbox=value_token.bbox if value_token else token.bbox,
            )
        return values

    def _extract_from_lines(self, text: str) -> dict[str, LocatedValue]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        values: dict[str, LocatedValue] = {}
        section = "top"
        for index, line in enumerate(lines):
            for header, section_name in (("판매자 정보", "seller"), ("가맹점 정보", "merchant"), ("금액", "amount")):
                if label_matches(line, header, 0.82):
                    section = section_name
            label = self._canonical_label(line)
            if not label:
                continue
            value = lines[index + 1] if index + 1 < len(lines) and not self._canonical_label(lines[index + 1]) else None
            values[self._key(label, section)] = LocatedValue(label, value, None, None)
        return values

    def _nearest_value_token(self, label: OcrToken, tokens: list[OcrToken], label_index: int) -> OcrToken | None:
        if label.bbox:
            lx1, ly1, lx2, ly2 = label.bbox
            height = max(10.0, ly2 - ly1)
            candidates = []
            for token in tokens:
                if token is label or not token.bbox or self._canonical_label(token.text) or self._is_header(token.text):
                    continue
                tx1, ty1, tx2, ty2 = token.bbox
                vertical_gap = abs(((ty1 + ty2) / 2) - ((ly1 + ly2) / 2))
                if tx1 >= lx2 - 5 and vertical_gap <= max(28.0, height * 1.1):
                    candidates.append((vertical_gap, tx1 - lx2, token))
            if candidates:
                return min(candidates, key=lambda item: (item[0], item[1]))[2]
        for token in tokens[label_index + 1 : label_index + 4]:
            if not self._canonical_label(token.text) and not self._is_header(token.text):
                return token
        return None

    def _heading_positions(self, tokens: list[OcrToken]) -> dict[str, float]:
        headings: dict[str, float] = {}
        for token in tokens:
            for header, section in (("판매자 정보", "seller"), ("가맹점 정보", "merchant"), ("금액", "amount")):
                if label_matches(token.text, header, 0.78):
                    headings[section] = self._y(token)
        return headings

    def _section_for_token(self, token: OcrToken, headings: dict[str, float]) -> str:
        y = self._y(token)
        seller = headings.get("seller", float("inf"))
        merchant = headings.get("merchant", float("inf"))
        amount = headings.get("amount", float("inf"))
        if seller < y < merchant:
            return "seller"
        if merchant < y < amount:
            return "merchant"
        if y > amount:
            return "amount"
        return "top"

    def _canonical_label(self, value: str) -> str | None:
        for label in self.LABELS:
            if label_matches(value, label):
                return label
        return None

    def _is_header(self, value: str) -> bool:
        return any(label_matches(value, header, 0.78) for header in self.HEADERS)

    @staticmethod
    def _key(label: str, section: str) -> str:
        if label in {"대표자명", "사업자등록번호", "주소"}:
            return f"{section}:{label}"
        return label

    @staticmethod
    def _raw(located: dict[str, LocatedValue], label: str, section: str | None = None) -> str | None:
        key = f"{section}:{label}" if section and label in {"대표자명", "사업자등록번호", "주소"} else label
        value = located.get(key)
        return value.raw_value if value else None

    @staticmethod
    def _split_pair(value: str | None) -> tuple[str | None, str | None]:
        if not value:
            return None, None
        parts = [part.strip() for part in value.split("/", 1)]
        return (parts[0], parts[1]) if len(parts) == 2 else (None, parts[0])

    @staticmethod
    def _card_only(value: str | None) -> str | None:
        if not value:
            return None
        return value.split("(", 1)[0].strip()

    @staticmethod
    def _sort_key(token: OcrToken) -> tuple[float, float]:
        if not token.bbox:
            return float("inf"), float("inf")
        return token.bbox[1], token.bbox[0]

    @staticmethod
    def _y(token: OcrToken) -> float:
        return token.bbox[1] if token.bbox else float("inf")

    @staticmethod
    def _combine_confidence(label: OcrToken, value: OcrToken | None) -> float | None:
        scores = [score for score in (label.confidence, value.confidence if value else None) if score is not None]
        return mean(scores) if scores else None

    @staticmethod
    def _transaction_confidence(located: dict[str, LocatedValue], classification_confidence: float) -> float:
        scores = [value.confidence for value in located.values() if value.confidence is not None]
        return min(classification_confidence, mean(scores)) if scores else classification_confidence

    def _make_evidence(
        self,
        page: PageExtraction,
        transaction: Transaction,
        located: dict[str, LocatedValue],
    ) -> list:
        mapping = {
            "결제일자": ("occurred_at", transaction.occurred_at, "parse_datetime"),
            "상품 주문번호": ("order_number", transaction.order_number, None),
            "상품명": ("items[0].name", transaction.items[0].name if transaction.items else None, "join_lines"),
            "승인금액": ("amounts.approved_amount", transaction.amounts.approved_amount, "parse_krw"),
            "공급가액": ("amounts.supply_amount", transaction.amounts.supply_amount, "parse_krw"),
            "부가세액": ("amounts.vat_amount", transaction.amounts.vat_amount, "parse_krw"),
            "봉사료": ("amounts.service_charge", transaction.amounts.service_charge, "parse_krw"),
            "합계": ("amounts.total_amount", transaction.amounts.total_amount, "parse_krw"),
            "판매자상호": ("seller.name", transaction.seller.name, None),
            "seller:대표자명": ("seller.representative_name", transaction.seller.representative_name, None),
            "seller:사업자등록번호": (
                "seller.business_registration_number",
                transaction.seller.business_registration_number,
                "digits_only",
            ),
            "전화번호": ("seller.phone_number", transaction.seller.phone_number, None),
            "사업장주소": ("seller.address", transaction.seller.address, None),
            "가맹점명": ("merchant.name", transaction.merchant.name, None),
            "merchant:대표자명": ("merchant.representative_name", transaction.merchant.representative_name, None),
            "가맹점번호": ("merchant.merchant_number", transaction.merchant.merchant_number, None),
            "merchant:사업자등록번호": (
                "merchant.business_registration_number",
                transaction.merchant.business_registration_number,
                "digits_only",
            ),
            "merchant:주소": ("merchant.address", transaction.merchant.address, None),
        }
        evidence = []
        for key, (path, normalized, transform) in mapping.items():
            value = located.get(key)
            if not value:
                continue
            evidence.append(
                make_evidence(
                    transaction.transaction_id,
                    value.label,
                    path,
                    value.raw_value,
                    normalized,
                    self.name,
                    page.method,
                    confidence=value.confidence,
                    bbox=value.bbox,
                    transform=transform,
                )
            )
        return evidence

