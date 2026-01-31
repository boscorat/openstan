from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog, QGridLayout

from openstan.components import Qt, StanButton, StanTreeView, StanWidget
from openstan.paths import Paths


class FileDialog(QFileDialog):
    caption = "Statement pdf files"
    initial_filter = "Portable Document Format files (*.pdf)"  # Select one from the list.

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
        self.setNameFilter(self.initial_filter)
        self.selectNameFilter(self.initial_filter)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)


class FolderDialog(QFileDialog):
    caption = "Statement folders selection"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
        self.setFileMode(QFileDialog.FileMode.Directory)


class StatementQueueView(StanWidget):
    header = "#### Statement Queue - Select any new pdf statements to add to your project"

    def __init__(self) -> None:
        super().__init__()
        self.file_dialog = FileDialog()  # create file dialog instance - will be triggered on button click in StatementQueuePresenter
        self.folder_dialog = FolderDialog()  # create folder dialog instance - will be triggered on button click in StatementQueuePresenter
        layout = QGridLayout()
        # three buttons for folder import, file import, and remove selected
        self.buttonAddFolders = StanButton("Add Folders of Statements")
        self.buttonAddFiles = StanButton("Add Individual Statement Files")
        self.buttonRemove = StanButton("Remove Selected")
        self.buttonClear = StanButton("Clear All Statements")
        self.buttonAddFolders.setIcon(QIcon(Paths.icon("folder_add.svg")))
        self.buttonAddFiles.setIcon(QIcon(Paths.icon("file_add.svg")))
        self.buttonRemove.setIcon(QIcon(Paths.icon("file_remove.svg")))
        self.buttonClear.setIcon(QIcon(Paths.icon("folder_remove.svg")))
        layout.addWidget(self.buttonAddFolders, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.buttonAddFiles, 0, 1, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.buttonRemove, 2, 0, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.buttonClear, 2, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Tree View for statements
        self.tree = StanTreeView()
        self.tree.setMinimumWidth(800)
        layout.addWidget(self.tree, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Run Import Button
        self.buttonRunImport = StanButton("Run Statement Import")
        self.buttonRunImport.setIcon(QIcon(Paths.icon("run.svg")))
        self.buttonRunImport.setDisabled(True)
        layout.addWidget(self.buttonRunImport, 4, 1, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)
