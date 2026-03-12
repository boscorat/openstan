from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout

from openstan.components import (
    Qt,
    StanButton,
    StanLabel,
    StanProgressBar,
    StanTableView,
    StanWidget,
)
from openstan.paths import Paths


class StatementResultView(StanWidget):
    header = "#### Statement Import Results"

    def __init__(self) -> None:
        super().__init__()
        outer_layout = QVBoxLayout()

        # Progress Bar
        self.progressBar = StanProgressBar()
        self.progressBar.setMinimumWidth(800)
        outer_layout.addWidget(self.progressBar, alignment=Qt.AlignmentFlag.AlignTop)

        # Summary label
        self.labelStatementsProcessed = StanLabel(
            "Processed: 0  |  Success: 0  |  Review: 0  |  Failed: 0"
        )
        outer_layout.addWidget(
            self.labelStatementsProcessed, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ── SUCCESS section ────────────────────────────────────────────────
        self.labelSuccess = StanLabel("##### SUCCESS (0)")
        self.success_table = StanTableView()
        self.success_table.setMinimumWidth(800)
        self.success_table.setMinimumHeight(160)

        success_buttons = QGridLayout()
        self.buttonAbandonSuccessful = StanButton("Abandon Successful")
        self.buttonAbandonSuccessful.setIcon(QIcon(Paths.icon("bin.svg")))
        self.buttonAddSuccessful = StanButton("Add Successful")
        self.buttonAddSuccessful.setIcon(QIcon(Paths.icon("tick.svg")))
        success_buttons.addWidget(
            self.buttonAbandonSuccessful, 0, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        success_buttons.addWidget(
            self.buttonAddSuccessful, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )

        outer_layout.addWidget(self.labelSuccess, alignment=Qt.AlignmentFlag.AlignLeft)
        outer_layout.addWidget(self.success_table)
        outer_layout.addLayout(success_buttons)

        # ── REVIEW section ─────────────────────────────────────────────────
        self.labelReview = StanLabel("##### REVIEW (0)")
        self.review_table = StanTableView()
        self.review_table.setMinimumWidth(800)
        self.review_table.setMinimumHeight(120)

        outer_layout.addWidget(self.labelReview, alignment=Qt.AlignmentFlag.AlignLeft)
        outer_layout.addWidget(self.review_table)

        # ── FAILURE section ────────────────────────────────────────────────
        self.labelFailure = StanLabel("##### FAILURE (0)")
        self.failure_table = StanTableView()
        self.failure_table.setMinimumWidth(800)
        self.failure_table.setMinimumHeight(120)

        failure_buttons = QGridLayout()
        self.buttonDebugFailed = StanButton("Debug Failed")
        self.buttonDebugFailed.setIcon(QIcon(Paths.icon("bug.svg")))
        self.buttonAbandonFailed = StanButton("Abandon Failed")
        self.buttonAbandonFailed.setIcon(QIcon(Paths.icon("bin.svg")))
        failure_buttons.addWidget(
            self.buttonDebugFailed, 0, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        failure_buttons.addWidget(
            self.buttonAbandonFailed, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )

        outer_layout.addWidget(self.labelFailure, alignment=Qt.AlignmentFlag.AlignLeft)
        outer_layout.addWidget(self.failure_table)
        outer_layout.addLayout(failure_buttons)

        # ── Global exit button ─────────────────────────────────────────────
        self.buttonExit = StanButton("Exit Results View")
        self.buttonExit.setIcon(QIcon(Paths.icon("exit.svg")))
        outer_layout.addWidget(self.buttonExit, alignment=Qt.AlignmentFlag.AlignRight)

        # Hide all action buttons initially; presenter reveals them once
        # results are available.
        self.buttonAddSuccessful.setVisible(False)
        self.buttonAbandonSuccessful.setVisible(False)
        self.buttonDebugFailed.setVisible(False)
        self.buttonAbandonFailed.setVisible(False)
        self.buttonExit.setVisible(False)

        self.setLayout(outer_layout)
