from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSlot as Slot


class StanPresenter(QObject):
    def __init__(self, stan):
        super().__init__()
        self.stan = stan

        # presenters
        self.project_presenter = self.stan.project_presenter
        self.session_presenter = self.stan.session_presenter
        self.statement_queue_presenter = self.stan.statement_queue_presenter

        # views
        self.project_view = self.project_presenter.view
        self.footer_view = self.stan.footer_view

        # signals
        self.project_view.selection.currentIndexChanged.connect(self.project_selection_changed)
        self.session_presenter.db_lock_signal.connect(self.db_lock_handler)

        # add a new user to the database if not exists
        self.stan.userID = self.stan.user_model.user_id_from_username(self.stan.username)
        if not self.stan.userID:
            self.stan.userID = self.stan.user_presenter.create_new_user(self.stan.username, self.stan.sessionID)
        self.stan.sessionID = self.stan.session_presenter.new_session(self.stan.userID)
        self.project_presenter.sessionID = self.stan.sessionID
        self.statement_queue_presenter.sessionID = self.stan.sessionID

        # update current project info
        self.update_current_project_info()

    @Slot()
    def db_lock_handler(self):
        self.stan.error_db_lock.showMessage("Database is locked! Another active session may exist.\nThe application will close shortly.")

    @Slot(int)
    def project_selection_changed(self, index):
        # Handle the project selection change logic here
        self.update_current_project_info(index)

    def cleanup_before_exit(self):
        self.session_presenter.end_active_sessions(sessionID=self.stan.sessionID, userID=self.stan.userID)
        print("CLEANUP: StanPresenter.cleanup_before_exit: Session ended.")

    def update_current_project_info(self, index=None):
        if index is None:
            index = self.project_view.selection.currentIndex()
        selected_project = self.project_view.selection.model().record(index)
        self.stan.current_project_name = selected_project.value("project_name")
        self.stan.current_project_id = selected_project.value("project_ID")
        self.stan.statement_queue_presenter.projectID = self.stan.current_project_id
        self.stan.statement_queue_presenter.update_view()
        self.footer_view.labelProject.setText(f"##### Project: {self.stan.current_project_name} (ID: {self.stan.current_project_id})")
