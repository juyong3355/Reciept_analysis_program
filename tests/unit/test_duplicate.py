from copy import deepcopy
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
)
from receipt_mvp.validators import mark_duplicate_candidates


def record(name: str) -> ReceiptRecord:
    return ReceiptRecord(
        document=DocumentInfo(
            source_file_name=name,
            source_file_path=name,
            file_sha256=("a" if name == "a.pdf" else "b") * 64,
            page_number=1,
            platform=Platform.COUPANG,
            extraction_method=ExtractionMethod.PDF_TEXT,
        ),
        extraction=PageExtraction(source_path=name, page_number=1, method=ExtractionMethod.PDF_TEXT),
        transactions=[
            Transaction(
                occurred_at=datetime(2026, 1, 1),
                approval_number="A1",
                seller=Party(name="S", business_registration_number="1234567890"),
                amounts=Amounts(total_amount=1000),
            )
        ],
    )


def test_marks_possible_duplicate() -> None:
    first = record("a.pdf")
    second = record("b.pdf")
    mark_duplicate_candidates([first, second])
    assert not first.validation_issues
    assert any(issue.code == "POSSIBLE_DUPLICATE" for issue in second.validation_issues)

