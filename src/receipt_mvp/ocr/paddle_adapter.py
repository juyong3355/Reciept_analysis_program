from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from statistics import mean
from typing import Any

from receipt_mvp.models import OcrToken
from receipt_mvp.ocr.base import OcrAdapter, OcrResult, OcrUnavailableError


class PaddleOcrAdapter(OcrAdapter):
    def __init__(self, language: str = "korean") -> None:
        self.language = language
        self._engine: Any = None

    def is_available(self) -> bool:
        return importlib.util.find_spec("paddleocr") is not None

    def _get_engine(self) -> Any:
        if not self.is_available():
            raise OcrUnavailableError(
                "PaddleOCR이 설치되지 않았습니다. 'pip install .[ocr]'로 준비해 주세요."
            )
        if self._engine is None:
            os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
            from paddleocr import PaddleOCR

            try:
                self._engine = PaddleOCR(
                    text_detection_model_name="PP-OCRv5_mobile_det",
                    text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=False,
                )
            except TypeError:
                self._engine = PaddleOCR(lang=self.language, use_angle_cls=True, show_log=False)
        return self._engine

    def extract(self, image_path: str | Path) -> OcrResult:
        engine = self._get_engine()
        path = str(Path(image_path))
        if hasattr(engine, "predict"):
            result = engine.predict(path)
            tokens = self._tokens_from_predict(result)
        else:
            result = engine.ocr(path, cls=True)
            tokens = self._tokens_from_legacy(result)
        text = "\n".join(token.text for token in tokens)
        confidences = [token.confidence for token in tokens if token.confidence is not None]
        return OcrResult(
            text=text,
            tokens=tokens,
            confidence=mean(confidences) if confidences else None,
        )

    @staticmethod
    def _bbox_from_polygon(polygon: Any) -> tuple[float, float, float, float] | None:
        try:
            xs = [float(point[0]) for point in polygon]
            ys = [float(point[1]) for point in polygon]
            return min(xs), min(ys), max(xs), max(ys)
        except (TypeError, ValueError, IndexError):
            return None

    def _tokens_from_legacy(self, result: Any) -> list[OcrToken]:
        tokens: list[OcrToken] = []
        pages = result or []
        for page in pages:
            for line_index, line in enumerate(page or []):
                if not line or len(line) < 2:
                    continue
                polygon, value = line[0], line[1]
                text, confidence = value[0], float(value[1])
                tokens.append(
                    OcrToken(
                        text=str(text),
                        bbox=self._bbox_from_polygon(polygon),
                        confidence=confidence,
                        line_id=str(line_index),
                    )
                )
        return tokens

    def _tokens_from_predict(self, result: Any) -> list[OcrToken]:
        tokens: list[OcrToken] = []
        for page in result or []:
            payload = getattr(page, "json", None)
            if callable(payload):
                payload = payload()
            if isinstance(payload, str):
                import json

                payload = json.loads(payload)
            payload = payload or getattr(page, "res", None) or {}
            if isinstance(payload, dict) and "res" in payload:
                payload = payload["res"]
            texts = payload.get("rec_texts", []) if isinstance(payload, dict) else []
            scores = payload.get("rec_scores", []) if isinstance(payload, dict) else []
            polygons = payload.get("rec_polys", []) if isinstance(payload, dict) else []
            for index, text in enumerate(texts):
                score = float(scores[index]) if index < len(scores) else None
                polygon = polygons[index] if index < len(polygons) else None
                tokens.append(
                    OcrToken(
                        text=str(text),
                        bbox=self._bbox_from_polygon(polygon),
                        confidence=score,
                        line_id=str(index),
                    )
                )
        return tokens
