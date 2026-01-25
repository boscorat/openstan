from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileDialog, QGridLayout

from openstan.gui.components import StanButton, StanTreeView, StanWidget
from openstan.gui.paths import Paths

# from views.examples import TreeViewExample


class FileDialog(QFileDialog):
    caption = "Statement pdf files"
    initial_filter = "Portable Document Format files (*.pdf)"  # Select one from the list.

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
        self.setNameFilter(self.initial_filter)
        self.selectNameFilter(self.initial_filter)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)
        # if self.exec() == 1:
        #     print("Files selected:", self.selectedFiles())


class FolderDialog(QFileDialog):
    caption = "Statement folders selection"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.caption)
        self.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
        self.setFileMode(QFileDialog.FileMode.Directory)
        # if self.exec() == 1:
        #     print("Folder selected:", self.selectedFiles())


class StatementQueueView(StanWidget):
    header = "#### Statement Queue - Select any new pdf statements to add to your project"

    def __init__(self, stan):
        super().__init__()
        self.userID = stan.userID
        self.sessionID = stan.sessionID
        self.projectID = stan.current_project_id
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
        # self.buttonClear.setIcon(QIcon(Paths.icon("folder_remove.svg")))
        layout.addWidget(self.buttonAddFolders, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.buttonAddFiles, 0, 1, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.buttonRemove, 2, 0, alignment=Qt.AlignmentFlag.AlignTop)
        # layout.addWidget(self.buttonClear, 2, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # # date table view for testing
        # self.table = QTableView()
        # layout.addWidget(self.table, 2, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Tree View for statements
        self.tree = StanTreeView()
        layout.addWidget(self.tree, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignVCenter)

        # signals
        # self.buttonAddFiles.clicked.connect(lambda: FileDialog())
        # self.buttonAddFolders.clicked.connect(lambda: self.add_folders(parent.db))

        # Run Import Button
        self.buttonRunImport = StanButton("Run Statement Import")
        self.buttonRunImport.setIcon(QIcon(Paths.icon("run.svg")))
        self.buttonRunImport.setDisabled(True)
        layout.addWidget(self.buttonRunImport, 4, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

    # # slots
    # def add_files(self, db):
    #     caption = "Statement pdf files"
    #     initial_filter = "Portable Document Format files (*.pdf)"  # Select one from the list.

    #     dialog = QFileDialog()
    #     dialog.setWindowTitle(caption)
    #     dialog.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
    #     dialog.setNameFilter(initial_filter)
    #     dialog.selectNameFilter(initial_filter)
    #     dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)

    #     if dialog.exec() == 1:
    #         queue_model = QueueModel(db=db)
    #         for file in dialog.selectedFiles():
    #             queue_model.add_queue_file(
    #                 project_id=self.projectID,
    #                 session_id=self.sessionID,
    #                 status_id=0,  # status_id 0 = pending
    #                 path=file,
    #             )
    #         # self.list.addItems(dialog.selectedFiles())

    # def add_folders(self, db):
    #     caption = "Statement folders selection"

    #     dialog = QFileDialog()
    #     dialog.setWindowTitle(caption)
    #     dialog.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
    #     dialog.setFileMode(QFileDialog.FileMode.Directory)

    #     if dialog.exec() == 1:
    #         queue_model = QueueModel(db=db)
    #         for folder in dialog.selectedFiles():
    #             queue_model.add_queue_folder(
    #                 project_id=self.projectID,
    #                 session_id=self.sessionID,
    #                 status_id=0,  # status_id 0 = pending
    #                 path=folder,
    #             )
