"""export_data_presenter.py — Presenter for the Export Data panel.

Wires the three export buttons and parameter controls in ``ExportDataView``
to BSP's default export functions.  Each export runs off the main thread
via a ``QRunnable`` so the GUI stays responsive during file I/O.  On
success the output folder is opened in the system file manager; on failure
a modal error dialog is shown.

The project path and project ID are pushed in by ``StanPresenter`` whenever
the active project changes — consistent with the pattern used by
``StatementQueuePresenter`` and ``StatementResultPresenter``.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog

from openstan.components import StanErrorMessage
from openstan.presenters.workers import ExportWorker
from openstan.views.pending_batch_dialog import PendingBatchDialog

if TYPE_CHECKING:
    from PyQt6.QtCore import QThreadPool

    from openstan.models.batch_model import BatchModel
    from openstan.views.export_data_view import ExportDataView


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class ExportDataPresenter(QObject):
    """Presenter for the Export Data panel.

    Receives the view, a ``QThreadPool``, and a ``BatchModel`` at
    construction time.  The active project path and project ID are pushed
    in by ``StanPresenter`` after every project change::

        self.export_data_presenter.project_path = paths.root
        self.export_data_presenter.project_id = current_project_id

    Signals
    -------
    review_pending_batch:
        Emitted when the user chooses "Review Pending Batch" from the
        ``PendingBatchDialog``.  Connected in ``StanPresenter`` to
        ``show_results()``.
    """

    review_pending_batch: pyqtSignal = pyqtSignal()

    def __init__(
        self,
        view: "ExportDataView",
        threadpool: "QThreadPool",
        batch_model: "BatchModel",
    ) -> None:
        super().__init__()
        self.view: "ExportDataView" = view
        self.threadpool: "QThreadPool" = threadpool
        self.batch_model: "BatchModel" = batch_model

        # Set by StanPresenter on every project selection change.
        self.project_path: Path | None = None
        self.project_id: str | None = None

        # Custom folder selected by the user (None = use BSP defaults).
        self._custom_folder: Path | None = None

        # Error dialog — parented to the view so it is modal to the window.
        self._error_dialog = StanErrorMessage(view)

        # ── Signal wiring ──────────────────────────────────────────────────
        self.view.button_csv.clicked.connect(self._on_csv)
        self.view.button_excel.clicked.connect(self._on_excel)
        self.view.button_json.clicked.connect(self._on_json)
        self.view.button_browse_folder.clicked.connect(self._on_browse_folder)
        self.view.button_reset_folder.clicked.connect(self._on_reset_folder)

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    def _all_buttons(self) -> tuple:
        """Return all export buttons as a tuple."""
        v = self.view
        return (v.button_csv, v.button_excel, v.button_json)

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
        fn: Callable[[], Any],
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

    def _read_export_params(self) -> dict | None:
        """Read current parameter selections from the view widgets.

        Returns a dict with keys ``type``, ``batch_id``,
        ``filename_timestamp``, and ``folder``.  Returns ``None`` if
        a required value cannot be resolved (e.g. "Latest" batch selected
        but no committed batches exist) — an error dialog is shown in that
        case.  Also returns ``None`` when the user chooses "Review Pending
        Batch" in the ``PendingBatchDialog`` (and emits
        ``review_pending_batch`` so ``StanPresenter`` can navigate there).
        """
        v = self.view

        # Type
        export_type: str = "single" if v.radio_type_single.isChecked() else "multi"

        # Batch
        batch_id: str | None = None
        if v.radio_batch_latest.isChecked():
            if self.project_id is None:
                self._error_dialog.showMessage(
                    "No project is currently selected. Cannot resolve latest batch."
                )
                return None

            # Check for a pending (uncommitted) batch first.
            pending_id = self.batch_model.get_pending_batch_id(self.project_id)
            if pending_id is not None:
                dlg = PendingBatchDialog(parent=self.view)
                dlg.exec()
                if dlg.choice == PendingBatchDialog.CHOICE_REVIEW_PENDING:
                    self.review_pending_batch.emit()
                    return None
                elif dlg.choice == PendingBatchDialog.CHOICE_CANCELLED:
                    return None
                # CHOICE_EXPORT_COMMITTED — fall through to get_latest_batch_id

            batch_id = self.batch_model.get_latest_batch_id(self.project_id)
            if batch_id is None:
                self._error_dialog.showMessage(
                    "No committed batches found for the current project. "
                    "Import and commit a batch first, or select 'All'."
                )
                return None

        # Filename timestamp
        filename_timestamp: bool = v.radio_ts_on.isChecked()

        # Folder
        folder: Path | None = self._custom_folder

        return {
            "type": export_type,
            "batch_id": batch_id,
            "filename_timestamp": filename_timestamp,
            "folder": folder,
        }

    def _output_folder_for_format(self, fmt: str, params: dict) -> Path:
        """Determine the output folder for status display and file-manager open.

        If the user chose a custom folder, use that.  Otherwise fall back to
        the BSP default: ``<project>/export/<fmt>/``.
        """
        if params["folder"] is not None:
            return params["folder"]
        # Mirror BSP's default folder structure.
        assert self.project_path is not None
        return self.project_path / "export" / fmt

    def update_folder_display(self) -> None:
        """Update the folder line-edit to show the current default path.

        Called when ``project_path`` is set or when the user resets the
        custom folder.
        """
        if self._custom_folder is not None:
            self.view.line_edit_folder.setText(str(self._custom_folder))
        elif self.project_path is not None:
            self.view.line_edit_folder.setText("")
            self.view.line_edit_folder.setPlaceholderText(
                str(self.project_path / "export" / "<format>")
            )
        else:
            self.view.line_edit_folder.setText("")
            self.view.line_edit_folder.setPlaceholderText("(project default)")

    # ---------------------------------------------------------------------------
    # Folder slots
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _on_browse_folder(self) -> None:
        """Open a folder dialog and store the user's choice."""
        start_dir = str(self.project_path / "export") if self.project_path else ""
        folder = QFileDialog.getExistingDirectory(
            self.view,
            "Select export folder",
            start_dir,
        )
        if folder:
            self._custom_folder = Path(folder)
            self.update_folder_display()

    @pyqtSlot()
    def _on_reset_folder(self) -> None:
        """Reset to the BSP default export folder."""
        self._custom_folder = None
        self.update_folder_display()

    # ---------------------------------------------------------------------------
    # Export slots — delegate to shared _on_export(fmt)
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _on_csv(self) -> None:
        self._on_export("csv")

    @pyqtSlot()
    def _on_excel(self) -> None:
        self._on_export("excel")

    @pyqtSlot()
    def _on_json(self) -> None:
        self._on_export("json")

    def _on_export(self, fmt: str) -> None:
        """Resolve params, build the correct BSP worker, and start the export."""
        project_path = self._resolve_project_path()
        if project_path is None:
            return
        params = self._read_export_params()
        if params is None:
            return
        output_folder = self._output_folder_for_format(fmt, params)

        # Capture narrowed locals so closures don't close over the dict | None type.
        export_type = cast(Literal["single", "multi"], params["type"])
        batch_id: str | None = params["batch_id"]
        filename_timestamp: bool = params["filename_timestamp"]
        custom_folder: Path | None = params["folder"]

        if fmt == "excel":
            # export_excel takes ``path`` (a file) rather than ``folder``.
            excel_path: Path | None = (
                custom_folder / "transactions.xlsx"
                if custom_folder is not None
                else None
            )

            def fn() -> None:
                return bsp.db.export_excel(
                    type=export_type,
                    project_path=project_path,
                    batch_id=batch_id,
                    filename_timestamp=filename_timestamp,
                    path=excel_path,
                )

        elif fmt == "csv":

            def fn() -> None:  # type: ignore[no-redef]
                return bsp.db.export_csv(
                    type=export_type,
                    project_path=project_path,
                    batch_id=batch_id,
                    filename_timestamp=filename_timestamp,
                    folder=custom_folder,
                )

        else:  # json

            def fn() -> None:  # type: ignore[no-redef]
                return bsp.db.export_json(
                    type=export_type,
                    project_path=project_path,
                    batch_id=batch_id,
                    filename_timestamp=filename_timestamp,
                    folder=custom_folder,
                )

        worker = self._make_worker(
            fn=fn,
            description=f"{fmt.upper()} ({export_type.title()})",
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
        self._error_dialog.showMessage(f"Export failed:\n\n{message}")
