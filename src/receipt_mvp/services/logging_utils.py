from __future__ import annotations

import logging
import re
from typing import Any


BUSINESS_NUMBER = re.compile(r"(?<!\d)\d{3}[- ]?\d{2}[- ]?\d{5}(?!\d)")
CARD_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")
PHONE_NUMBER = re.compile(r"(?<!\d)(?:0\d{1,2})[- ]?\d{3,4}[- ]?\d{4}(?!\d)")
ADDRESS_HINT = re.compile(r"(?:주소|address)\s*[=:]\s*[^,;\n]+", re.IGNORECASE)


def redact_sensitive(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = BUSINESS_NUMBER.sub("***-**-*****", value)
    value = CARD_NUMBER.sub("[MASKED_CARD]", value)
    value = PHONE_NUMBER.sub("[MASKED_PHONE]", value)
    value = ADDRESS_HINT.sub("주소=[MASKED_ADDRESS]", value)
    return value


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.msg)
        if isinstance(record.args, dict):
            record.args = {key: redact_sensitive(value) for key, value in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(redact_sensitive(value) for value in record.args)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SensitiveDataFilter())
    han�m4����k�w��us.value == "ANALYSIS_FAILED" for record in records)
        self.result_summary.setText(f"총 {len(records)}건 · 정상 {normal} · 확인 필요 {review} · 실패 {failed}")
        self.progress_bar.setValue(100)
        self.progress_label.setText("분석 완료")
        self.analyze_button.setEnabled(True)
        self.export_button.setEnabled(bool(records))
        self.tabs.setCurrentWidget(self.results_tab)
        self.statusBar().showMessage("분석이 완료되었습니다. 확인이 필요한 항목을 검토하세요.")

    def _analysis_failed(self, traceback_text: str) -> None:
        self.analyze_button.setEnabled(True)
        self.progress_label.setText("분석 중 오류")
        QMessageBox.critical(self, "분석 오류", "분석을 완료하지 못했습니다. 로그를 확인해 주세요.")

    def _selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        indexes = self.results_table.selectionModel().selectedRows()
        if not indexes:
            return
        source = self.proxy_model.mapToSource(indexes[0])
        record = self.table_model.record_for_row(source.row())
        self._show_preview(record)

    def _show_preview(self, record: ReceiptRecord) -> None:
        image_path = record.extraction.image_path
        if not image_path:
            image_path = self._render_preview(record)
        if not image_path or not Path(image_path).is_file():
            self.preview_label.setText("원본 미리보기를 만들 수 없습니다.")
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("이미지를 표시할 수 없습니다.")
            return
        scaled = pixmap.scaled(820, 1120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        self.preview_label.resize(scaled.size())

    def _render_preview(self, record: ReceiptRecord) -> str | None:
        source = record.document.source_file_path
        if not source or Path(source).suffix.lower() != ".pdf":
            return source
        try:
            document = fitz.open(source)
            page = document.load_page(record.document.page_number - 1)
            output = Path(self.temp_dir.name) / f"preview-{record.document.document_id}.png"
            page.get_pixmap(dpi=130, alpha=False).save(output)
            document.close()
            return str(output)
        except Exception:
            return None

    def selected_export_columns(self) -> list[str] | None:
        if self.mode_default.isChecked():
            return []
        if self.mode_all.isChecked():
            return None
        return [key for key, checkbox in self.column_checks.items() if checkbox.isChecked()]

    def export_excel(self) -> None:
        if not self.records:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel 저장",
            "영수증_정리.xlsx",
            "Excel 통합 문서 (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            from receipt_mvp.exporters.excel import ExcelExporter

            ExcelExporter().export(self.records, path, self.selected_export_columns())
            QMessageBox.information(self, "저장 완료", "Excel 파일을 저장했습니다.")
            self.statusBar().showMessage(f"저장 완료: {Path(path).name}")
        except Exception as error:
            QMessageBox.critical(self, "저장 오류", f"Excel 파일을 저장하지 못했습니다.\n{error}")
