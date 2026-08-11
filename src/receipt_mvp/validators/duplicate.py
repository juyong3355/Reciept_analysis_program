from __future__ import annotations

from receipt_mvp.models import ReceiptRecord, Severity, ValidationIssue


def _transaction_key(record: ReceiptRecord, index: int) -> tuple | None:
    transaction = record.transactions[index]
    seller_number = (
        transaction.seller.business_registration_number if transaction.seller else None
    )
    values = (
        record.document.platform,
        transaction.occurred_at,
        transaction.approval_number,
        transaction.amounts.total_amount,
        seller_number,
    )
    return values if all(value is not None for value in values) else None


def mark_duplicate_candidates(records: list[ReceiptRecord]) -> list[ReceiptRecord]:
    seen: dict[tuple, tuple[str, int]] = {}
    for record in records:
        for index, transaction in enumerate(record.transactions):
            key = _transaction_key(record, index)
            if key is None:
                continue
            if key in seen:
                source_document, source_page = seen[key]
                issue = ValidationIssue(
                    code="POSSIBLE_DUPLICATE",
                    severity=Severity.WARNING,
                    field_path=None,
                    message=f"동일 거래 가능성이 있습니다: {source_document} {source_page}쪽",
                )
                if not any(existing.code == issue.code for existing in record.validation_issues):
                    record.validation_issues.append(issue)
                transaction.validation_status = "REVIEW_REQUIRED"
            else:
                seen[key] = (record.document.source_file_name, record.document.page_number)
    return records

