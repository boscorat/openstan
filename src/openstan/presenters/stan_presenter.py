from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
from bank_statement_parser import ProjectPaths
from PyQt6.QtCore import QObject, pyqtSlot

from openstan.models.statement_result_model import ResultRow
from openstan.presenters.project_presenter import get_project_info

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
        self.nav_view = self.stan.project_nav_view

        # ── Signal wiring ──────────────────────────────────────────────────────
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

        # Nav button clicks
        self.nav_view.button_info.clicked.connect(self.__nav_to_info)
        self.nav_view.button_import.clicked.connect(self.__nav_to_import)
        self.nav_view.button_export.clicked.connect(self.__nav_to_export)
        self.nav_view.button_reports.clicked.connect(self.__nav_to_reports)

        # Gap detail dialog
        self.stan.project_info_view.gap_clicked.connect(self.__show_gap_detail)

        # ── Bootstrap ──────────────────────────────────────────────────────────
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

        # update current project info (sets nav state + panel)
        self.update_current_project_info(
            self.project_presenter.view.selection.currentIndex()
        )

    # ---------------------------------------------------------------------------
    # DB lock
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def db_lock_handler(self) -> None:
        self.stan.error_db_lock.showMessage(
            "Database is locked! Another active session may exist.\nThe application will close shortly."
        )

    # ---------------------------------------------------------------------------
    # Project selection
    # ---------------------------------------------------------------------------

    @pyqtSlot(int)
    def project_selection_changed(self, index: int) -> None:
        self.update_current_project_info(index)

    def cleanup_before_exit(self) -> None:
        # Cancel any in-progress debug worker so it stops at its next iteration
        cancel = self.statement_result_presenter._debug_cancel  # noqa: SLF001
        if cancel is not None:
            cancel.set()
        self.session_presenter.end_active_sessions()
        print("CLEANUP: StanPresenter.cleanup_before_exit: Session ended.")

    def update_current_project_info(self, index: int) -> None:
        current_record: "QSqlRecord" = self.project_presenter.model.record(index)
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

        # Refresh project info panel and update nav button visibility.
        self.__refresh_project_info()

        # Clear any in-memory results from the previous project.
        self.statement_result_presenter.clear_for_project_change()

        # Session restore: check for a locked batch on this project.
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

    # ---------------------------------------------------------------------------
    # Navigation helpers
    # ---------------------------------------------------------------------------

    def __refresh_project_info(self) -> None:
        """Query project.db and push the result into the Project Info panel.

        Also updates nav button visibility based on whether data exists.
        """
        if self.stan.current_project_paths is None:
            return
        info = get_project_info(self.stan.current_project_paths.root)
        self.stan.project_info_view.update(info)
        self.__update_nav_for_project(has_data=info is not None)

    def __update_nav_for_project(self, *, has_data: bool) -> None:
        """Show/hide data-dependent buttons and navigate to the default panel.

        Projects with data default to Project Info; new/empty projects default
        to Import Statements (the only always-available panel).
        """
        self.nav_view.button_info.setVisible(has_data)
        self.nav_view.button_export.setVisible(has_data)
        self.nav_view.button_reports.setVisible(has_data)

        if has_data:
            self.__nav_to_info()
        else:
            self.__nav_to_import()

    def __set_panel(self, idx: int) -> None:
        """Switch the stacked content widget to the given index."""
        self.stan.content_stack.setCurrentIndex(idx)

    @pyqtSlot()
    def __nav_to_info(self) -> None:
        self.nav_view.button_info.setChecked(True)
        self.__set_panel(self.stan.NAV_IDX_INFO)

    @pyqtSlot()
    def __nav_to_import(self) -> None:
        self.nav_view.button_import.setChecked(True)
        self.__set_panel(self.stan.NAV_IDX_IMPORT)

    @pyqtSlot()
    def __nav_to_export(self) -> None:
        self.nav_view.button_export.setChecked(True)
        self.__set_panel(self.stan.NAV_IDX_EXPORT)

    @pyqtSlot()
    def __nav_to_reports(self) -> None:
        self.nav_view.button_reports.setChecked(True)
        self.__set_panel(self.stan.NAV_IDX_REPORTS)

    # ---------------------------------------------------------------------------
    # Results panel (import flow — overlays import panel)
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def __show_gap_detail(self) -> None:
        """Open the gap detail dialog from the Project Info panel."""
        self.stan.project_info_view.gap_dialog.exec()

    def show_results(self) -> None:
        """Switch the content area to the results block."""
        self.__set_panel(self.stan.NAV_IDX_RESULTS)
        # Uncheck all nav buttons — results is not a user-navigable panel
        for btn in self.nav_view._group.buttons():  # noqa: SLF001
            btn.setChecked(False)

    def hide_results(self) -> None:
        """Return from the results block to the import panel."""
        self.__nav_to_import()

    # ---------------------------------------------------------------------------
    # Statement import callbacks
    # ---------------------------------------------------------------------------

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
        buttons so the user is ready to start a new import.  Also refreshes
        the project summary and nav button visibility, since build_datamart ran
        as part of the commit and the project now has data.
        """
        self.statement_queue_presenter.clear_all_items()
        self.statement_queue_presenter.update_view()
        # Refresh project info — the project may now have data for the first time.
        self.__refresh_project_info()

    # ---------------------------------------------------------------------------
    # Admin
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def open_admin_dialog(self) -> None:
        self.stan.admin_presenter.refresh_combos()
        self.stan.admin_view.exec()
