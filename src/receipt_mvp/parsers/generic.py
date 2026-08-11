from __future__ import annotations

import re

from receipt_mvp.classifiers import ClassificationResult
from receipt_mvp.models import Amounts, LineItem, PageExtraction, Transaction
from receipt_mvp.normalizers import normalize_datetime, normalize_money
from receipt_mvp.parsers.base import ParseResult, ReceiptParser


class GenericReceiptParser(ReceiptParser):
    name = "GenericReceiptParser/1.0"

    def parse(self, page: PageExtraction, classification: ClassificationResult) -> ParseResult:
        text = page.raw_text
        total_match = re.search(r"(?:합계|총액|승인금액)\s*[:：]?\s*([\d,]+)\s*원?", text)
        date_match = re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?", text)
        item_match = re.search(r"(?:상품명|품명)\s*[:：]?\s*([^\n]+)", text)
        transaction = Transaction(
            occurred_at=normalize_datetime(date_match.group(0)) if date_match else None,
            items=[LineItem(name=item_match.group(1).strip())] if item_match else [],
            amounts=Amounts(total_amount=normalize_money(total_match.group(1)) if total_match else None),
            confidence=min(0.5, classification.confidence),
        )
        return ParseResult(transactions=[transaction], parser_name=self.name)

