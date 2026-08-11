from __future__ import annotations

from datetime import datetime

from receipt_mvp.models import (
    Amounts,
    DocumentInfo,
    ExtractionMethod,
    PageExtraction,
    Party,
    Platform,
    ReceiptRecord,
    Transaction,
    ValidationStatus,
)
from receipt_mvp.validators import RecordValidator


def make_record(platform: Platform, amounts: Amounts) -> ReceiptRecord:
    document = DocumentInfo(
        source_file_name="synthetic.pdf",
        source_file_path="C:/synthetic.pdf",
        file_sha256="a" * 64,
        page_number=1,
        platform=platform,
        extraction_method=ExtractionMethod.PDF_TEXT,
    )
    extraction = PageExtraction(
        source_path="C:/synthetic.pdf",
        page_number=1,
        method=ExtractionMethod.PDF_TEXT,
    )
    transaction = Transaction(
        occurred_at=datetime(2026, 1, 1),
        seller=Party(name="합성판매자"),
        amounts=amounts,
    )
    return ReceiptRecord(document=document, extraction=extraction, transactions=[transaction])


def test_valid_coupang_amounts_are_normal() -> None:
    record = make_record(
        Platform.COUPANG,
        Amounts(taxable_amount_raw=10000, tax_exempt_amount=0, vat_amount=1000, total_amount=11000),
    )
    validated = RecordValidator().validate(record)
    assert validated.transactions[0].validation_status == ValidationStatus.NORMAL
    assert not validated.validation_issues


def test_amount_mismatch_requires_review() -> None:
    record = make_record(
        Platform.NAVER,
        Amounts(supply_amount=10000, vat_amount=1000, service_charge=0, approved_amount=12000, total_amount=12000),
    )
    validated = RecordValidator().validate(record)
    assert validated.transactions[0].validation_status == ValidationStatus.REVIEW_REQUIRED
    assert any(issue.code == "AMOUNT_MISMATCH" for issue in validated.validation_issues)


def test_missing_value_is_not_treated_as_zero() -> None:
    record = make_record(
        Platform.COUPANG,
        Amounts(taxable_amount_raw=10000, tax_exempt_amount=None, vat_amount=1000, total_amount=11000),
    )
    validated = RecordValidator().validate(record)
    assert any(issue.code == "REQUIRED_FIELD_MISSING" for issue in validated.validation_issues)

