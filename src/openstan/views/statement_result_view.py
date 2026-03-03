from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGridLayout

from openstan.components import (
    Qt,
    StanButton,
    StanLabel,
    StanProgressBar,
    StanTreeView,
    StanWidget,
)
from openstan.paths import Paths


class StatementResultView(StanWidget):
    header = "#### Statement Import Results"

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout()
        # Progress Bar
        self.progressBar = StanProgressBar()
        self.progressBar.setMinimumWidth(800)
        layout.addWidget(
            self.progressBar,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )
        # Tree View for statement results
        self.tree = StanTreeView()
        self.tree.setMinimumWidth(800)
        self.tree.setMinimumHeight(520)
        layout.addWidget(
            self.tree,
            1,
            0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )

        # summary info labels
        self.labelStatementsProcessed = StanLabel(
            "Statements Processed: 0  Successful: 0  Failed: 0"
        )
        layout.addWidget(
            self.labelStatementsProcessed, 2, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # decision buttons
        self.buttonAddSuccessful = StanButton("Add Successful")
        self.buttonAddSuccessful.setIcon(QIcon(Paths.icon("tick.svg")))
        self.buttonAbandonFailed = StanButton("Abandon Failed")
        self.buttonAbandonFailed.setIcon(QIcon(Paths.icon("bin.svg")))
        self.buttonAbandonSuccessful = StanButton("Abandon Successful")
        self.buttonAbandonSuccessful.setIcon(QIcon(Paths.icon("bin.svg")))
        self.buttonDebugFailed = StanButton("Debug Failed")
        self.buttonDebugFailed.setIcon(QIcon(Paths.icon("bug.svg")))
        self.buttonExit = StanButton("Exit Results View")
        self.buttonExit.setIcon(QIcon(Paths.icon("exit.svg")))

        # hide buttons initially
        self.buttonAddSuccessful.setVisible(False)
        self.buttonAbandonFailed.setVisible(False)
        self.buttonAbandonSuccessful.setVisible(False)
        self.buttonDebugFailed.setVisible(False)
        self.buttonExit.setVisible(False)

        # button layout — row 0: abandon successful | add successful | exit
        #                  row 1: debug failed      | abandon failed
        button_layout = QGridLayout()
        button_layout.addWidget(
            self.buttonAbandonSuccessful, 0, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        button_layout.addWidget(
            self.buttonAddSuccessful, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )
        button_layout.addWidget(
            self.buttonExit, 0, 2, alignment=Qt.AlignmentFlag.AlignRight
        )
        button_layout.addWidget(
            self.buttonDebugFailed, 1, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        button_layout.addWidget(
            self.buttonAbandonFailed, 1, 1, alignment=Qt.AlignmentFlag.AlignRight
        )
        layout.addLayout(
            button_layout,
            3,
            0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        self.setLayout(layout)
