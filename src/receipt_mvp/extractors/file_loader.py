from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from receipt_mvp.config.settings import DEFAULT_SETTINGS, Settings


class UnsupportedFileError(ValueError):
    pass


class FileDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    name: str
    suffix: str
    size: int
    sha256: str
    duplicate_of: str | None = None


class FileLoader:
    def __init__(self, settings: Settings = DEFAULT_SETTINGS) -> None:
        self.settings = settings

    def describe(self, path: str | Path) -> FileDescriptor:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {source.name}")
        suffix = source.suffix.lower()
        if suffix not in self.settings.supported_extensions:
            raise UnsupportedFileError(
                f"지원하지 않는 파일 형식입니다: {suffix or '(확장자 없음)'}"
            )
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return FileDescriptor(
            path=str(source),
            name=source.name,
            suffix=suffix,
            size=source.stat().st_size,
            sha256=digest.hexdigest().upper(),
        )

    def describe_many(self, paths: list[str | Path]) -> list[FileDescriptor]:
        descriptors: list[FileDescriptor] = []
        seen_hashes: dict[str, str] = {}
        for path in paths:
            descriptor = self.describe(path)
            if descriptor.sha256 in seen_hashes:
                descriptor.duplicate_of = seen_hashes[descriptor.sha256]
            else:
                seen_hashes[descriptor.sha256] = descriptor.path
            descriptors.append(descriptor)
        return descriptors

