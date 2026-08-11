from __future__ import annotations

import os
from pathlib import Path

import pytest

from receipt_mvp.classifiers import DocumentClassifier
from receipt_mvp.extractors import DocumentExtractor, FileLoader
from receipt_mvp.models import Platform
from receipt_mvp.parsers import CoupangParser


@pytest.mark.integration
def test_real_coupang_all_pages(tmp_path: Path) -> None:
    sample = os.environ.get("RECEIPT_SAMPLE_COUPANG")
    if not sample:
        pytest.skip("RECEIPT_SAMPLE_COUPANG is not configured")
    pages = DocumentExtractor(tmp_path / "temp").extract(FileLoader().describe(sample))
    assert len(pages) == 18
    classifier = DocumentClassifier()
    for page in pages:
        classification = classifier.classify(page)
        assert classification.platform == Platform.COUPANG
        result = CoupangParser().parse(page, classification)
        transaction = result.transactions[0]
        assert transaction.order_number
        assert transaction.approval_number
        assert transaction.seller and transaction.seller.name
        assert transaction.amounts.total_amount is not None
        assert transaction.amounts.supply_amount is not None

