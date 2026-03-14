from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog, QGridLayout

from openstan.components import Qt, StanButton, StanLabel, StanTreeView, StanWidget
from openstan.paths import Paths


class FileDialog(QFileDialog):
    caption = "Statement pdf files"
    initial_filter = (
        "Portable Document Format files (*.pdf)"  # Select one from the list.
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            )
        )
        self.setNameFilter(self.initial_filter)
        self.selectNameFilter(self.initial_filter)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)


class FolderDialog(QFileDialog):
    caption = "Statement folders selection"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            )
        )
        self.setFileMode(QFileDialog.FileMode.Directory)


class StatementQueueView(StanWidget):
    header = (
        "#### Statement Queue - Select any new pdf statements to add to your project"
    )

    def __init__(self) -> None:
        super().__init__()
        self.file_dialog = FileDialog()  # create file dialog instance - will be triggered on button click in StatementQueuePresenter
        self.folder_dialog = FolderDialog()  # create folder dialog instance - will be triggered on button click in StatementQueuePresenter
        layout = QGridLayout()
        layout.setRowStretch(1, 1)  # tree row grows to fill available height

        # ── Queue modification buttons ─────────────────────────────────────
        self.buttonAddFolders = StanButton("Add Folders of Statements")
        self.buttonAddFiles = StanButton("Add Individual Statement Files")
        self.buttonRemove = StanButton("Remove Selected")
        self.buttonClear = StanButton("Clear All Statements")
        self.buttonAddFolders.setIcon(QIcon(Paths.icon("folder_add.svg")))
        self.buttonAddFiles.setIcon(QIcon(Paths.icon("file_add.svg")))
        self.buttonRemove.setIcon(QIcon(Paths.icon("file_remove.svg")))
        self.buttonClear.setIcon(QIcon(Paths.icon("folder_remove.svg")))
        layout.addWidget(
            self.buttonAddFolders, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(
            self.buttonAddFiles, 0, 1, alignment=Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.buttonRemove, 2, 0, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.buttonClear, 2, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # ── Tree View for statements ───────────────────────────────────────
        self.tree = StanTreeView()
        self.tree.setMinimumWidth(800)
        layout.addWidget(self.tree, 1, 0, 1, 2)

        # ── Lock status label (hidden when queue is free) ──────────────────
        self.labelLocked = StanLabel(
            "**Queue locked \u2014 a batch is in progress or awaiting commit / abandon**"
        )
        self.labelLocked.setVisible(False)
        layout.addWidget(
            self.labelLocked, 3, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ── Run Import / View Results buttons ──────────────────────────────
        self.buttonRunImport = StanButton("Run Statement Import")
        self.buttonRunImport.setIcon(QIcon(Paths.icon("run.svg")))
        self.buttonRunImport.setDisabled(True)
        layout.addWidget(
            self.buttonRunImport, 4, 1, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.buttonViewResults = StanButton("View Statement Results")
        self.buttonViewResults.setIcon(QIcon(Paths.icon("download.svg")))
        self.buttonViewResults.setVisible(False)
        layout.addWidget(
            self.buttonViewResults, 4, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.buttonViewCategories = StanButton("View Transaction Categories")
        self.buttonViewCategories.setIcon(QIcon(Paths.icon("tick.svg")))
        self.buttonViewCategories.setVisible(False)
        layout.addWidget(
            self.buttonViewCategories, 5, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.setLayout(layout)
