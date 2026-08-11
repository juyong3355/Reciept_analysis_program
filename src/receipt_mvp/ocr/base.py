from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from receipt_mvp.models import OcrToken


class OcrUnavailableError(RuntimeError):
    pass


class OcrResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    tokens: list[OcrToken] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class OcrAdapter(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, image_path: str | Path) -> OcrResult:
        raise NotImplementedError


class UnavailableOcrAdapter(OcrAdapter):
    def is_available(self) -> bool:
        return False

    def extract(self, image_path: str | Path) -> OcrResult:
        raise OcrUnavailableError("한국어 OCR 엔진이 설치되지 않았습니다.")

