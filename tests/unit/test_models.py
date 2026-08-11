from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from receipt_mvp.models import (
    Amounts,
    DocumentInfo,
    ExtractionMethod,
    LineItem,
    PageExtraction,
    Party,
    PaymentInfo,
    Platform,
    ReceiptRecord,
    Transaction,
)


def make_record() -> ReceiptRecord:
    document = DocumentInfo(
        source_file_name="synthetic.pdf",
        source_file_path="C:/synthetic.pdf",
        file_sha256="a" * 64,
        page_number=1,
        platform=Platform.COUPANG,
        extraction_method=ExtractionMethod.PDF_TEXT,
    )
    extraction = PageExtraction(
        source_path="C:/synthetic.pdf",
        page_number=1,
        method=ExtractionMethod.PDF_TEXT,
        raw_text="synthetic",
    )
    return ReceiptRecord(document=document, extraction=extraction)


def test_zero_and_missing_amount_are_distinct() -> None:
    amounts = Amounts(vat_amount=0, tax_exempt_amount=None)
    payload = amounts.model_dump()
    assert payload["vat_amount"] == 0
    assert payload["tax_exempt_amount"] is None


def test_transaction_supports_multiple_items() -> None:
    transaction = Transaction(
        occurred_at=datetime(2026, 1, 2, 3, 4, 5),
        items=[LineItem(name="A"), LineItem(name="B")],
    )
    assert [item.name for item in transaction.items] == ["A", "B"]


def test_seller_and_merchant_are_independent() -> None:
    transaction = Transaction(
        seller=Party(name="판매자", business_registration_number="0000000000"),
        merchant=Party(name="가맹점", business_registration_number="1111111111"),
    )
    assert transaction.seller is not transaction.merchant
    assert transaction.seller.name == "판매자"
    assert transaction.merchant.name == "가맹점"


def test_full_card_number_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PaymentInfo(masked_card_number="1234-5678-9012-3456")


def test_masked_card_number_is_allowed() -> None:
    payment = PaymentInfo(masked_card_number="1234-****-****-3456")
    assert payment.masked_card_number.endswith("3456")


def test_receipt_record_serializes_and_emits_schema() -> None:
    record = make_record()
    assert record.model_dump(mode="json")["document"]["page_number"] == 1
    schema = ReceiptRecord.model_json_schema()
    assert schema["title"] == "ReceiptRecord"
    assert "document" in schema["properties"]

