from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from receipt_mvp.models import ExtractionMethod, FieldEvidence, ReceiptRecord, ValidationStatus
from receipt_mvp.normalizers import normalize_business_number, normalize_datetime, normalize_money
from receipt_mvp.validators import RecordValidator


@dataclass(frozen=True, slots=True)
class Column:
    key: str
    title: str
    editable: bool = False
    width: int = 110


COLUMNS = (
    Column("file", "파일명", width=170),
    Column("page", "원본 페이지", width=90),
    Column("platform", "플랫폼", width=80),
    Column("document_type", "문서 유형", width=120),
    Column("occurred_at", "거래일시", True, 145),
    Column("seller_name", "판매자상호", True, 150),
    Column("seller_business_number", "판매자 사업자번호", True, 135),
    Column("item_name", "상품명", True, 240),
    Column("supply_amount", "공급가액", True, 95),
    Column("tax_exempt_amount", "면세금액", True, 95),
    Column("vat_amount", "부가세액", True, 90),
    Column("service_charge", "봉사료", True, 80),
    Column("total_amount", "합계금액", True, 100),
    Column("confidence", "신뢰도", width=75),
    Column("status", "검증 상태", width=90),
)


class ReceiptTableModel(QAbstractTableModel):
    def __init__(self, records: list[ReceiptRecord] | None = None) -> None:
        super().__init__()
        self.records = records or []
        self.rows: list[tuple[int, int]] = []
        self.validator = RecordValidator()
        self._rebuild_rows()

    def set_records(self, records: list[ReceiptRecord]) -> None:
        self.beginResetModel()
        self.records = records
        self._rebuild_rows()
        self.endResetModel()

    def _rebuild_rows(self) -> None:
        self.rows = []
        for record_index, record in enumerate(self.records):
            if record.transactions:
                self.rows.extend((record_index, index) for index in range(len(record.transactions)))
            else:
                self.rows.append((record_index, -1))

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section].title
        return section + 1

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.isValid() and COLUMNS[index.column()].editable and self.rows[index.row()][1] >= 0:
            flags |= Qt.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        record, transaction = self._objects(index.row())
        column = COLUMNS[index.column()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = self._value(record, transaction, column.key)
            if role == Qt.EditRole:
                if isinstance(value, datetime):
                    return value.strftime("%Y-%m-%d %H:%M:%S")
                return "" if value is None else value
            return self._display(value, column.key)
        if role == Qt.TextAlignmentRole and column.key in {
            "page",
            "supply_amount",
            "tax_exempt_amount",
            "vat_amount",
            "service_charge",
            "total_amount",
            "confidence",
        }:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.UserRole:
            return self._value(record, transaction, column.key)
        if role == Qt.ToolTipRole:
            if column.key == "status" and record.validation_issues:
                return "\n".join(issue.message for issue in record.validation_issues)
            return None
        if role == Qt.ForegroundRole and column.key == "status":
            from PySide6.QtGui import QColor

            status = self._value(record, transaction, "status")
            colors = {
                ValidationStatus.NORMAL: QColor("#087F5B"),
                ValidationStatus.REVIEW_REQUIRED: QColor("#B76E00"),
                ValidationStatus.ANALYSIS_FAILED: QColor("#C92A2A"),
            }
            return colors.get(status)
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if role != Qt.EditRole or not index.isValid() or not COLUMNS[index.column()].editable:
            return False
        record, transaction = self._objects(index.row())
        if transaction is None:
            return False
        key = COLUMNS[index.column()].key
        try:
            normalized = self._normalize_edit(key, value)
            self._assign(transaction, key, normalized)
        except (TypeError, ValueError):
            return False
        transaction.user_modified = True
        record.field_evidence.append(
            FieldEvidence(
                transaction_id=transaction.transaction_id,
                source_label="사용자 수정",
                standard_path=key,
                raw_value=value,
                normalized_value=normalized,
                parser="UserEdit",
                extraction_method=ExtractionMethod.USER_EDIT,
                confidence=1.0,
                user_modified=True,
            )
        )
        self.validator.validate(record)
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), len(COLUMNS) - 1))
        return True

    def record_for_row(self, row: int) -> ReceiptRecord:
        return self.records[self.rows[row][0]]

    def transaction_for_row(self, row: int):
        record, transaction = self._objects(row)
        return transaction

    def _objects(self, row: int):
        record_index, transaction_index = self.rows[row]
        record = self.records[record_index]
        transaction = record.transactions[transaction_index] if transaction_index >= 0 else None
        return record, transaction

    @staticmethod
    def _display(value: Any, key: str) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if key in {"supply_amount", "tax_exempt_amount", "vat_amount", "service_charge", "total_amount"}:
            return f"{value:,}"
        if key == "confidence":
            return f"{value * 100:.0f}%"
        if isinstance(value, ValidationStatus):
            return {
                ValidationStatus.NORMAL: "정상",
                ValidationStatus.REVIEW_REQUIRED: "확인 필요",
                ValidationStatus.ANALYSIS_FAILED: "분석 실패",
            }[value]
        return str(value)

    @staticmethod
    def _value(record: ReceiptRecord, transaction, key: str) -> Any:
        if key == "file":
            return record.document.source_file_name
        if key == "page":
            return record.document.page_number
        if key == "platform":
            return record.document.platform.value
        if key == "document_type":
            return record.document.document_type
        if key == "status":
            return transaction.validation_status if transaction else ValidationStatus.ANALYSIS_FAILED
        if transaction is None:
            return None
        if key == "occurred_at":
            return transaction.occurred_at
        if key == "seller_name":
            return transaction.seller.name if transaction.seller else None
        if key == "seller_business_number":
            return transaction.seller.business_registration_number if transaction.seller else None
        if key == "item_name":
            return transaction.items[0].name if transaction.items else None
        if key in {"supply_amount", "tax_exempt_amount", "vat_amount", "service_charge", "total_amount"}:
            return getattr(transaction.amounts, key)
        if key == "confidence":
            return transaction.confidence
        return None

    @staticmethod
    def _normalize_edit(key: str, value: Any) -> Any:
        text = str(value).strip()
        if key == "occurred_at":
            normalized = normalize_datetime(text)
            if text and normalized is None:
                raise ValueError("invalid date")
            return normalized
        if key == "seller_business_number":
            if not text:
                return None
            normalized = normalize_business_number(text)
            if normalized is None:
                raise ValueError("invalid business number")
            return normalized
        if key in {"supply_amount", "tax_exempt_amount", "vat_amount", "service_charge", "total_amount"}:
            if not text:
                return None
            normalized = normalize_money(text)
            if normalized is None:
                raise ValueError("invalid money")
            return normalized
        return text or None

    @staticmethod
    def _assign(transaction, key: str, value: Any) -> None:
        if key == "occurred_at":
            transaction.occurred_at = value
        elif key == "seller_name":
            if transaction.seller is None:
                from receipt_mvp.models import Party

                transaction.seller = Party()
            transaction.seller.name = value
        elif key == "seller_business_number":
            if transaction.seller is None:
                from receipt_mvp.models import Party

                transaction.seller = Party()
            transaction.seller.business_registration_number = value
        elif key == "item_name":
            if not transaction.items:
                from receipt_mvp.models import LineItem

                transaction.items.append(LineItem())
            transaction.items[0].name = value
        elif key in {"supply_amount", "tax_exempt_amount", "vat_amount", "service_charge", "total_amount"}:
            setattr(transaction.amounts, key, value)
        else:
            raise ValueError(f"unsupported edit: {key}")


class StatusFilterProxyModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self.status_filter = "ALL"

    def set_status_filter(self, status: str) -> None:
        self.status_filter = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if self.status_filter == "ALL":
            return True
        model = self.sourceModel()
        if not isinstance(model, ReceiptTableModel):
            return True
        record = model.record_for_row(source_row)
        transaction = model.transaction_for_row(source_row)
        status = transaction.validation_status if transaction else ValidationStatus.ANALYSIS_FAILED
        return status.value == self.status_filter

