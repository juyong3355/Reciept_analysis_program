from __future__ import annotations

from receipt_mvp.config.settings import DEFAULT_SETTINGS, Settings
from receipt_mvp.models import (
    Platform,
    ProcessingStatus,
    ReceiptRecord,
    Severity,
    Transaction,
    ValidationIssue,
    ValidationStatus,
)
from receipt_mvp.validators.business_number import business_number_checksum_valid


class RecordValidator:
    def __init__(self, settings: Settings = DEFAULT_SETTINGS) -> None:
        self.settings = settings

    def validate(self, record: ReceiptRecord) -> ReceiptRecord:
        issues = [issue for issue in record.validation_issues if issue.code.startswith("FILE_")]
        if record.extraction.error_code:
            issues.append(
                self._issue(
                    record.extraction.error_code,
                    Severity.ERROR,
                    None,
                    self._extraction_message(record.extraction.error_code),
                )
            )
            record.document.processing_status = ProcessingStatus.FAILED
            record.validation_issues = self._deduplicate(issues)
            return record
        if not record.transactions:
            issues.append(self._issue("NO_TRANSACTION", Severity.ERROR, None, "거래 정보를 찾지 못했습니다."))
            record.document.processing_status = ProcessingStatus.REVIEW_REQUIRED
            record.validation_issues = self._deduplicate(issues)
            return record
        for transaction in record.transactions:
            transaction_issues = self._validate_transaction(record, transaction)
            issues.extend(transaction_issues)
            transaction.validation_status = (
                ValidationStatus.REVIEW_REQUIRED if transaction_issues else ValidationStatus.NORMAL
            )
        record.validation_issues = self._deduplicate(issues)
        record.document.processing_status = (
            ProcessingStatus.REVIEW_REQUIRED
            if record.validation_issues
            else ProcessingStatus.COMPLETED
        )
        return record

    def _validate_transaction(
        self,
        record: ReceiptRecord,
        transaction: Transaction,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        required = {
            "occurred_at": transaction.occurred_at,
            "seller.name": transaction.seller.name if transaction.seller else None,
            "amounts.total_amount": transaction.amounts.total_amount,
        }
        for path, value in required.items():
            if value is None or value == "":
                issues.append(
                    self._issue(
                        "REQUIRED_FIELD_MISSING",
                        Severity.WARNING,
                        path,
                        f"필수 항목을 확인해 주세요: {path}",
                    )
                )
        issues.extend(self._validate_amounts(record.document.platform, transaction))
        for role, party in (("seller", transaction.seller), ("merchant", transaction.merchant)):
            if not party or not party.business_registration_number:
                continue
            valid = business_number_checksum_valid(party.business_registration_number)
            if valid is False:
                issues.append(
                    self._issue(
                        "BUSINESS_NUMBER_CHECKSUM",
                        Severity.WARNING,
                        f"{role}.business_registration_number",
                        "사업자등록번호를 원본과 비교해 주세요.",
                    )
                )
        critical_paths = {
            "approval_number",
            "amounts.total_amount",
            "amounts.approved_amount",
            "seller.business_registration_number",
            "merchant.business_registration_number",
        }
        for evidence in record.field_evidence:
            if evidence.transaction_id != transaction.transaction_id or evidence.confidence is None:
                continue
            threshold = (
                self.settings.critical_confidence_threshold
                if evidence.standard_path in critical_paths
                else self.settings.general_confidence_threshold
            )
            if evidence.confidence < threshold:
                issues.append(
                    self._issue(
                        "LOW_CONFIDENCE",
                        Severity.WARNING,
                        evidence.standard_path,
                        "인식 신뢰도가 낮아 원본 확인이 필요합니다.",
                        evidence.confidence,
                    )
                )
        return issues

    def _validate_amounts(self, platform: Platform, transaction: Transaction) -> list[ValidationIssue]:
        amounts = transaction.amounts
        tolerance = self.settings.amount_tolerance_krw
        issues: list[ValidationIssue] = []
        if platform == Platform.COUPANG:
            values = (
                amounts.taxable_amount_raw,
                amounts.tax_exempt_amount,
                amounts.vat_amount,
                amounts.total_amount,
            )
            if any(value is None for value in values):
                issues.append(
                    self._issue(
                        "REQUIRED_FIELD_MISSING",
                        Severity.WARNING,
                        "amounts",
                        "쿠팡 금액 검증에 필요한 항목이 누락되었습니다.",
                    )
                )
            elif abs(values[0] + values[1] + values[2] - values[3]) > tolerance:
                issues.append(
                    self._issue(
                        "AMOUNT_MISMATCH",
                        Severity.WARNING,
                        "amounts.total_amount",
                        "과세금액, 비과세금액, 부가세와 합계금액이 일치하지 않습니다.",
                    )
                )
        elif platform == Platform.NAVER:
            values = (
                amounts.supply_amount,
                amounts.vat_amount,
                amounts.service_charge,
                amounts.approved_amount,
                amounts.total_amount,
            )
            if any(value is None for value in values):
                issues.append(
                    self._issue(
                        "REQUIRED_FIELD_MISSING",
                        Severity.WARNING,
                        "amounts",
                        "네이버 금액 검증에 필요한 항목이 누락되었습니다.",
                    )
                )
            else:
                if abs(values[0] + values[1] + values[2] - values[3]) > tolerance:
                    issues.append(
                        self._issue(
                            "AMOUNT_MISMATCH",
                            Severity.WARNING,
                            "amounts.approved_amount",
                            "공급가액, 부가세액, 봉사료와 승인금액이 일치하지 않습니다.",
                        )
                    )
                if abs(values[3] - values[4]) > tolerance:
                    issues.append(
                        self._issue(
                            "AMOUNT_MISMATCH",
                            Severity.WARNING,
                            "amounts.total_amount",
                            "승인금액과 합계금액이 일치하지 않습니다.",
                        )
                    )
        return issues

    @staticmethod
    def _issue(
        code: str,
        severity: Severity,
        field_path: str | None,
        message: str,
        confidence: float | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            code=code,
            severity=severity,
            field_path=field_path,
            message=message,
            confidence=confidence,
        )

    @staticmethod
    def _deduplicate(issues: list[ValidationIssue]) -> list[ValidationIssue]:
        unique: dict[tuple[str, str | None, str], ValidationIssue] = {}
        for issue in issues:
            unique[(issue.code, issue.field_path, issue.message)] = issue
        return list(unique.values())

    @staticmethod
    def _extraction_message(code: str) -> str:
        messages = {
            "PDF_OPEN_FAILED": "PDF 파일을 열 수 없습니다.",
            "PAGE_EXTRACTION_FAILED": "PDF 페이지를 읽는 중 오류가 발생했습니다.",
            "IMAGE_OPEN_FAILED": "이미지 파일을 열 수 없습니다.",
            "OCR_NOT_AVAILABLE": "이미지 영수증 처리를 위한 OCR 구성이 필요합니다.",
            "OCR_FAILED": "문자 인식 중 오류가 발생했습니다.",
        }
        return messages.get(code, "문서 추출 중 오류가 발생했습니다.")

