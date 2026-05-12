"""
statement_result_presenter.py — Presenter for the Statement Import Results panel.

Owns all result-panel interaction after an import batch completes:
* populates the three in-memory table views live during import,
* persists all results to gui.db at batch completion,
* wires the three batch action buttons,
* manages the enabled-state of ``buttonCommitBatch``.

Signal flow
-----------
* Live import  : ``StanPresenter.statement_imported``
                   → ``add_result_to_memory(row)``   (in-memory model updated instantly)
* Batch done   : ``StanPresenter.on_import_finished``
                   → ``persist_batch_to_db(batch_id)``  (write all rows to gui.db once)
* Session restore: ``StanPresenter.update_current_project_info``
                   → ``load_results_from_db(batch_id, project_id)``

Signals emitted (consumed by StanPresenter)
-------------------------------------------
* ``exit_results()``     — user pressed Close Results (queue stays locked).
* ``batch_abandoned()``  — user abandoned the batch; DB rows + payloads deleted.
"""

import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from openstan.components import StanErrorMessage, StanInfoMessage
from openstan.models.statement_result_model import ResultRow

if TYPE_CHECKING:
    from openstan.models.batch_model import BatchModel
    from openstan.models.statement_result_model import (
        FailureResultModel,
        ReviewResultModel,
        StatementResultModel,
        StatementResultPayloadModel,
        SuccessResultModel,
    )
    from openstan.models.statement_queue_model import StatementQueueModel
    from openstan.views.debug_info_dialog import DebugInfoDialog
    from openstan.views.statement_result_view import StatementResultView


# ---------------------------------------------------------------------------
# Background worker for the three-step commit sequence
# ---------------------------------------------------------------------------


class CommitWorkerSignals(QObject):
    """Cross-thread signals for CommitWorker."""

    step = pyqtSignal(str)  # emitted before each bsp call — step description
    finished = pyqtSignal()  # all three calls succeeded
    error = pyqtSignal(str)  # one call raised — human-readable message


class CommitWorker(QRunnable):
    """Run update_db → copy_statements_to_project → delete_temp_files off-thread.

    Parameters
    ----------
    processed_pdfs:
        Ordered list of ``PdfResult`` objects (or ``BaseException`` for
        failed items) that match *pdfs* index-for-index.
    pdfs:
        Ordered list of source PDF ``Path`` objects.
    batch_id, session_id, user_id, path:
        Metadata forwarded to ``bsp.update_db``.
    pdf_count, errors, reviews:
        Aggregate counts forwarded to ``bsp.update_db``.
    project_path:
        Resolved project root — must never be ``None``.
    duration_secs:
        Actual PDF processing seconds for this batch, read from the
        ``batch`` table in gui.db so the value persists across sessions.
    """

    def __init__(
        self,
        processed_pdfs: list,
        pdfs: list[Path],
        batch_id: str,
        session_id: str,
        user_id: str,
        path: str,
        pdf_count: int,
        errors: int,
        reviews: int,
        project_path: Path,
        duration_secs: float,
    ) -> None:
        super().__init__()
        self.signals = CommitWorkerSignals()
        self._processed_pdfs = processed_pdfs
        self._pdfs = pdfs
        self._batch_id = batch_id
        self._session_id = session_id
        self._user_id = user_id
        self._path = path
        self._pdf_count = pdf_count
        self._errors = errors
        self._reviews = reviews
        self._project_path = project_path
        self._duration_secs = duration_secs

    def run(self) -> None:
        try:
            self.signals.step.emit("Updating database…")
            bsp.update_db(
                processed_pdfs=self._processed_pdfs,
                batch_id=self._batch_id,
                session_id=self._session_id,
                user_id=self._user_id,
                path=self._path,
                company_key=None,
                account_key=None,
                pdf_count=self._pdf_count,
                errors=self._errors,
                reviews=self._reviews,
                duration_secs=self._duration_secs,
                process_time=datetime.now(timezone.utc),
                project_path=self._project_path,
            )

            self.signals.step.emit("Copying statements…")
            bsp.copy_statements_to_project(
                processed_pdfs=self._processed_pdfs,
                pdfs=self._pdfs,
                project_path=self._project_path,
            )

            self.signals.step.emit("Cleaning up temporary files…")
            bsp.delete_temp_files(
                processed_pdfs=self._processed_pdfs,
                project_path=self._project_path,
            )

        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.signals.error.emit(
                "An error occurred during commit. See stderr for details."
            )
            return

        self.signals.finished.emit()


# ---------------------------------------------------------------------------
# Background worker for async debug file generation
# ---------------------------------------------------------------------------


class DebugWorkerSignals(QObject):
    """Cross-thread signals for DebugWorker."""

    # Emitted once per non-success row after debug_pdf_statement completes.
    # Carries: (result_id, debug_json_path | None)
    entry_done = pyqtSignal(str, object)
    all_done = pyqtSignal()
    error = pyqtSignal(str)


class DebugWorker(QRunnable):
    """Run ``bsp.debug_pdf_statement`` for each non-success row off-thread.

    Handles both REVIEW and FAILURE rows — bsp.debug_statements() skips
    REVIEW entries so we call debug_pdf_statement() directly for all of them.

    Parameters
    ----------
    rows:
        Ordered list of non-success ``ResultRow`` objects (REVIEW + FAILURE).
    result_ids:
        Ordered list of result_ids matching *rows* index-for-index.
    batch_id:
        The current batch identifier forwarded to ``bsp.debug_pdf_statement``.
    project_path:
        Resolved project root — must never be ``None``.
    cancel_event:
        Set this event to request cancellation before the next iteration.
    """

    def __init__(
        self,
        rows: list[ResultRow],
        result_ids: list[str],
        batch_id: str,
        project_path: Path,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self.signals = DebugWorkerSignals()
        self._rows = rows
        self._result_ids = result_ids
        self._batch_id = batch_id
        self._project_path = project_path
        self._cancel_event = cancel_event

    def run(self) -> None:
        try:
            for i, row in enumerate(self._rows):
                if self._cancel_event.is_set():
                    break

                result_id = self._result_ids[i] if i < len(self._result_ids) else ""

                debug_json_path: Path | None = None
                try:
                    debug_json_path = bsp.debug_pdf_statement(
                        pdf=row.file_path,
                        batch_id=self._batch_id,
                        company_key=None,
                        account_key=None,
                        project_path=self._project_path,
                    )
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    print(
                        f"WARNING: debug_pdf_statement failed for {row.file_path.name}; "
                        "entry will have no debug JSON.",
                        file=sys.stderr,
                    )

                self.signals.entry_done.emit(result_id, debug_json_path)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.signals.error.emit(
                "An error occurred while generating debug files. "
                "See stderr for details."
            )
            # still emit all_done so the presenter can clean up
            self.signals.all_done.emit()
            return

        self.signals.all_done.emit()


class StatementResultPresenter(QObject):
    exit_results = pyqtSignal()
    batch_abandoned = pyqtSignal()
    batch_committed = pyqtSignal()

    def __init__(
        self,
        success_model: "SuccessResultModel",
        review_model: "ReviewResultModel",
        failure_model: "FailureResultModel",
        result_model: "StatementResultModel",
        payload_model: "StatementResultPayloadModel",
        queue_model: "StatementQueueModel",
        batch_model: "BatchModel",
        view: "StatementResultView",
    ) -> None:
        super().__init__()
        self.view = view

        # In-memory presentation models (live during import, populated on restore)
        self.success_model = success_model
        self.review_model = review_model
        self.failure_model = failure_model

        # DB persistence models
        self.result_model = result_model
        self.payload_model = payload_model
        self.queue_model = queue_model
        self.batch_model = batch_model

        # Wire each table view to its in-memory model
        self.view.success_table.setModel(self.success_model)
        self.view.review_table.setModel(self.review_model)
        self.view.failure_table.setModel(self.failure_model)

        # Refresh view whenever any in-memory model changes
        self.success_model.model_updated.connect(self.__refresh_labels_and_buttons)
        self.review_model.model_updated.connect(self.__refresh_labels_and_buttons)
        self.failure_model.model_updated.connect(self.__refresh_labels_and_buttons)

        # Batch action buttons
        self.view.buttonCloseResults.clicked.connect(self.__on_close_results)
        self.view.buttonAbandonBatch.clicked.connect(self.__on_abandon_batch)
        self.view.buttonViewDebugInfo.clicked.connect(self.__on_view_debug_info)
        self.view.buttonCommitBatch.clicked.connect(self.__on_commit_batch)

        self._current_batch_id: str | None = None
        self._current_project_id: str | None = None

        # True while the background import worker is running — all buttons
        # are disabled until import finishes to prevent a mid-batch commit.
        self._importing: bool = False
        self._total_files: int = 0  # set when import starts; used for Pending count

        # Debug worker state
        self._debug_cancel: threading.Event | None = None
        self._debug_worker_done: bool = True  # True = not running
        self._debug_done_count: int = 0
        self._debug_total_count: int = 0

        # Soft-delete / hard-delete lifecycle after commit
        self._pending_batch_id: str | None = (
            None  # set after commit, before hard-delete
        )
        self._pending_hard_delete: bool = False

        # Counts captured at persist time for commit summary dialog
        self._n_success: int = 0
        self._n_review: int = 0
        self._n_failure: int = 0

        # Open debug-info dialog (may be None when closed)
        self._debug_dialog: "DebugInfoDialog | None" = None

        # Set by StanPresenter.update_current_project_info so the commit worker
        # has the correct context without accessing stan directly.
        self.session_id: str = ""
        self.project_path: Path | None = None
        self.username: str = ""

    # ---------------------------------------------------------------------------
    # Public: live import — called per statement_imported signal
    # ---------------------------------------------------------------------------

    def add_result_to_memory(self, row: ResultRow) -> None:
        """Append one result to the correct in-memory model.

        Called by ``StanPresenter.statement_imported`` on the main thread for
        every statement the worker processes.  The in-memory model update
        triggers ``model_updated`` which refreshes labels and column widths.
        """
        self._current_batch_id = row.batch_id
        self._current_project_id = row.project_id
        if row.result == "SUCCESS":
            self.success_model.add_row(row)
        elif row.result == "REVIEW":
            self.review_model.add_row(row)
        else:
            self.failure_model.add_row(row)

    # ---------------------------------------------------------------------------
    # Public: batch-end persist — called once when import_finished fires
    # ---------------------------------------------------------------------------

    def persist_batch_to_db(self, batch_id: str) -> None:
        """Write all in-memory rows to gui.db in one pass.

        Called by ``StanPresenter.on_import_finished``.  Iterates all three
        in-memory models and writes each row to ``statement_result`` +
        ``statement_result_payload``.  Errors are printed to stderr per-row
        so a single failure does not abort the entire persist.
        """
        all_rows: list[ResultRow] = (
            self.success_model.all_rows()
            + self.review_model.all_rows()
            + self.failure_model.all_rows()
        )
        print(f"Persisting {len(all_rows)} result(s) for batch {batch_id} …")
        for row in all_rows:
            ok, result_id, msg = self.result_model.add_result(
                batch_id=batch_id,
                queue_id=row.queue_id,
                project_id=row.project_id,
                result=row.result,
                file_path=row.file_path,
                id_account=row.id_account,
                statement_date=row.statement_date,
                payments_in=row.payments_in,
                payments_out=row.payments_out,
                error_type=row.error_type,
                message=row.message,
            )
            if ok and row.pdf_result is not None:
                p_ok, p_msg = self.payload_model.add_payload(result_id, row.pdf_result)
                if not p_ok:
                    print(
                        f"WARNING: Could not persist payload for {row.file_path.name}: {p_msg}",
                        file=sys.stderr,
                    )
            elif not ok:
                print(
                    f"WARNING: Could not persist result for {row.file_path.name}: {msg}",
                    file=sys.stderr,
                )
        print(f"Persist complete for batch {batch_id}.")

        # Capture counts for commit summary dialog
        self._n_success = self.success_model.row_count
        self._n_review = self.review_model.row_count
        self._n_failure = self.failure_model.row_count

        # Auto-start debug worker for all non-success rows
        if self._n_review + self._n_failure > 0:
            self.__start_debug_worker(batch_id)

    # ---------------------------------------------------------------------------
    # Public: project change — always called before session restore check
    # ---------------------------------------------------------------------------

    def clear_for_project_change(self) -> None:
        """Reset all result state when the user switches project.

        Clears in-memory models and resets the view to its empty state.
        Called unconditionally by ``StanPresenter.update_current_project_info``
        before the session-restore check; if the new project has a locked batch
        ``load_results_from_db`` will repopulate immediately afterward.
        """
        self._current_batch_id = None
        self._current_project_id = None
        self.__clear_views()

    # ---------------------------------------------------------------------------
    # Public: session restore — called on project switch with locked batch
    # ---------------------------------------------------------------------------

    def load_results_from_db(self, batch_id: str, project_id: str) -> None:
        """Populate the in-memory models from DB rows (session restore path).

        Called by ``StanPresenter.update_current_project_info`` when a project
        has a locked batch.  Clears any existing in-memory rows first, then
        reads all ``ResultRow`` objects for this batch from ``statement_result``
        and routes them to the correct in-memory model.

        ``pdf_result`` is ``None`` on restore — payloads are only needed for
        the commit path.
        """
        self._current_batch_id = batch_id
        self._current_project_id = project_id

        # Clear any leftover in-memory state from a previous project
        self.__clear_memory_models_silently()

        rows = self.result_model.get_rows_for_batch(batch_id)
        for row in rows:
            if row.result == "SUCCESS":
                self.success_model.add_row(row)
            elif row.result == "REVIEW":
                self.review_model.add_row(row)
            else:
                self.failure_model.add_row(row)

    # ---------------------------------------------------------------------------
    # Public: import lifecycle — called by StanPresenter
    # ---------------------------------------------------------------------------

    def set_importing(self, importing: bool, total_files: int = 0) -> None:
        """Set whether a background import is currently running.

        When *importing* is ``True`` all three action buttons are disabled so
        the user cannot commit or abandon a batch that is still being built.
        When *importing* is ``False`` (import finished) the buttons are
        re-enabled according to the normal rules: Close and Abandon are always
        enabled, Commit only when n_success > 0.

        *total_files* is the number of PDF files in the batch; it is stored so
        that the results label can show a live Pending count during import.

        Called by ``StanPresenter``:
        * ``True``  — just before the worker thread is started.
        * ``False`` — inside ``on_import_finished``, after persisting to DB.
        """
        self._importing = importing
        if importing:
            self._total_files = total_files
        self.__apply_button_state()

    def cancel_debug_worker(self) -> None:
        """Signal the background debug worker to stop at its next iteration.

        Safe to call even if no worker is running (no-op when ``_debug_cancel``
        is ``None``).  Called by ``StanPresenter`` during project change and
        application exit.
        """
        if self._debug_cancel is not None:
            self._debug_cancel.set()

    # ---------------------------------------------------------------------------
    # Button slots
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def __on_close_results(self) -> None:
        """Navigate back to the queue view; queue stays locked."""
        self.exit_results.emit()

    @pyqtSlot()
    def __on_abandon_batch(self) -> None:
        """Confirm with the user, then cancel debug worker, delete DB rows, unlock queue."""
        confirm = StanInfoMessage(parent=self.view)
        confirm.setText(
            "Are you sure you want to abandon this batch?\n\n"
            "All imported results will be discarded and the queue will be unlocked."
        )
        confirm.setStandardButtons(
            StanInfoMessage.StandardButton.Yes | StanInfoMessage.StandardButton.Cancel
        )
        confirm.setDefaultButton(StanInfoMessage.StandardButton.Cancel)
        if confirm.exec() != StanInfoMessage.StandardButton.Yes:
            return

        # Signal the debug worker to stop at its next iteration
        if self._debug_cancel is not None:
            self._debug_cancel.set()

        batch_id = self._current_batch_id
        project_id = self._current_project_id

        if batch_id:
            # 1. Collect result_ids so we can delete payloads too
            result_ids = self.result_model.get_result_ids_for_batch(batch_id)

            # 2. Delete payloads first (FK-safe order)
            ok, msg = self.payload_model.delete_payloads_for_results(result_ids)
            if not ok:
                print(f"ERROR: Could not delete payloads: {msg}", file=sys.stderr)

            # 3. Hard-delete all result rows (including any soft-deleted ones)
            ok, msg = self.result_model.delete_results_for_batch(batch_id)
            if not ok:
                print(f"ERROR: Could not delete results: {msg}", file=sys.stderr)

            # 4. Delete batch record
            ok, msg = self.batch_model.delete_batch(batch_id)
            if not ok:
                print(f"ERROR: Could not delete batch record: {msg}", file=sys.stderr)

            # 5. Clear batch_id on queue rows → unlock the queue
            if project_id:
                ok, msg = self.queue_model.clear_batch_id()
                if not ok:
                    print(
                        f"ERROR: Could not clear batch_id on queue: {msg}",
                        file=sys.stderr,
                    )

        # 6. Clear in-memory state and reset labels
        self._current_batch_id = None
        self._current_project_id = None
        self._pending_hard_delete = False
        self._pending_batch_id = None
        self.__clear_views()

        # 7. Notify StanPresenter
        self.batch_abandoned.emit()

    @pyqtSlot()
    def __on_view_debug_info(self) -> None:
        """Open (or re-open) the DebugInfoDialog for all non-success rows."""
        from openstan.views.debug_info_dialog import DebugInfoDialog

        # Re-read from DB so debug_status / debug_json_path are always fresh,
        # even when the dialog is opened after the debug worker has already finished.
        if self._current_batch_id:
            all_rows = self.result_model.get_rows_for_batch(self._current_batch_id)
            non_success = [r for r in all_rows if r.result != "SUCCESS"]
        else:
            non_success = self.review_model.all_rows() + self.failure_model.all_rows()

        if not non_success:
            return

        self._debug_dialog = DebugInfoDialog(
            rows=non_success,
            project_paths=(
                bsp.ProjectPaths.resolve(self.project_path)
                if self.project_path is not None
                else None
            ),
            parent=self.view,
        )
        if not self._debug_worker_done:
            self._debug_dialog.update_progress_label(
                self._debug_done_count, self._debug_total_count
            )
        else:
            self._debug_dialog.set_all_done()
        self._debug_dialog.exec()
        self._debug_dialog = None

    # ---------------------------------------------------------------------------
    # Debug worker — auto-started after persist, runs for all non-success rows
    # ---------------------------------------------------------------------------

    def __start_debug_worker(self, batch_id: str) -> None:
        """Collect all non-success rows and start DebugWorker off-thread."""
        if self.project_path is None:
            print(
                "WARNING: Cannot start debug worker — project path is not set.",
                file=sys.stderr,
            )
            return

        non_success = self.review_model.all_rows() + self.failure_model.all_rows()
        if not non_success:
            return

        # result_ids are persisted in order: success first, then review, then failure
        all_result_ids = self.result_model.get_result_ids_for_batch(batch_id)
        n_success = self.success_model.row_count
        non_success_ids = all_result_ids[n_success:]

        # Mark all non-success rows as 'pending' in the DB
        for rid in non_success_ids:
            self.result_model.update_debug_info(rid, "pending", None)

        self._debug_cancel = threading.Event()
        self._debug_worker_done = False
        self._debug_done_count = 0
        self._debug_total_count = len(non_success)

        self.__update_debug_button_label()

        worker = DebugWorker(
            rows=non_success,
            result_ids=non_success_ids,
            batch_id=batch_id,
            project_path=self.project_path,
            cancel_event=self._debug_cancel,
        )
        worker.signals.entry_done.connect(self.__on_debug_entry_done)
        worker.signals.all_done.connect(self.__on_debug_all_done)
        worker.signals.error.connect(self.__on_debug_error)

        thread_pool = QThreadPool.globalInstance()
        assert thread_pool is not None, "QThreadPool.globalInstance() returned None"
        thread_pool.start(worker)

    @pyqtSlot(str, object)
    def __on_debug_entry_done(
        self, result_id: str, debug_json_path: "Path | None"
    ) -> None:
        """Persist debug result for one row and update the open dialog if any."""
        status = "done" if debug_json_path is not None else "error"
        self.result_model.update_debug_info(result_id, status, debug_json_path)

        self._debug_done_count += 1

        if self._debug_dialog is not None:
            self._debug_dialog.update_row(result_id, status, debug_json_path)

        self.__update_debug_button_label()

    @pyqtSlot()
    def __on_debug_all_done(self) -> None:
        """Worker finished (or was cancelled) — finalise state."""
        self._debug_worker_done = True

        if self._debug_dialog is not None:
            self._debug_dialog.set_all_done()

        self.__update_debug_button_label()

        if self._pending_hard_delete and self._pending_batch_id:
            ok, msg = self.result_model.hard_delete_soft_deleted(self._pending_batch_id)
            if not ok:
                print(f"ERROR: hard_delete_soft_deleted failed: {msg}", file=sys.stderr)
            self._pending_hard_delete = False
            self._pending_batch_id = None

    @pyqtSlot(str)
    def __on_debug_error(self, message: str) -> None:
        """Worker raised an outer exception — treat as all-done."""
        print(f"ERROR: DebugWorker: {message}", file=sys.stderr)
        self.__on_debug_all_done()

    def __update_debug_button_label(self) -> None:
        """Refresh the View Debug Info button label with live progress."""
        n_non_success = self.review_model.row_count + self.failure_model.row_count
        if n_non_success == 0:
            self.view.buttonViewDebugInfo.setText("View Debug Info")
            return
        if not self._debug_worker_done:
            self.view.buttonViewDebugInfo.setText(
                f"View Debug Info ({self._debug_done_count}/{self._debug_total_count})"
            )
        else:
            self.view.buttonViewDebugInfo.setText("View Debug Info")

    @pyqtSlot()
    def __on_commit_batch(self) -> None:
        """Launch CommitWorker to run update_db → copy_statements → delete_temps.

        Disables Commit and Abandon buttons while the worker runs.  On success
        the same abandon-batch cleanup is performed (DB rows/payloads deleted,
        queue lock cleared) since the data is now safely in project.db.  On
        error a StanErrorMessage dialog is shown and the buttons re-enabled so
        the user can retry.
        """
        batch_id = self._current_batch_id
        project_id = self._current_project_id

        if not batch_id or not project_id:
            return

        if self.project_path is None:
            StanErrorMessage(parent=self.view).showMessage(
                "Cannot commit: project path is not set."
            )
            return

        # Collect result_ids so we can load payloads in insertion order
        result_ids = self.result_model.get_result_ids_for_batch(batch_id)

        # Build pdfs + processed_pdfs lists in insertion order by iterating
        # all_rows() from each in-memory model (SUCCESS first, then REVIEW,
        # then FAILURE — matching the order rows were added to the DB).
        all_rows_ordered: list[ResultRow] = (
            self.success_model.all_rows()
            + self.review_model.all_rows()
            + self.failure_model.all_rows()
        )

        # Load payloads from DB (handles session-restore where pdf_result is None)
        id_to_payload = self.payload_model.load_payloads_for_batch(result_ids)

        # Re-map: result_ids are ordered the same way all_rows() were persisted
        # (persist_batch_to_db iterates success+review+failure in the same order).
        processed_pdfs: list = []
        pdfs: list[Path] = []
        for i, row in enumerate(all_rows_ordered):
            result_id = result_ids[i] if i < len(result_ids) else None
            payload = (
                id_to_payload.get(result_id)
                if result_id is not None
                else row.pdf_result
            )
            if payload is None and row.pdf_result is not None:
                payload = row.pdf_result
            if payload is not None:
                processed_pdfs.append(payload)
                pdfs.append(row.file_path)

        n_success = self.success_model.row_count
        n_review = self.review_model.row_count
        n_failure = self.failure_model.row_count
        pdf_count = n_success + n_review + n_failure

        folder_path = self.queue_model.get_folder_paths_for_batch(batch_id)

        # Read persisted processing duration for this batch
        duration_secs = self.batch_model.get_duration(batch_id)

        # Lock UI for the duration of the worker
        self.view.buttonCommitBatch.setEnabled(False)
        self.view.buttonAbandonBatch.setEnabled(False)
        self.view.progressBar.setValue(0)

        worker = CommitWorker(
            processed_pdfs=processed_pdfs,
            pdfs=pdfs,
            batch_id=batch_id,
            session_id=self.session_id,
            user_id=self.username,
            path=folder_path,
            pdf_count=pdf_count,
            errors=n_failure,
            reviews=n_review,
            project_path=self.project_path,
            duration_secs=duration_secs,
        )

        worker.signals.step.connect(self.__on_commit_step)
        worker.signals.finished.connect(self.__on_commit_finished)
        worker.signals.error.connect(self.__on_commit_error)

        thread_pool = QThreadPool.globalInstance()
        assert thread_pool is not None, "QThreadPool.globalInstance() returned None"
        thread_pool.start(worker)

    # ---------------------------------------------------------------------------
    # Commit worker callbacks
    # ---------------------------------------------------------------------------

    _COMMIT_STEP_VALUES = {
        "Updating database…": 0,
        "Copying statements…": 33,
        "Cleaning up temporary files…": 66,
    }

    @pyqtSlot(str)
    def __on_commit_step(self, description: str) -> None:
        """Advance progress bar and update label for the current step."""
        value = self._COMMIT_STEP_VALUES.get(description, self.view.progressBar.value())
        self.view.progressBar.setValue(value)
        self.view.labelStatementsProcessed.setText(description)

    @pyqtSlot()
    def __on_commit_finished(self) -> None:
        """All three bsp calls succeeded — soft-delete results, show summary, close."""
        self.view.progressBar.setValue(100)
        batch_id = self._current_batch_id
        project_id = self._current_project_id

        if batch_id:
            # Delete payloads (no longer needed — data is in project.db)
            result_ids = self.result_model.get_result_ids_for_batch(batch_id)
            ok, msg = self.payload_model.delete_payloads_for_results(result_ids)
            if not ok:
                print(
                    f"ERROR: Could not delete payloads after commit: {msg}",
                    file=sys.stderr,
                )

            # Soft-delete result rows so the UI clears immediately;
            # debug worker (if still running) will hard-delete once done.
            ok, msg = self.result_model.soft_delete_batch(batch_id)
            if not ok:
                print(
                    f"ERROR: Could not soft-delete results after commit: {msg}",
                    file=sys.stderr,
                )

            # Mark batch as committed in gui.db so the export panel can
            # identify it as a completed (non-pending) batch when resolving
            # "Latest" batch exports.
            ok, msg = self.batch_model.commit_batch(batch_id)
            if not ok:
                print(
                    f"WARNING: Could not mark batch as committed: {msg}",
                    file=sys.stderr,
                )

            if project_id:
                ok, msg = self.queue_model.clear_batch_id()
                if not ok:
                    print(
                        f"ERROR: Could not clear batch_id after commit: {msg}",
                        file=sys.stderr,
                    )

        self._current_batch_id = None
        self._current_project_id = None

        # Hard-delete: if the debug worker is already done, do it now;
        # otherwise schedule it for when the worker finishes.
        if batch_id:
            if self._debug_worker_done:
                ok, msg = self.result_model.hard_delete_soft_deleted(batch_id)
                if not ok:
                    print(
                        f"ERROR: hard_delete_soft_deleted failed: {msg}",
                        file=sys.stderr,
                    )
            else:
                self._pending_batch_id = batch_id
                self._pending_hard_delete = True

        # Build commit summary message
        lines: list[str] = []
        if self._n_success:
            lines.append(f"{self._n_success} successful statement(s) committed.")
        if self._n_review:
            lines.append(
                f"{self._n_review} review statement(s) committed but excluded from "
                "reporting & export due to checks & balances failure."
            )
        if self._n_failure:
            log_path = (
                str(self.project_path / "log" / "debug")
                if self.project_path is not None
                else "project log/debug directory"
            )
            lines.append(
                f"{self._n_failure} failed statement(s) abandoned — "
                f"logs available at {log_path}"
            )
        summary = "\n".join(lines) if lines else "Batch committed."

        info = StanInfoMessage(parent=self.view)
        info.setText(summary)
        info.exec()

        # Clear in-memory state and reset the results panel to its empty state.
        self.__clear_views()

        # Notify StanPresenter to hide the results panel, clear the queue, and
        # refresh the queue view.
        self.batch_committed.emit()

    @pyqtSlot(str)
    def __on_commit_error(self, message: str) -> None:
        """A bsp call failed — show error dialog and re-enable retry."""
        StanErrorMessage(parent=self.view).showMessage(message)
        # Re-enable so the user can retry or abandon (import is not running)
        self.__apply_button_state()

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def __refresh_labels_and_buttons(self) -> None:
        """Update summary label, tab labels/visibility, column widths, and button state."""
        n_success = self.success_model.row_count
        n_review = self.review_model.row_count
        n_failure = self.failure_model.row_count
        n_processed = n_success + n_review + n_failure
        n_pending = max(0, self._total_files - n_processed)

        self.view.labelStatementsProcessed.setText(
            f"Total: {self._total_files}  |  "
            f"Pending: {n_pending}  |  "
            f"Processed: {n_processed}  |  "
            f"Success: {n_success}  |  "
            f"Review: {n_review}  |  "
            f"Failed: {n_failure}"
        )

        tabs = self.view.results_tabs
        tabs.setTabText(self.view.TAB_SUCCESS, f"SUCCESS ({n_success})")
        tabs.setTabText(self.view.TAB_REVIEW, f"REVIEW ({n_review})")
        tabs.setTabText(self.view.TAB_FAILURE, f"FAILURE ({n_failure})")
        tabs.setTabVisible(self.view.TAB_SUCCESS, n_success > 0)
        tabs.setTabVisible(self.view.TAB_REVIEW, n_review > 0)
        tabs.setTabVisible(self.view.TAB_FAILURE, n_failure > 0)

        # Ensure the tab widget itself is always visible once any results arrive
        tabs.setVisible(n_processed > 0)

        self.view.success_table.resizeColumnsToContents()
        self.view.review_table.resizeColumnsToContents()
        self.view.failure_table.resizeColumnsToContents()

        self.__apply_button_state()

    def __apply_button_state(self) -> None:
        """Set enabled state of all four action buttons.

        All buttons are disabled while import is running.  Once import
        finishes, Close and Abandon are always enabled; View Debug Info is
        enabled when any non-success rows exist; Commit is enabled only when
        at least one successful result exists.
        """
        if self._importing:
            self.__set_all_buttons_enabled(False)
        else:
            n_non_success = self.review_model.row_count + self.failure_model.row_count
            self.view.buttonCloseResults.setEnabled(True)
            self.view.buttonAbandonBatch.setEnabled(True)
            self.view.buttonViewDebugInfo.setEnabled(n_non_success > 0)
            self.view.buttonCommitBatch.setEnabled(self.success_model.row_count > 0)

    def __set_all_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all four action buttons at once."""
        self.view.buttonCloseResults.setEnabled(enabled)
        self.view.buttonAbandonBatch.setEnabled(enabled)
        self.view.buttonViewDebugInfo.setEnabled(enabled)
        self.view.buttonCommitBatch.setEnabled(enabled)

    def __clear_memory_models_silently(self) -> None:
        """Clear in-memory models without triggering model_updated signals.

        Used before repopulating on session restore to avoid a redundant
        label refresh mid-load.
        """
        # Disconnect temporarily so the intermediate clear doesn't refresh labels
        self.success_model.model_updated.disconnect(self.__refresh_labels_and_buttons)
        self.review_model.model_updated.disconnect(self.__refresh_labels_and_buttons)
        self.failure_model.model_updated.disconnect(self.__refresh_labels_and_buttons)

        self.success_model.clear_rows()
        self.review_model.clear_rows()
        self.failure_model.clear_rows()

        self.success_model.model_updated.connect(self.__refresh_labels_and_buttons)
        self.review_model.model_updated.connect(self.__refresh_labels_and_buttons)
        self.failure_model.model_updated.connect(self.__refresh_labels_and_buttons)

    def __clear_views(self) -> None:
        """Clear in-memory models and reset all labels/buttons/tabs to zero state."""
        self.success_model.clear_rows()
        self.review_model.clear_rows()
        self.failure_model.clear_rows()
        self._total_files = 0

        self.view.labelStatementsProcessed.setText(
            "Total: 0  |  Pending: 0  |  Processed: 0  |  Success: 0  |  Review: 0  |  Failed: 0"
        )
        tabs = self.view.results_tabs
        tabs.setTabText(self.view.TAB_SUCCESS, "SUCCESS (0)")
        tabs.setTabText(self.view.TAB_REVIEW, "REVIEW (0)")
        tabs.setTabText(self.view.TAB_FAILURE, "FAILURE (0)")
        tabs.setTabVisible(self.view.TAB_SUCCESS, False)
        tabs.setTabVisible(self.view.TAB_REVIEW, False)
        tabs.setTabVisible(self.view.TAB_FAILURE, False)
        tabs.setVisible(False)
        self.view.progressBar.setValue(0)
        self.view.progressBar.setFormat("%p%")
        # Clearing always means we are no longer in an importing state
        self._importing = False
        self.view.buttonCloseResults.setEnabled(True)
        self.view.buttonAbandonBatch.setEnabled(True)
        self.view.buttonViewDebugInfo.setEnabled(False)
        self.view.buttonViewDebugInfo.setText("View Debug Info")
        self.view.buttonCommitBatch.setEnabled(False)
