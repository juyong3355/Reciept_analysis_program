from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from receipt_mvp.classifiers import ClassificationResult
from receipt_mvp.models import FieldEvidence, PageExtraction, Transaction, ValidationIssue


@dataclass(slots=True)
class ParseResult:
    transactions: list[Transaction] = field(default_factory=list)
    field_evidence: list[FieldEvidence] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    parser_name: str = ""


class ReceiptParser(ABC):
    @abstractmethod
    def parse(self, page: PageExtraction, classification: ClassificationResult) -> ParseResult:
        raise NotImplementedError

