from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanLabel,
    StanProgressBar,
    StanTableView,
    StanTabWidget,
    StanWidget,
)
from openstan.paths import Paths


class StatementResultView(StanWidget):
    """Results view shown after a statement import batch completes.

    Three result categories (SUCCESS / REVIEW / FAILURE) are presented as tabs
    inside a ``QTabWidget``.  Each tab is hidden when its count is zero and
    shown as soon as the first row arrives, so the widget stays uncluttered
    during sparse batches.

    Action buttons:
    * ``buttonCloseResults``    — navigate back to the queue view; queue stays locked.
    * ``buttonAbandonBatch``    — delete all results and unlock the queue.
    * ``buttonViewDebugInfo``   — open the Debug Information modal; enabled when any
                                  non-success rows exist.
    * ``buttonCommitBatch``     — commit results to the project database; enabled only
                                  when n_success > 0.
    """

    header = "#### Statement Import Results"

    # Tab indices — kept as class constants so the presenter can reference them
    # without hard-coding magic numbers.
    TAB_SUCCESS = 0
    TAB_REVIEW = 1
    TAB_FAILURE = 2

    def __init__(self) -> None:
        super().__init__()
        outer_layout = QVBoxLayout()

        # ── Progress Bar ───────────────────────────────────────────────────
        self.progressBar = StanProgressBar()
        self.progressBar.setMinimumWidth(800)
        outer_layout.addWidget(self.progressBar, alignment=Qt.AlignmentFlag.AlignTop)

        # ── Summary label ──────────────────────────────────────────────────
        self.labelStatementsProcessed = StanLabel(
            "Total: 0  |  Pending: 0  |  Processed: 0  |  Success: 0  |  Review: 0  |  Failed: 0"
        )
        outer_layout.addWidget(
            self.labelStatementsProcessed, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ── Tabbed result sections ─────────────────────────────────────────
        self.results_tabs = StanTabWidget()
        self.results_tabs.setMinimumWidth(800)

        # SUCCESS tab
        self.success_table = StanTableView()
        self.results_tabs.addTab(self.success_table, "SUCCESS (0)")

        # REVIEW tab
        self.review_table = StanTableView()
        self.results_tabs.addTab(self.review_table, "REVIEW (0)")

        # FAILURE tab
        self.failure_table = StanTableView()
        self.results_tabs.addTab(self.failure_table, "FAILURE (0)")

        # All tabs start hidden; the presenter shows them as rows arrive
        self.results_tabs.setTabVisible(self.TAB_SUCCESS, False)
        self.results_tabs.setTabVisible(self.TAB_REVIEW, False)
        self.results_tabs.setTabVisible(self.TAB_FAILURE, False)

        outer_layout.addWidget(self.results_tabs, stretch=1)

        # ── Batch action buttons ───────────────────────────────────────────
        action_buttons = QGridLayout()

        self.buttonCloseResults = StanButton("Close Results")
        self.buttonCloseResults.setIcon(QIcon(Paths.themed_icon("exit.svg")))

        self.buttonAbandonBatch = StanButton("Abandon Batch")
        self.buttonAbandonBatch.setIcon(QIcon(Paths.themed_icon("bin.svg")))

        self.buttonViewDebugInfo = StanButton("View Debug Info")
        self.buttonViewDebugInfo.setIcon(QIcon(Paths.themed_icon("bug.svg")))
        self.buttonViewDebugInfo.setEnabled(
            False
        )  # enabled by presenter when non-success rows exist

        self.buttonCommitBatch = StanButton("Commit Batch")
        self.buttonCommitBatch.setIcon(QIcon(Paths.themed_icon("tick.svg")))
        self.buttonCommitBatch.setEnabled(
            False
        )  # enabled by presenter when n_success > 0

        action_buttons.addWidget(
            self.buttonCloseResults, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )
        action_buttons.addWidget(
            self.buttonAbandonBatch, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )
        action_buttons.addWidget(
            self.buttonViewDebugInfo, 0, 2, alignment=Qt.AlignmentFlag.AlignRight
        )
        action_buttons.addWidget(
            self.buttonCommitBatch, 0, 3, alignment=Qt.AlignmentFlag.AlignRight
        )

        outer_layout.addLayout(action_buttons)
        self.setLayout(outer_layout)
