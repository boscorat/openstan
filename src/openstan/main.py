import os
import sys
from pathlib import Path
from uuid import uuid4

from bank_statement_parser import ProjectPaths
from PyQt6.QtCore import QSysInfo, QThreadPool, qDebug
from PyQt6.QtSql import QSqlDatabase
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout

from openstan.components import (  # mostly widget subclasses
    Qt,
    QWidget,
    StanErrorMessage,
    StanLabel,
)
from openstan.data.create_gui_db import create_gui_db
from openstan.models import (
    FailureResultModel,
    ProjectModel,
    ReviewResultModel,
    SessionModel,
    StatementQueueModel,
    StatementQueueTreeModel,
    StatementResultModel,
    StatementResultPayloadModel,
    SuccessResultModel,
    UserModel,
)
from openstan.paths import Paths
from openstan.presenters import (
    AdminPresenter,
    ProjectPresenter,
    SessionPresenter,
    StanPresenter,
    StatementQueuePresenter,
    StatementResultPresenter,
    UserPresenter,
)
from openstan.views import (
    AdminView,
    ContentFrameView,
    FooterView,
    ProjectView,
    StatementQueueView,
    StatementResultView,
    TitleView,
)


def main() -> None:
    qDebug("Starting StanCafe GUI application...")
    app: QApplication = QApplication(sys.argv)

    # set application style based on OS
    if QSysInfo.productType() == "windows":
        app.setStyle("Windows")
    elif QSysInfo.productType() in ("ios", "tvos", "watchos", "macos", "darwin"):
        app.setStyle("macOS")
    else:
        app.setStyle("Fusion")

    # bootstrap: create gui.db if it doesn't exist (e.g. fresh clone / install)
    gui_db_path = Path(Paths.databases("gui.db"))
    if not gui_db_path.exists():
        create_gui_db(gui_db_path)

    # database connections
    gui_db: QSqlDatabase = QSqlDatabase("QSQLITE")
    gui_db.setDatabaseName(Paths.databases("gui.db"))
    gui_db.open()

    # user and session details
    username: str = os.path.expanduser("~").split(os.sep)[-1]
    sessionID: str = uuid4().hex

    window: Stan = Stan(gui_db=gui_db, sessionID=sessionID, username=username)
    window.show()

    app.exec()

    window.gui_db.close()


class Stan(QMainWindow):
    def __init__(self, gui_db, sessionID, username) -> None:
        super().__init__()
        self.threadpool = QThreadPool()
        print(
            "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        )
        self.gui_db = gui_db
        self.userID = None
        self.sessionID = sessionID
        self.username = username
        self.current_project_name = None
        self.current_project_id = None
        self.current_project_paths: ProjectPaths | None = None

        # error message dialogs
        self.error_db_lock = StanErrorMessage(self)
        self.error_db_lock.accepted.connect(self.close)

        # ── Models ────────────────────────────────────────────────────────
        self.user_model = UserModel(db=gui_db)
        self.session_model = SessionModel(db=gui_db)
        self.project_model = ProjectModel(db=gui_db)
        self.statement_queue_model = StatementQueueModel(db=gui_db)
        self.statement_queue_tree_model = StatementQueueTreeModel(db=gui_db)
        self.success_result_model = SuccessResultModel()
        self.review_result_model = ReviewResultModel()
        self.failure_result_model = FailureResultModel()
        self.statement_result_model = StatementResultModel(db=gui_db)
        self.statement_result_payload_model = StatementResultPayloadModel(db=gui_db)

        # ── Views ─────────────────────────────────────────────────────────
        self.stan = QWidget()
        self.title_view = TitleView()
        self.project_view = ProjectView()
        self.footer_view = FooterView()
        self.admin_view = AdminView(parent=self)

        self.statement_queue_view = StatementQueueView()
        self.statement_result_view = StatementResultView()

        # stretch_content=True lets the inner tree / tab widget grow vertically
        self.statement_queue_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_queue_view.header), 0, 0),
                (self.statement_queue_view, 1, 0),
            ],
            stretch_content=True,
        )

        self.statement_result_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_result_view.header), 0, 0),
                (self.statement_result_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.statement_result_block.setVisible(False)  # hide initially

        # ── Presenters ────────────────────────────────────────────────────
        self.user_presenter = UserPresenter(model=self.user_model, view=None)
        self.session_presenter = SessionPresenter(model=self.session_model, view=None)
        self.project_presenter = ProjectPresenter(
            model=self.project_model, view=self.project_view
        )
        self.statement_queue_presenter = StatementQueuePresenter(
            model=self.statement_queue_model,
            view=self.statement_queue_view,
            tree_model=self.statement_queue_tree_model,
            threadpool=self.threadpool,
        )
        self.statement_result_presenter = StatementResultPresenter(
            success_model=self.success_result_model,
            review_model=self.review_result_model,
            failure_model=self.failure_result_model,
            result_model=self.statement_result_model,
            payload_model=self.statement_result_payload_model,
            queue_model=self.statement_queue_model,
            view=self.statement_result_view,
        )
        self.admin_presenter = AdminPresenter(
            model=self.project_model, view=self.admin_view, stan=self
        )
        self.stan_presenter = StanPresenter(stan=self)

        # ── Layout ────────────────────────────────────────────────────────
        # VBox: title → project selector → [queue block | result block] → footer
        # The queue/result block row has stretch=1 so it absorbs all extra
        # vertical space when the window is resized.  Footer has stretch=0
        # so it stays pinned to the bottom.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.title_view, stretch=0)
        layout.addWidget(
            self.project_view, stretch=0, alignment=Qt.AlignmentFlag.AlignTop
        )
        layout.addWidget(self.statement_queue_block, stretch=1)
        layout.addWidget(self.statement_result_block, stretch=1)
        layout.addWidget(self.footer_view, stretch=0)

        self.stan.setLayout(layout)
        self.setCentralWidget(self.stan)

    def closeEvent(self, a0) -> None:
        print("Window is closing")
        if self.sessionID:
            self.stan_presenter.cleanup_before_exit()
        if a0:
            a0.accept()


if __name__ == "__main__":
    main()
