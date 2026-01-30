from PyQt6.QtWidgets import QGridLayout

from openstan.components import Qt, StanLabel, StanTreeView, StanWidget


class StatementResultView(StanWidget):
    header = "#### Statement Import Results"

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout()
        # Tree View for statement results
        self.tree = StanTreeView()
        self.tree.setMinimumWidth(800)
        self.tree.setMinimumHeight(50)
        layout.addWidget(self.tree, 0, 0, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)

        # summary info labels
        self.labelStatementsProcessed = StanLabel("Statements Processed: 0  Successful: 0  Failed: 0")
        layout.addWidget(self.labelStatementsProcessed, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
