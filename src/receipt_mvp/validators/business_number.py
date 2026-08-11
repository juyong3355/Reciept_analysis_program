from __future__ import annotations

import re


def business_number_checksum_valid(value: str | None) -> bool | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        return False
    numbers = [int(digit) for digit in digits]
    weights = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    weighted = sum(number * weight for number, weight in zip(numbers[:9], weights, strict=True))
    weighted += (numbers[8] * 5) // 10
    expected = (10 - (weighted % 10)) % 10
    return expected == numbers[9]

