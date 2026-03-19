import os
import sys
from pathlib import Path
from uuid import uuid4

from bank_statement_parser import ProjectPaths
from PyQt6.QtCore import QSysInfo, QThreadPool, qDebug
from PyQt6.QtSql import QSqlDatabase
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout

from openstan.components import (  # mostly widget subclasses
    Qt,
    QWidget,
    StanErrorMessage,
    StanLabel,
)
from openstan.data.create_gui_db import create_gui_db
from openstan.models import (
    BatchModel,
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
    ExportDataView,
    FooterView,
    ProjectInfoView,
    ProjectNavView,
    ProjectView,
    RunReportsView,
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
        self.batch_model = BatchModel(db=gui_db)

        # ── Views ─────────────────────────────────────────────────────────
        self.stan = QWidget()
        self.title_view = TitleView()
        self.project_view = ProjectView()
        self.project_nav_view = ProjectNavView()
        self.footer_view = FooterView()
        self.admin_view = AdminView(parent=self)

        self.project_info_view = ProjectInfoView()
        self.statement_queue_view = StatementQueueView()
        self.export_data_view = ExportDataView()
        self.run_reports_view = RunReportsView()
        self.statement_result_view = StatementResultView()

        # Each panel is wrapped in a ContentFrameView (header label + content).
        # Index constants mirror the order panels are added to the stacked widget.
        self.project_info_block = ContentFrameView(
            widgets=[
                (StanLabel(self.project_info_view.header), 0, 0),
                (self.project_info_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.statement_queue_block = ContentFrameView(
            widgets=[
                (StanLabel(self.statement_queue_view.header), 0, 0),
                (self.statement_queue_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.export_data_block = ContentFrameView(
            widgets=[
                (StanLabel(self.export_data_view.header), 0, 0),
                (self.export_data_view, 1, 0),
            ],
            stretch_content=True,
        )
        self.run_reports_block = ContentFrameView(
            widgets=[
                (StanLabel(self.run_reports_view.header), 0, 0),
                (self.run_reports_view, 1, 0),
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

        # Stacked widget — one slot per panel.
        # NAV_IDX_* constants are used by StanPresenter to switch panels.
        self.content_stack = QStackedWidget()
        self.NAV_IDX_INFO: int = self.content_stack.addWidget(self.project_info_block)
        self.NAV_IDX_IMPORT: int = self.content_stack.addWidget(
            self.statement_queue_block
        )
        self.NAV_IDX_EXPORT: int = self.content_stack.addWidget(self.export_data_block)
        self.NAV_IDX_REPORTS: int = self.content_stack.addWidget(self.run_reports_block)
        self.NAV_IDX_RESULTS: int = self.content_stack.addWidget(
            self.statement_result_block
        )

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
            batch_model=self.batch_model,
            view=self.statement_result_view,
        )
        self.admin_presenter = AdminPresenter(
            model=self.project_model,
            view=self.admin_view,
            stan=self,  # type: ignore[arg-type]
        )
        self.stan_presenter = StanPresenter(stan=self)  # type: ignore[arg-type]

        # ── Layout ────────────────────────────────────────────────────────
        # VBox: title → project selector → nav bar → stacked content → footer
        # The stacked content row has stretch=1 so it absorbs all extra
        # vertical space when the window is resized.  Footer has stretch=0
        # so it stays pinned to the bottom.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.title_view, stretch=0)
        layout.addWidget(
            self.project_view, stretch=0, alignment=Qt.AlignmentFlag.AlignTop
        )
        layout.addWidget(self.project_nav_view, stretch=0)
        layout.addWidget(self.content_stack, stretch=1)
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
