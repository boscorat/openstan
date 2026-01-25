import os
import sys
from uuid import uuid4

from PyQt6.QtCore import QSysInfo, Qt, qDebug
from PyQt6.QtSql import QSqlDatabase
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from openstan.gui.components import StanErrorMessage, StanLabel  # mostly widget subclasses
from openstan.gui.models import ProjectModel, SessionModel, StatementQueueModel, StatementQueueTreeModel, UserModel
from openstan.gui.paths import Paths
from openstan.gui.presenters import ProjectPresenter, SessionPresenter, StanPresenter, StatementQueuePresenter, UserPresenter
from openstan.gui.views import ContentFrameView, ExportView, FooterView, ProjectView, StatementQueueView, TitleView


def main():
    qDebug("Starting StanCafe GUI application...")
    app: QApplication = QApplication(sys.argv)

    # set application style based on OS
    if QSysInfo.productType() == "windows":
        app.setStyle("Windows")
    # elif QSysInfo.productType() in ("ios", "tvos", "watchos", "macos", "darwin"):
    #     app.setStyle("macOS")
    else:
        app.setStyle("Fusion")

    # database connections
    gui_db: QSqlDatabase = QSqlDatabase("QSQLITE")
    gui_db.setDatabaseName(Paths.databases("gui.db"))
    gui_db.open()

    # user and session details
    username: str = os.path.expanduser("~").split(os.sep)[-1]
    sessionID = uuid4().hex

    window: Stan = Stan(gui_db=gui_db, sessionID=sessionID, username=username)
    window.setWindowOpacity(0.5)
    window.show()

    app.exec()

    window.gui_db.close()


class Stan(QMainWindow):
    def __init__(self, gui_db, sessionID, username):
        super().__init__()
        self.gui_db = gui_db
        self.userID = None
        self.sessionID = sessionID
        self.username = username
        self.current_project_name = None
        self.current_project_id = None

        # error message dialogs
        self.error_db_lock = StanErrorMessage(self)
        self.error_db_lock.accepted.connect(self.close)

        # models initiation
        self.user_model = UserModel(db=gui_db)
        self.session_model = SessionModel(db=gui_db)
        self.project_model = ProjectModel(db=gui_db)
        self.statement_queue_model = StatementQueueModel(db=gui_db)
        self.statement_queue_tree_model = StatementQueueTreeModel(db=gui_db)
        # main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # master widgets
        self.stan = QWidget()
        self.title_view = TitleView()
        self.project_view = ProjectView()
        self.footer_view = FooterView(stan=self)

        # process flow widgets
        self.statement_queue_view = StatementQueueView(stan=self)
        self.export_view = ExportView(stan=self)

        statement_queue_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_queue_view.header), 0, 0),
                (self.statement_queue_view, 1, 0),
            ]
        )

        export_block = ContentFrameView(
            widgets=[
                (StanLabel(self.export_view.header), 0, 0),
                (self.export_view, 1, 0),
            ]
        )

        # hook up the presenters
        self.user_presenter = UserPresenter(model=self.user_model, view=None)
        self.session_presenter = SessionPresenter(model=self.session_model, view=None)
        self.project_presenter = ProjectPresenter(model=self.project_model, view=self.project_view)
        self.statement_queue_presenter = StatementQueuePresenter(
            model=self.statement_queue_model, view=self.statement_queue_view, tree_model=self.statement_queue_tree_model
        )
        self.stan_presenter = StanPresenter(stan=self)

        # assemble layout
        layout.addWidget(self.title_view, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.project_view, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(statement_queue_block, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(export_block, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.footer_view, alignment=Qt.AlignmentFlag.AlignBottom)

        self.stan.setLayout(layout)
        self.setCentralWidget(self.stan)

    def closeEvent(self, a0):
        print("Window is closing")
        if self.sessionID:
            self.stan_presenter.cleanup_before_exit()
        if a0:
            a0.accept()  # Accept


if __name__ == "__main__":
    main()
