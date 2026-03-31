"""export_data_presenter.py — Presenter for the Export Data panel.

Wires the six export buttons in ``ExportDataView`` to BSP's default export
functions.  Each export runs off the main thread via a ``QRunnable`` so the
GUI stays responsive during file I/O.  On success the output folder is opened
in the system file manager; on failure a modal error dialog is shown.

The project path is pushed in by ``StanPresenter`` (via ``project_path``)
whenever the active project changes — consistent with the pattern used by
``StatementQueuePresenter`` and ``StatementResultPresenter``.
"""

import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QRunnable, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices

from openstan.components import StanErrorMessage

if TYPE_CHECKING:
    from PyQt6.QtCore import QThreadPool

    from openstan.views.export_data_view import ExportDataView


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------


class ExportWorkerSignals(QObject):
    """Signals emitted by ``ExportWorker`` back to the main thread."""

    finished = pyqtSignal(str, str)  # (human description, output folder path)
    error = pyqtSignal(str)  # error message


class ExportWorker(QRunnable):
    """Runs a single BSP export function off the GUI thread.

    Parameters
    ----------
    fn:
        A zero-argument callable that performs the export.  The caller should
        bind ``project_path`` via a lambda or ``functools.partial`` before
        passing it in.
    description:
        Short human-readable label shown in the status bar on success
        (e.g. ``"CSV (Simple)"``).
    output_folder:
        Path to the folder that will contain the exported files, used to open
        the folder in the system file manager after a successful export.
    """

    def __init__(
        self,
        fn: Callable[[], None],
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


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class ExportDataPresenter(QObject):
    """Presenter for the Export Data panel.

    Receives the view and a ``QThreadPool`` at construction time.  The active
    project path is pushed in by ``StanPresenter`` after every project change::

        self.export_data_presenter.project_path = stan.current_project_paths.root
    """

    def __init__(
        self,
        view: "ExportDataView",
        threadpool: "QThreadPool",
    ) -> None:
        super().__init__()
        self.view: "ExportDataView" = view
        self.threadpool: "QThreadPool" = threadpool

        # Set by StanPresenter on every project selection change.
        self.project_path: Path | None = None

        # Error dialog — parented to the view so it is modal to the window.
        self._error_dialog = StanErrorMessage(view)

        # ── Signal wiring ──────────────────────────────────────────────────
        self.view.button_csv_simple.clicked.connect(self._on_csv_simple)
        self.view.button_csv_full.clicked.connect(self._on_csv_full)
        self.view.button_excel_simple.clicked.connect(self._on_excel_simple)
        self.view.button_excel_full.clicked.connect(self._on_excel_full)
        self.view.button_json_simple.clicked.connect(self._on_json_simple)
        self.view.button_json_full.clicked.connect(self._on_json_full)

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    def _all_buttons(self):  # type: ignore[return]
        """Return all six export buttons as a tuple."""
        v = self.view
        return (
            v.button_csv_simple,
            v.button_csv_full,
            v.button_excel_simple,
            v.button_excel_full,
            v.button_json_simple,
            v.button_json_full,
        )

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._all_buttons():
            btn.setEnabled(enabled)

    def _start_export(self, worker: ExportWorker) -> None:
        """Disable UI, show progress bar, and dispatch the worker."""
        self._set_buttons_enabled(False)
        self.view.label_status.setText("")
        self.view.progress_bar.setVisible(True)
        worker.signals.finished.connect(self._on_export_finished)
        worker.signals.error.connect(self._on_export_error)
        self.threadpool.start(worker)

    def _make_worker(
        self,
        fn: Callable[[], None],
        description: str,
        output_folder: Path,
    ) -> ExportWorker:
        return ExportWorker(fn=fn, description=description, output_folder=output_folder)

    def _resolve_project_path(self) -> Path | None:
        """Return the current project path, or None if not set."""
        if self.project_path is None:
            self._error_dialog.showMessage(
                "No project is currently selected. "
                "Please select a project before exporting."
            )
            return None
        return self.project_path

    # ---------------------------------------------------------------------------
    # Slots — one per button
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _on_csv_simple(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "csv"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_csv(type="single", project_path=project_path),
            description="CSV (Single)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    @pyqtSlot()
    def _on_csv_full(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "csv"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_csv(type="multi", project_path=project_path),
            description="CSV (Multi)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    @pyqtSlot()
    def _on_excel_simple(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "excel"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_excel(type="single", project_path=project_path),
            description="Excel (Single)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    @pyqtSlot()
    def _on_excel_full(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "excel"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_excel(type="multi", project_path=project_path),
            description="Excel (Multi)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    @pyqtSlot()
    def _on_json_simple(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "json"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_json(type="single", project_path=project_path),
            description="JSON (Single)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    @pyqtSlot()
    def _on_json_full(self) -> None:
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        output_folder = project_path / "export" / "json"
        worker = self._make_worker(
            fn=lambda: bsp.db.export_json(type="multi", project_path=project_path),
            description="JSON (Multi)",
            output_folder=output_folder,
        )
        self._start_export(worker)

    # ---------------------------------------------------------------------------
    # Worker callbacks (main thread via Qt signal)
    # ---------------------------------------------------------------------------

    @pyqtSlot(str, str)
    def _on_export_finished(self, description: str, output_folder: str) -> None:
        self.view.progress_bar.setVisible(False)
        self._set_buttons_enabled(True)
        self.view.label_status.setText(
            f"###### Exported {description} to `{output_folder}`"
        )
        # Open the output folder in the system file manager.
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_folder))

    @pyqtSlot(str)
    def _on_export_error(self, message: str) -> None:
        self.view.progress_bar.setVisible(False)
        self._set_buttons_enabled(True)
        self.view.label_status.setText("")
        print(f"ExportDataPresenter: export error:\n{message}", flush=True)
        self._error_dialog.showMessage(f"Export failed:\n\n{message}")
