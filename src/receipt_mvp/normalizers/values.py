from __future__ import annotations

import re
from datetime import datetime


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized or None


def normalize_money(value: str | int | None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"[Ooㅇ○〇0-9,.\s원₩()+-]+", text):
        text = text.translate(str.maketrans({"O": "0", "o": "0", "ㅇ": "0", "○": "0", "〇": "0"}))
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    amount = int(digits)
    return -amount if negative else amount


def normalize_business_number(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    return digits if len(digits) == 10 else None


DATETIME_FORMATS = (
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y.%m.%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M",
    "%Y.%m.%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)


def normalize_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = normalize_text(value)
    if not text:
        return None
    text = re.sub(r"(?<=\d)\s+(?=\d{1,2}:\d{2})", " ", text)
    for date_format in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    match = re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?", text)
    if match and match.group(0) != text:
        return normalize_datetime(match.group(0))
    return None
