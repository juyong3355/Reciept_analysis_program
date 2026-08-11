from __future__ import annotations

import logging

from receipt_mvp.services.logging_utils import SensitiveDataFilter, redact_sensitive


def test_redact_sensitive_values() -> None:
    text = "사업자 123-45-67890 카드 1234-5678-9012-3456 전화 010-1234-5678 주소=합성시 합성구 1"
    redacted = redact_sensitive(text)
    assert "123-45-67890" not in redacted
    assert "1234-5678-9012-3456" not in redacted
    assert "010-1234-5678" not in redacted
    assert "합성시 합성구 1" not in redacted


def test_logging_filter_redacts_arguments() -> None:
    record = logging.LogRecord("test", logging.INFO, "", 1, "value=%s", ("123-45-67890",), None)
    assert SensitiveDataFilter().filter(record)
    assert "123-45-67890" not in record.getMessage()

