from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt

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
from receipt_mvp.ui.table_model import COLUMNS, ReceiptTableModel


def make_record() -> ReceiptRecord:
    return ReceiptRecord(
        document=DocumentInfo(
            source_file_name="synthetic.pdf",
            source_file_path="C:/synthetic.pdf",
            file_sha256="a" * 64,
            page_number=1,
            platform=Platform.COUPANG,
            extraction_method=ExtractionMethod.PDF_TEXT,
        ),
        extraction=PageExtraction(
            source_path="C:/synthetic.pdf", page_number=1, method=ExtractionMethod.PDF_TEXT
        ),
        transactions=[
            Transaction(
                occurred_at=datetime(2026, 1, 1),
                seller=Party(name="판매자"),
                amounts=Amounts(
                    taxable_amount_raw=10000,
                    supply_amount=10000,
                    tax_exempt_amount=0,
                    vat_amount=1000,
                    total_amount=11000,
                ),
            )
        ],
    )


def column_index(key: str) -> int:
    return next(index for index, column in enumerate(COLUMNS) if column.key == key)


def test_edit_marks_transaction_and_evidence(qtbot) -> None:
    record = make_record()
    model = ReceiptTableModel([record])
    index = model.index(0, column_index("seller_name"))
    assert model.setData(index, "수정 판매자", Qt.EditRole)
    assert record.transactions[0].seller.name == "수정 판매자"
    assert record.transactions[0].user_modified is True
    assert any(evidence.user_modified for evidence in record.field_evidence)


def test_invalid_money_edit_is_rejected(qtbot) -> None:
    model = ReceiptTableModel([make_record()])
    index = model.index(0, column_index("total_amount"))
    assert not model.setData(index, "금액없음", Qt.EditRole)

