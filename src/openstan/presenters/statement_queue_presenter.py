"""
statement_queue_presenter.py — Presenter for the Statement Queue panel.

Owns all queue interaction: adding/removing items, locking the queue when an
import batch starts, restoring lock state on project switch, and signalling
when the user wants to view the results panel.

Lock state machine
------------------
* **Unlocked** — ``batch_id`` is NULL on all queue rows.
  All modification buttons enabled; Run Import enabled if rows exist.
  labelLocked and buttonViewResults hidden.

* **Locked** — ``batch_id`` is set on all queue rows (set when import starts).
  All modification buttons disabled; Run Import disabled.
  labelLocked visible; buttonViewResults visible once import finishes.

Signals emitted (consumed by StanPresenter)
--------------------------------------------
* ``statement_imported(Path, PdfResult, int)`` — one per processed file.
* ``import_finished()``                         — worker thread done.
* ``view_results_requested()``                  — user pressed View Results.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from PyQt6.QtCore import QThreadPool

    from openstan.models.statement_queue_model import (
        StatementQueueModel,
        StatementQueueTreeModel,
    )
    from openstan.views.statement_queue_view import StatementQueueView


class WorkerSignals(QObject):
    """Signals emitted from the background import thread."""

    progress = pyqtSignal(
        Path, int, bsp.PdfResult, str
    )  # (file_path, progress_%, result, queue_id)
    finished = pyqtSignal()


class SQWorker(QRunnable):
    """Background worker: iterates the queue and calls bsp.process_pdf_statement."""

    def __init__(
        self,
        presenter: "StatementQueuePresenter",
        model: "StatementQueueModel",
        batch_id: str,
    ) -> None:
        super().__init__()
        self.presenter = presenter
        self.model = model
        self.signals = WorkerSignals()
        self.batch_id = batch_id

    @pyqtSlot()
    def run(self) -> None:
        total_n = self.model.rowCount()
        for n in range(total_n):
            progress_pc = int(100 * float(n + 1) / total_n)
            record = self.model.record(n)
            if record.value("is_folder") == 1:
                continue  # skip folder rows
            file_path = Path(record.value("path"))
            queue_id = str(record.value("queue_id"))
            print(f"Importing statement: {file_path.stem} ({n + 1}/{total_n})")
            stmt = bsp.process_pdf_statement(
                pdf=file_path,
                batch_id=self.batch_id,
                session_id=self.presenter.sessionID,
                user_id="",
                company_key=None,
                account_key=None,
                project_path=self.presenter.projectPath,
            )
            self.signals.progress.emit(file_path, progress_pc, stmt, queue_id)
        self.signals.finished.emit()


class StatementQueuePresenter(QObject):
    """Presenter for the statement queue panel."""

    statement_imported = pyqtSignal(
        Path, bsp.PdfResult, int, str
    )  # file, result, progress%, queue_id
    import_finished = pyqtSignal()
    view_results_requested = pyqtSignal()

    def __init__(
        self,
        model: "StatementQueueModel",
        view: "StatementQueueView",
        tree_model: "StatementQueueTreeModel",
        threadpool: "QThreadPool",
    ) -> None:
        super().__init__()
        self.threadpool: "QThreadPool" = threadpool
        self.sessionID: str = "<<NO SESSION ID>>"  # set by StanPresenter
        self.projectID: str = "<<NO PROJECT ID>>"  # set by StanPresenter
        self.projectPath: Path = Path("<<NO PROJECT PATH>>")  # set by StanPresenter
        self._current_batch_id: str | None = None

        self.model: "StatementQueueModel" = model
        self.view: "StatementQueueView" = view
        self.tree_model: "StatementQueueTreeModel" = tree_model

        self.view.tree.setModel(self.tree_model)
        self.view.tree.setHeaderHidden(True)

        # ── Signal wiring ──────────────────────────────────────────────────
        self.view.buttonAddFolders.clicked.connect(self.open_folder_dialog)
        self.view.buttonAddFiles.clicked.connect(self.open_file_dialog)
        self.view.buttonRemove.clicked.connect(self.remove_selected_items)
        self.view.buttonClear.clicked.connect(self.clear_all_items)
        self.view.buttonRunImport.clicked.connect(self.run_import)
        self.view.buttonViewResults.clicked.connect(self.__on_view_results_clicked)

    # ---------------------------------------------------------------------------
    # Import
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def run_import(self) -> None:
        """Lock the queue and start the background import worker."""
        batch_id: str = uuid4().hex
        print(f"Running statement import — batch_id: {batch_id}")

        # Lock every queue row for this project
        success, msg = self.model.set_batch_id(self.projectID, batch_id)
        if not success:
            print(f"ERROR: Could not lock queue: {msg}", flush=True)
            return

        self._current_batch_id = batch_id
        self.__set_queue_locked(importing=True)

        worker = SQWorker(presenter=self, model=self.model, batch_id=batch_id)
        worker.signals.progress.connect(self.__on_worker_progress)
        worker.signals.finished.connect(self.__on_worker_finished)
        self.threadpool.start(worker)

    @pyqtSlot(Path, int, bsp.PdfResult, str)
    def __on_worker_progress(
        self,
        file_path: Path,
        progress_bar_value: int,
        statement: bsp.PdfResult,
        queue_id: str,
    ) -> None:
        self.statement_imported.emit(file_path, statement, progress_bar_value, queue_id)
        print(
            f" Import progress: {progress_bar_value}% "
            f"— Result: {statement.result} {statement.outcome}"
        )

    @pyqtSlot()
    def __on_worker_finished(self) -> None:
        """Import worker is done: show View Results button, emit import_finished."""
        self.view.buttonViewResults.setVisible(True)
        self.import_finished.emit()
        print("Import finished.")

    @pyqtSlot()
    def __on_view_results_clicked(self) -> None:
        self.view_results_requested.emit()

    # ---------------------------------------------------------------------------
    # Queue modification slots
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_folder_dialog(self) -> None:
        if self.view.folder_dialog.exec():
            selected_folder: str = self.view.folder_dialog.selectedFiles()[0]
            print("Selected folder:", selected_folder)
            folder_id: str = uuid4().hex
            folder_path = Path(selected_folder)
            self.add_record(
                queue_id=folder_id, parent_id=folder_id, path=folder_path, is_folder=1
            )
            for file in folder_path.iterdir():
                if file.is_file() and file.suffix.lower() == ".pdf":
                    file_id: str = uuid4().hex
                    self.add_record(
                        queue_id=file_id, parent_id=folder_id, path=file, is_folder=0
                    )
            self.update_view()

    @pyqtSlot()
    def open_file_dialog(self) -> None:
        if self.view.file_dialog.exec():
            selected_files: list[str] = self.view.file_dialog.selectedFiles()
            print("Selected files:", selected_files)
            for file in selected_files:
                file_id = uuid4().hex
                self.add_record(
                    queue_id=file_id, parent_id=file_id, path=Path(file), is_folder=0
                )
            self.update_view()

    @pyqtSlot()
    def remove_selected_items(self) -> None:
        selected_indexes: list | None = self.view.tree.selectedIndexes()
        if not selected_indexes:
            return
        selected_ids: list[str] = [
            str(index.data()) for index in selected_indexes if index.column() == 1
        ]
        self.model.delete_records(queue_ids=selected_ids)
        self.update_view()

    @pyqtSlot()
    def clear_all_items(self) -> None:
        result: tuple[bool, list[str], str] = self.model.clear_records()
        print(result)
        self.update_view()

    def add_record(self, queue_id, parent_id, path, is_folder) -> None:
        result: tuple[bool, str, str] = self.model.add_record(
            queue_id=queue_id,
            parent_id=parent_id,
            project_id=self.projectID,
            session_id=self.sessionID,
            status_id=0,
            path=path,
            is_folder=is_folder,
        )
        if not result[0]:
            print(f"Error adding record: {result[2]}")
        else:
            print(f"Record added successfully: {queue_id}")

    # ---------------------------------------------------------------------------
    # View refresh & lock-state restoration
    # ---------------------------------------------------------------------------

    def update_view(self) -> None:
        """Refresh the tree and restore the correct lock state."""
        if self.projectID is not None:
            self.model.setFilter(f"project_id = '{self.projectID}'")
            self.model.select()
            self.tree_model.update_model(self.projectID)
            self.view.tree.expandToDepth(0)
            self._restore_lock_state()
        else:
            print("Project ID is not set. Cannot update view.")

    def _restore_lock_state(self) -> None:
        """Inspect the DB and apply the correct enabled/visible state to buttons.

        Called on every ``update_view()`` so that switching projects (or starting
        a fresh session on a project with a pending batch) always shows the right
        state without requiring extra signals.
        """
        batch_id = self.model.get_batch_id(self.projectID)
        if batch_id:
            self._current_batch_id = batch_id
            # Import may already have finished — show View Results immediately
            self.__set_queue_locked(importing=False)
            self.view.buttonViewResults.setVisible(True)
        else:
            self._current_batch_id = None
            self.__set_queue_unlocked()

    def __set_queue_locked(self, *, importing: bool) -> None:
        """Disable all modification buttons and show the lock label.

        *importing=True*  hides View Results (worker not done yet).
        *importing=False* is used on restore — View Results shown by caller.
        """
        self.view.buttonAddFolders.setEnabled(False)
        self.view.buttonAddFiles.setEnabled(False)
        self.view.buttonRemove.setEnabled(False)
        self.view.buttonClear.setEnabled(False)
        self.view.buttonRunImport.setEnabled(False)
        self.view.labelLocked.setVisible(True)
        if importing:
            self.view.buttonViewResults.setVisible(False)

    def __set_queue_unlocked(self) -> None:
        """Re-enable modification buttons and hide the lock indicator."""
        self.view.buttonAddFolders.setEnabled(True)
        self.view.buttonAddFiles.setEnabled(True)
        self.view.buttonRemove.setEnabled(True)
        self.view.buttonClear.setEnabled(True)
        # Run Import enabled only if there are rows to process
        has_rows = self.model.rowCount() > 0
        self.view.buttonRunImport.setEnabled(has_rows)
        self.view.labelLocked.setVisible(False)
        self.view.buttonViewResults.setVisible(False)
