"""workers.py — Shared background worker classes for export presenters.

``ExportWorker`` and ``ExportWorkerSignals`` are used by both
``ExportDataPresenter`` (standard exports) and ``AdvancedExportPresenter``
(spec-based exports) so they live in a single shared module.
"""

import traceback
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class ExportWorkerSignals(QObject):
    """Signals emitted by ``ExportWorker`` back to the main thread."""

    finished = pyqtSignal(str, str)  # (human description, output folder path)
    error = pyqtSignal(str)  # error traceback string


class ExportWorker(QRunnable):
    """Runs a single BSP export function off the GUI thread.

    Parameters
    ----------
    fn:
        A zero-argument callable that performs the export.  The caller should
        bind all parameters via a lambda or ``functools.partial`` before
        passing it in.
    description:
        Short human-readable label shown in the status bar on success
        (e.g. ``"CSV (Single)"``).
    output_folder:
        Path to the folder that will contain the exported files, used to open
        the folder in the system file manager after a successful export.
    """

    def __init__(
        self,
        fn: Callable[[], Any],
        description: str,
        output_folder: Path,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._description = description
        self._output_folder = output_folder
        self.signals = ExportWorkerSignals()

    def run(self) -> None:  # noqa: N802
        try:
            self._fn()
            self.signals.finished.emit(self._description, str(self._output_folder))
        except Exception:
            self.signals.error.emit(traceback.format_exc())
