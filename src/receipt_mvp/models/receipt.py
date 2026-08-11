from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Platform(StrEnum):
    COUPANG = "COUPANG"
    NAVER = "NAVER"
    GENERIC = "GENERIC"
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(StrEnum):
    PDF_TEXT = "PDF_TEXT"
    OCR = "OCR"
    IMAGE = "IMAGE"
    USER_EDIT = "USER_EDIT"


class ProcessingStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class ValidationStatus(StrEnum):
    NORMAL = "NORMAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class OcrToken(Model):
    text: str
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    line_id: str | None = None


class PageExtraction(Model):
    source_path: str
    page_number: int = Field(ge=1)
    method: ExtractionMethod
    raw_text: str = ""
    tokens: list[OcrToken] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    image_path: str | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    render_dpi: int | None = Field(default=None, ge=72)
    error_code: str | None = None
    error_message: str | None = None


class DocumentInfo(Model):
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    source_file_name: str
    source_file_path: str | None
    file_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    page_number: int = Field(ge=1)
    platform: Platform = Platform.UNKNOWN
    document_type: str | None = None
    extraction_method: ExtractionMethod
    processing_status: ProcessingStatus = ProcessingStatus.PENDING


class PaymentInfo(Model):
    card_issuer: str | None = None
    masked_card_number: str | None = None
    installment: str | None = None
    payment_method: str | None = None

    @field_validator("masked_card_number")
    @classmethod
    def require_masked_card_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = "".join(character for character in value if character.isdigit())
        has_mask = any(character in value for character in ("*", "X", "x", "•"))
        if len(digits) >= 12 and not has_mask:
            raise ValueError("full card numbers are not allowed")
        return value


class LineItem(Model):
    item_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    unit_price: int | None = None
    amount: int | None = None


class Party(Model):
    name: str | None = None
    representative_name: str | None = None
    business_registration_number: str | None = Field(default=None, pattern=r"^[0-9]{10}$")
    phone_number: str | None = None
    address: str | None = None
    merchant_number: str | None = None


class Amounts(Model):
    taxable_amount_raw: int | None = None
    supply_amount: int | None = None
    tax_exempt_amount: int | None = None
    vat_amount: int | None = None
    service_charge: int | None = None
    approved_amount: int | None = None
    total_amount: int | None = None


class FieldEvidence(Model):
    transaction_id: str | None = None
    source_label: str | None = None
    standard_path: str | None = None
    raw_value: Any = None
    normalized_value: Any = None
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    parser: str
    extraction_method: ExtractionMethod
    transform: str | None = None
    user_modified: bool = False


class ValidationIssue(Model):
    code: str
    severity: Severity
    field_path: str | None = None
    message: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    user_modified: bool = False


class Transaction(Model):
    transaction_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime | None = None
    order_number: str | None = None
    approval_number: str | None = None
    evidence_type: str | None = None
    tax_category: str | None = None
    payment: PaymentInfo = Field(default_factory=PaymentInfo)
    items: list[LineItem] = Field(default_factory=list)
    seller: Party | None = None
    merchant: Party | None = None
    amounts: Amounts = Field(default_factory=Amounts)
    confidence: float | None = Field(default=None, ge=0, le=1)
    validation_status: ValidationStatus = ValidationStatus.REVIEW_REQUIRED
    user_modified: bool = False


class ReceiptRecord(Model):
    schema_version: str = "1.0"
    document: DocumentInfo
    extraction: PageExtraction
    transactions: list[Transaction] = Field(default_factory=list)
    field_evidence: list[FieldEvidence] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def overall_status(self) -> ValidationStatus:
        if self.document.processing_status == ProcessingStatus.FAILED:
            return ValidationStatus.ANALYSIS_FAILED
        if not self.transactions:
            return ValidationStatus.REVIEW_REQUIRED
        if any(transaction.validation_status != ValidationStatus.NORMAL for transaction in self.transactions):
            return ValidationStatus.REVIEW_REQUIRED
        return ValidationStatus.NORMAL

    def safe_source_name(self) -> str:
        return Path(self.document.source_file_name).name

