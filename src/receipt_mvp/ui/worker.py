from __future__ import annotations

import traceback
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)


class AnalysisWorker(QRunnable):
    def __init__(self, paths: list[str], service_factory: Callable[[], object]) -> None:
        super().__init__()
        self.paths = paths
        self.service_factory = service_factory
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            service = self.service_factory()
            records = service.process_files(self.paths, self.signals.progress.emit)
            self.signals.completed.emit(records)
        except Exception:
            self.signals.failed.emit(traceback.format_exc())

