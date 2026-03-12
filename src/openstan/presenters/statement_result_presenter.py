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
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from openstan.components import StanErrorMessage, StanInfoMessage
from openstan.models.statement_result_model import ResultRow

if TYPE_CHECKING:
    from openstan.models.statement_result_model import (
        FailureResultModel,
        ReviewResultModel,
        StatementResultModel,
        StatementResultPayloadModel,
        SuccessResultModel,
    )
    from openstan.models.statement_queue_model import StatementQueueModel
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
                duration_secs=0,
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
        self.view.buttonCommitBatch.clicked.connect(self.__on_commit_batch)

        self._current_batch_id: str | None = None
        self._current_project_id: str | None = None

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
    # Button slots
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def __on_close_results(self) -> None:
        """Navigate back to the queue view; queue stays locked."""
        self.exit_results.emit()

    @pyqtSlot()
    def __on_abandon_batch(self) -> None:
        """Delete all DB result rows + payloads, unlock queue, go back."""
        batch_id = self._current_batch_id
        project_id = self._current_project_id

        if batch_id:
            # 1. Collect result_ids so we can delete payloads too
            result_ids = self.result_model.get_result_ids_for_batch(batch_id)

            # 2. Delete payloads first (FK-safe order)
            ok, msg = self.payload_model.delete_payloads_for_results(result_ids)
            if not ok:
                print(f"ERROR: Could not delete payloads: {msg}", file=sys.stderr)

            # 3. Delete result rows
            ok, msg = self.result_model.delete_results_for_batch(batch_id)
            if not ok:
                print(f"ERROR: Could not delete results: {msg}", file=sys.stderr)

            # 4. Clear batch_id on queue rows → unlock the queue
            if project_id:
                ok, msg = self.queue_model.clear_batch_id(project_id)
                if not ok:
                    print(
                        f"ERROR: Could not clear batch_id on queue: {msg}",
                        file=sys.stderr,
                    )

        # 5. Clear in-memory state and reset labels
        self._current_batch_id = None
        self._current_project_id = None
        self.__clear_views()

        # 6. Notify StanPresenter
        self.batch_abandoned.emit()

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
        )

        worker.signals.step.connect(self.__on_commit_step)
        worker.signals.finished.connect(self.__on_commit_finished)
        worker.signals.error.connect(self.__on_commit_error)

        QThreadPool.globalInstance().start(worker)

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
        """All three bsp calls succeeded — notify user, clean up, and close."""
        batch_id = self._current_batch_id
        project_id = self._current_project_id

        # Perform the same DB cleanup as abandon (data is now in project.db)
        if batch_id:
            result_ids = self.result_model.get_result_ids_for_batch(batch_id)
            ok, msg = self.payload_model.delete_payloads_for_results(result_ids)
            if not ok:
                print(
                    f"ERROR: Could not delete payloads after commit: {msg}",
                    file=sys.stderr,
                )
            ok, msg = self.result_model.delete_results_for_batch(batch_id)
            if not ok:
                print(
                    f"ERROR: Could not delete results after commit: {msg}",
                    file=sys.stderr,
                )
            if project_id:
                ok, msg = self.queue_model.clear_batch_id(project_id)
                if not ok:
                    print(
                        f"ERROR: Could not clear batch_id after commit: {msg}",
                        file=sys.stderr,
                    )

        self._current_batch_id = None
        self._current_project_id = None

        # Show the success modal before clearing the view — the message would
        # vanish immediately if we hid the results panel first.
        info = StanInfoMessage(parent=self.view)
        info.setText("Batch committed successfully.")
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
        # Re-enable so the user can retry or abandon
        self.view.buttonCommitBatch.setEnabled(self.success_model.row_count > 0)
        self.view.buttonAbandonBatch.setEnabled(True)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def __refresh_labels_and_buttons(self) -> None:
        """Update summary label, tab labels/visibility, column widths, and button state."""
        n_success = self.success_model.row_count
        n_review = self.review_model.row_count
        n_failure = self.failure_model.row_count
        n_total = n_success + n_review + n_failure

        self.view.labelStatementsProcessed.setText(
            f"Processed: {n_total}  |  "
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
        tabs.setVisible(n_total > 0)

        self.view.success_table.resizeColumnsToContents()
        self.view.review_table.resizeColumnsToContents()
        self.view.failure_table.resizeColumnsToContents()

        # Commit enabled only when there is at least one successful result
        self.view.buttonCommitBatch.setEnabled(n_success > 0)

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

        self.view.labelStatementsProcessed.setText(
            "Processed: 0  |  Success: 0  |  Review: 0  |  Failed: 0"
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
        self.view.buttonCommitBatch.setEnabled(False)
