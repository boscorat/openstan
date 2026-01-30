import os
import sys
from pathlib import Path
from uuid import uuid4

from bank_statement_parser.modules.classes import statements
from PyQt6.QtCore import QSysInfo, QThreadPool, qDebug
from PyQt6.QtSql import QSqlDatabase
from PyQt6.QtWidgets import QApplication, QGridLayout, QHeaderView, QMainWindow, QVBoxLayout

from openstan.components import (  # mostly widget subclasses
    Qt,
    QWidget,
    StanErrorMessage,
    StanLabel,
    StanPolarsModel,
    StanTableView,
    StanTreeView,
)
from openstan.models import ProjectModel, SessionModel, StatementQueueModel, StatementQueueTreeModel, StatementResultModel, UserModel
from openstan.paths import Paths
from openstan.presenters import ProjectPresenter, SessionPresenter, StanPresenter, StatementQueuePresenter, UserPresenter
from openstan.views import ContentFrameView, ExportView, FooterView, ProjectView, StatementQueueView, TitleView

file = Path("/Users/boscorat/Library/CloudStorage/OneDrive-Personal/OpenStan/Statements/HSBC/2025/HSBC_UK_CUR_31243535_20250608.pdf")
stmt = statements.Statement(file=file)
file2 = Path("/Users/boscorat/Library/CloudStorage/OneDrive-Personal/OpenStan/Statements/HSBC/2025/HSBC_UK_CUR_31243535_20250708.pdf")
stmt2 = statements.Statement(file=file2)
print(stmt)


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

    # database connections
    gui_db: QSqlDatabase = QSqlDatabase("QSQLITE")
    gui_db.setDatabaseName(Paths.databases("gui.db"))
    gui_db.open()

    # user and session details
    username: str = os.path.expanduser("~").split(os.sep)[-1]
    sessionID: str = uuid4().hex

    window: Stan = Stan(gui_db=gui_db, sessionID=sessionID, username=username)
    # window.setWindowOpacity(0.5)
    window.show()

    app.exec()

    window.gui_db.close()


class Stan(QMainWindow):
    def __init__(self, gui_db, sessionID, username) -> None:
        super().__init__()
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
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
        self.statement_result_model = StatementResultModel()
        self.statement_result_model.add_statement(stmt)
        self.statement_result_model.add_statement(stmt2)
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
            model=self.statement_queue_model,
            view=self.statement_queue_view,
            tree_model=self.statement_queue_tree_model,
            threadpool=self.threadpool,
        )
        self.stan_presenter = StanPresenter(stan=self)

        # assemble layout
        layout.addWidget(self.title_view, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.project_view, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(statement_queue_block, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(export_block, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.footer_view, alignment=Qt.AlignmentFlag.AlignBottom)

        self.master_layout = QGridLayout()
        self.master_layout.addLayout(layout, 0, 0)

        self.test_layout = QVBoxLayout()

        # table testing
        self.table_cab = StanTableView()
        self.table_cab.setMinimumWidth(600)
        self.table_head = StanTableView()
        self.table_lines = StanTableView()
        self.model_cab = StanPolarsModel(stmt.checks_and_balances)
        self.model_head = StanPolarsModel(stmt.header_results.collect())
        self.model_lines = StanPolarsModel(stmt.lines_results.collect())
        self.table_cab.setModel(self.model_cab)
        self.table_head.setModel(self.model_head)
        self.table_lines.setModel(self.model_lines)

        self.tree_result = StanTreeView()
        self.tree_result.setMinimumWidth(600)
        self.tree_result.setModel(self.statement_result_model)

        headers: list[QHeaderView | None] = [
            self.table_cab.verticalHeader(),
            self.table_head.verticalHeader(),
            self.table_lines.verticalHeader(),
        ]
        for header in headers:
            if header:
                header.setHidden(True)

        self.test_layout.addWidget(self.table_cab, alignment=Qt.AlignmentFlag.AlignTop)
        self.test_layout.addWidget(self.table_head, alignment=Qt.AlignmentFlag.AlignTop)
        self.test_layout.addWidget(self.table_lines, alignment=Qt.AlignmentFlag.AlignTop)
        self.test_layout.addWidget(self.tree_result, alignment=Qt.AlignmentFlag.AlignTop)

        self.master_layout.addLayout(self.test_layout, 0, 1)

        stmt_name: str = (
            str(stmt.ID_ACCOUNT) + " " + str(self.model_head.df["STD_STATEMENT_DATE"][0])
            if self.model_head.df.height > 0
            else "Unknown Statement"
        )
        print(f"{stmt_name}")

        self.stan.setLayout(self.master_layout)
        self.setCentralWidget(self.stan)

    def closeEvent(self, a0) -> None:
        print("Window is closing")
        if self.sessionID:
            self.stan_presenter.cleanup_before_exit()
        if a0:
            a0.accept()  # Accept


if __name__ == "__main__":
    main()
