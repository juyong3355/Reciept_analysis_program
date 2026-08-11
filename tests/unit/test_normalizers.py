from datetime import datetime

from receipt_mvp.normalizers import normalize_business_number, normalize_datetime, normalize_money


def test_normalize_money_preserves_zero_and_missing() -> None:
    assert normalize_money("0원") == 0
    assert normalize_money("o") == 0
    assert normalize_money("13,600원") == 13600
    assert normalize_money(None) is None


def test_normalize_datetime_variants() -> None:
    assert normalize_datetime("2026/01/02 03:04:05") == datetime(2026, 1, 2, 3, 4, 5)
    assert normalize_datetime("2026-01-02 03:04:05") == datetime(2026, 1, 2, 3, 4, 5)


def test_normalize_business_number_requires_ten_digits() -> None:
    assert normalize_business_number("123-45-67890") == "1234567890"
    assert normalize_business_number("123") is None
