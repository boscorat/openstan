from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSlot as Slot

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
        # self.project_view = self.project_presenter.view
        self.footer_view = self.stan.footer_view

        # signals
        self.project_presenter.view.selection.currentIndexChanged.connect(self.project_selection_changed)
        self.session_presenter.db_lock_signal.connect(self.db_lock_handler)
        self.statement_queue_presenter.statement_imported.connect(self.statement_imported)
        self.statement_queue_presenter.import_finished.connect(self.stan.statement_result_presenter.show_buttons_based_on_results)

        # add a new user to the database if not exists
        self.stan.userID = self.stan.user_model.user_id_from_username(self.stan.username)
        if not self.stan.userID:
            success: bool = bool(False)
            msg: str = ""
            success, self.stan.userID, msg = self.stan.user_presenter.create_new_user(self.stan.username, self.stan.sessionID)
            if not success:
                self.stan.error_db_lock.showMessage(f"{msg}\nThe application will close shortly.")
        # start a new session
        if self.stan.userID:
            success: bool = bool(False)
            msg: str = ""
            success, self.stan.sessionID, msg = self.stan.session_presenter.new_session(self.stan.userID)
            if not success:
                self.stan.error_db_lock.showMessage(f"{msg}\nThe application will close shortly.")

        # pass sessionID to other presenters
        self.project_presenter.sessionID = self.stan.sessionID
        self.statement_queue_presenter.sessionID = self.stan.sessionID

        # update current project info
        self.update_current_project_info(self.project_presenter.view.selection.currentIndex())

    @Slot()
    def db_lock_handler(self) -> None:
        self.stan.error_db_lock.showMessage("Database is locked! Another active session may exist.\nThe application will close shortly.")

    @Slot(int)
    def project_selection_changed(self, index: int) -> None:
        # Handle the project selection change logic here
        self.update_current_project_info(index)

    def cleanup_before_exit(self) -> None:
        self.session_presenter.end_active_sessions()
        print("CLEANUP: StanPresenter.cleanup_before_exit: Session ended.")

    def update_current_project_info(self, index: int) -> None:
        current_record: QSqlRecord = self.project_presenter.model.record(index)
        self.stan.current_project_name = current_record.value("project_name")
        self.stan.current_project_id = current_record.value("project_ID")
        self.stan.statement_queue_presenter.projectID = self.stan.current_project_id
        self.stan.statement_queue_presenter.update_view()
        self.footer_view.labelProject.setText(f"##### Project: {self.stan.current_project_name} (ID: {self.stan.current_project_id})")

    @Slot(object, int)
    def statement_imported(self, stmt, progress_bar_value) -> None:
        self.stan.statement_result_presenter.view.progressBar.setValue(progress_bar_value)
        self.stan.project_view.setVisible(False)
        self.stan.statement_queue_block.setVisible(False)
        self.stan.export_block.setVisible(False)
        self.stan.statement_result_block.setVisible(True)
        self.stan.statement_result_presenter.model.add_statement(stmt)
        self.stan.statement_result_presenter.on_model_updated()
