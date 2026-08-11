from __future__ import annotations

from pathlib import Path

import pytest

from receipt_mvp.extractors import FileLoader, UnsupportedFileError


def test_describe_and_detect_duplicate(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    descriptors = FileLoader().describe_many([first, second])
    assert descriptors[0].duplicate_of is None
    assert descriptors[1].duplicate_of == str(first.resolve())
    assert descriptors[0].sha256 == descriptors[1].sha256


def test_unsupported_file_has_clear_error(tmp_path: Path) -> None:
    source = tmp_path / "receipt.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(UnsupportedFileError, match="지원하지 않는"):
        FileLoader().describe(source)

