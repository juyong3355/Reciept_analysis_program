from receipt_mvp.validators import business_number_checksum_valid


def make_valid(prefix: str) -> str:
    assert len(prefix) == 9
    weights = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    digits = [int(value) for value in prefix]
    weighted = sum(number * weight for number, weight in zip(digits, weights, strict=True))
    weighted += (digits[8] * 5) // 10
    return prefix + str((10 - weighted % 10) % 10)


def test_business_number_checksum() -> None:
    valid = make_valid("123456789")
    assert business_number_checksum_valid(valid) is True
    assert business_number_checksum_valid(valid[:-1] + str((int(valid[-1]) + 1) % 10)) is False
    assert business_number_checksum_valid(None) is None

