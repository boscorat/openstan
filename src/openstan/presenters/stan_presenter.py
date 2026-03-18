from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
from bank_statement_parser import ProjectPaths
from PyQt6.QtCore import QObject, pyqtSlot

from openstan.models.statement_result_model import ResultRow
from openstan.presenters.project_presenter import get_project_summary

if TYPE_CHECKING:
    from PyQt6.QtSql import QSqlRecord

    from openstan.main import Stan


class StanPresenter(QObject):
    def __init__(self, stan: "Stan") -> None:
        super().__init__()
        self.stan: "Stan" = stan

        # presenters
        self.project_presenter = self.stan.project_presenter
        self.session_presenter = self.stan.session_presenter
        self.statement_queue_presenter = self.stan.statement_queue_presenter
        self.statement_result_presenter = self.stan.statement_result_presenter

        # views
        self.footer_view = self.stan.footer_view

        # signals
        self.project_presenter.view.selection.currentIndexChanged.connect(
            self.project_selection_changed
        )
        self.session_presenter.db_lock_signal.connect(self.db_lock_handler)
        self.statement_queue_presenter.statement_imported.connect(
            self.statement_imported
        )
        self.statement_queue_presenter.import_started.connect(self.on_import_started)
        self.statement_queue_presenter.import_finished.connect(self.on_import_finished)
        self.statement_queue_presenter.view_results_requested.connect(self.show_results)
        self.statement_result_presenter.exit_results.connect(self.hide_results)
        self.statement_result_presenter.batch_abandoned.connect(self.on_batch_abandoned)
        self.statement_result_presenter.batch_committed.connect(self.on_batch_committed)
        self.footer_view.admin_requested.connect(self.open_admin_dialog)

        # add a new user to the database if not exists
        self.stan.userID = self.stan.user_model.user_id_from_username(
            self.stan.username
        )
        if not self.stan.userID:
            success: bool = bool(False)
            msg: str = ""
            success, self.stan.userID, msg = self.stan.user_presenter.create_new_user(
                self.stan.username, self.stan.sessionID
            )
            if not success:
                self.stan.error_db_lock.showMessage(
                    f"{msg}\nThe application will close shortly."
                )
        # start a new session
        if self.stan.userID:
            success: bool = bool(False)
            msg: str = ""
            success, self.stan.sessionID, msg = self.stan.session_presenter.new_session(
                self.stan.userID
            )
            if not success:
                self.stan.error_db_lock.showMessage(
                    f"{msg}\nThe application will close shortly."
                )

        # update footer label with username and sessionID
        self.footer_view.labelUser.setText(
            f"##### User: {self.stan.username} | Session: {self.stan.sessionID}"
        )

        # pass sessionID to other presenters
        self.project_presenter.sessionID = self.stan.sessionID
        self.statement_queue_presenter.sessionID = self.stan.sessionID
        self.statement_result_presenter.session_id = self.stan.sessionID
        self.statement_result_presenter.username = self.stan.username

        # update current project info
        self.update_current_project_info(
            self.project_presenter.view.selection.currentIndex()
        )

    @pyqtSlot()
    def db_lock_handler(self) -> None:
        self.stan.error_db_lock.showMessage(
            "Database is locked! Another active session may exist.\nThe application will close shortly."
        )

    @pyqtSlot(int)
    def project_selection_changed(self, index: int) -> None:
        self.update_current_project_info(index)

    def cleanup_before_exit(self) -> None:
        self.session_presenter.end_active_sessions()
        print("CLEANUP: StanPresenter.cleanup_before_exit: Session ended.")

    def update_current_project_info(self, index: int) -> None:
        current_record: QSqlRecord = self.project_presenter.model.record(index)
        self.stan.current_project_name = current_record.value("project_name")
        self.stan.current_project_id = current_record.value("project_ID")
        self.statement_queue_presenter.projectID = self.stan.current_project_id
        self.statement_queue_presenter.update_view()
        self.footer_view.labelProject.setText(
            f"##### Project: {self.stan.current_project_name} (ID: {self.stan.current_project_id})"
        )
        self.stan.current_project_paths = ProjectPaths.resolve(
            Path(current_record.value("project_location")).absolute()
        )
        self.statement_queue_presenter.projectPath = (
            self.stan.current_project_paths.root
        )
        self.statement_result_presenter.project_path = (
            self.stan.current_project_paths.root
        )
        print(current_record.value("project_location"))

        self.stan.project_view.summary_label.setText(
            get_project_summary(self.stan.current_project_paths.root)
        )

        # Always reset to the queue view on project change and clear any
        # in-memory results from the previous project.  The session-restore
        # block below will repopulate if this project has a locked batch.
        self.statement_result_presenter.clear_for_project_change()
        self.hide_results()

        # Session restore: check for a locked batch on this project
        batch_id = self.statement_queue_presenter.model.get_batch_id()
        if batch_id:
            # Stale-lock detection: if the queue is locked but no results were
            # persisted (e.g. app closed mid-batch), treat it as abandoned and
            # unlock automatically so the user is not stuck.
            result_ids = self.stan.statement_result_model.get_result_ids_for_batch(
                batch_id
            )
            if not result_ids:
                print(
                    f"Stale lock detected for batch {batch_id} — no persisted results. "
                    "Clearing batch_id automatically."
                )
                self.stan.statement_queue_model.clear_batch_id()
                # Also remove any orphaned batch duration record
                self.stan.batch_model.delete_batch(batch_id)
                self.statement_queue_presenter.update_view()
            else:
                # Genuine restore: repopulate in-memory models from DB.
                # Do NOT auto-navigate to the results view — the user should
                # start from the queue and press "View Results" themselves.
                self.statement_result_presenter.load_results_from_db(
                    batch_id, self.stan.current_project_id
                )

    def __refresh_project_summary(self) -> None:
        """Update the project summary label synchronously from project.db."""
        if self.stan.current_project_paths is None:
            return
        self.stan.project_view.summary_label.setText(
            get_project_summary(self.stan.current_project_paths.root)
        )

    @pyqtSlot(Path, bsp.PdfResult, int, str)
    def statement_imported(
        self,
        file_path: Path,
        stmt: bsp.PdfResult,
        progress_bar_value: int,
        queue_id: str,
    ) -> None:
        self.stan.statement_result_presenter.view.progressBar.setValue(
            progress_bar_value
        )

        # Show the results block while import is in progress
        self.show_results()

        # Extract display fields from the typed payload
        id_account: str | None = None
        statement_date: str | None = None
        payments_in: float | None = None
        payments_out: float | None = None
        error_type: str | None = None
        message: str | None = None

        if stmt.result == "SUCCESS":
            info = stmt.payload.statement_info  # type: ignore[union-attr]
            id_account = info.id_account
            statement_date = str(info.statement_date)
            payments_in = float(info.payments_in)
            payments_out = float(info.payments_out)
        elif stmt.result == "REVIEW":
            info = stmt.payload.statement_info  # type: ignore[union-attr]
            id_account = info.id_account
            statement_date = str(info.statement_date)
            payments_in = float(info.payments_in)
            payments_out = float(info.payments_out)
            message = stmt.payload.message  # type: ignore[union-attr]
        else:
            error_type = stmt.payload.error_type  # type: ignore[union-attr]
            message = stmt.payload.message  # type: ignore[union-attr]

        batch_id = self.statement_queue_presenter._current_batch_id or ""

        row = ResultRow(
            result_id="",  # assigned at persist time
            batch_id=batch_id,
            queue_id=queue_id,
            project_id=str(self.stan.current_project_id or ""),
            result=stmt.result,
            file_path=file_path,
            id_account=id_account,
            statement_date=statement_date,
            payments_in=payments_in,
            payments_out=payments_out,
            error_type=error_type,
            message=message,
            pdf_result=stmt,
        )
        self.statement_result_presenter.add_result_to_memory(row)

    @pyqtSlot()
    def on_import_started(self) -> None:
        """Import worker has started: disable result action buttons."""
        self.statement_result_presenter.set_importing(True)

    @pyqtSlot(float)
    def on_import_finished(self, duration_secs: float) -> None:
        """Worker thread finished: persist batch record and all in-memory results."""
        batch_id = self.statement_queue_presenter._current_batch_id
        if batch_id:
            ok, msg = self.stan.batch_model.create_batch(
                batch_id=batch_id,
                project_id=str(self.stan.current_project_id or ""),
                duration_secs=duration_secs,
            )
            if not ok:
                print(f"WARNING: Could not persist batch duration: {msg}", flush=True)
            self.statement_result_presenter.persist_batch_to_db(batch_id)
        else:
            print("WARNING: on_import_finished called with no current batch_id.")
        # Re-enable action buttons now that import is complete
        self.statement_result_presenter.set_importing(False)

    # ---------------------------------------------------------------------------
    # Show / hide results panel
    # ---------------------------------------------------------------------------

    def show_results(self) -> None:
        """Switch the content area to the results block."""
        self.stan.statement_queue_block.setVisible(False)
        self.stan.statement_result_block.setVisible(True)

    def hide_results(self) -> None:
        """Switch the content area back to the main project view."""
        self.stan.statement_result_block.setVisible(False)
        self.stan.statement_queue_block.setVisible(True)

    # ---------------------------------------------------------------------------
    # Batch lifecycle callbacks
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def on_batch_abandoned(self) -> None:
        """Called when the user abandons a batch from the results view."""
        self.hide_results()
        # Refresh queue view to reflect unlocked state
        self.statement_queue_presenter.update_view()

    @pyqtSlot()
    def on_batch_committed(self) -> None:
        """Called after a batch is successfully committed to project.db.

        Hides the results panel, clears the queue, and resets all queue
        buttons so the user is ready to start a new import.
        """
        self.hide_results()
        self.statement_queue_presenter.clear_all_items()
        self.statement_queue_presenter.update_view()
        # build_datamart ran as part of the commit — refresh the summary counts.
        self.__refresh_project_summary()

    @pyqtSlot()
    def open_admin_dialog(self) -> None:
        self.stan.admin_presenter.refresh_combos()
        self.stan.admin_view.exec()
