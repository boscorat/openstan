from PyQt6.QtCore import QStandardPaths, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QFileDialog, QGridLayout, QSizePolicy

from openstan.components import Qt, StanButton, StanLabel, StanTreeView, StanWidget


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

    # Emitted when the user drops PDF files or folders onto the view.
    # Carries a list of Path-like strings (files and/or directories).
    paths_dropped: pyqtSignal = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.file_dialog = FileDialog()
        self.folder_dialog = FolderDialog()
        layout = QGridLayout()
        layout.setRowStretch(1, 1)  # tree row grows to fill available height

        # ── Queue modification buttons (all four above the tree) ───────────
        self.buttonAddFolders = StanButton("Add Folders of Statements")
        self.buttonAddFiles = StanButton("Add Individual Statement Files")
        self.buttonRemove = StanButton("Remove Selected")
        self.buttonClear = StanButton("Clear All Statements")

        self.buttonAddFolders.set_themed_icon("folder_add.svg")
        self.buttonAddFiles.set_themed_icon("file_add.svg")
        self.buttonRemove.set_themed_icon("file_remove.svg")
        self.buttonClear.set_themed_icon("folder_remove.svg")

        self.buttonAddFolders.setToolTip(
            "Browse for a folder and add all PDF statement files inside it to the queue"
        )
        self.buttonAddFiles.setToolTip(
            "Browse for individual PDF statement files and add them to the queue"
        )
        self.buttonRemove.setToolTip("Remove the selected statement(s) from the queue")
        self.buttonClear.setToolTip("Remove all statements from the queue")

        self.buttonAddFolders.setAccessibleName("Add folders of statements")
        self.buttonAddFiles.setAccessibleName("Add individual statement files")
        self.buttonRemove.setAccessibleName("Remove selected statements")
        self.buttonClear.setAccessibleName("Clear all statements")

        # Allow buttons to grow vertically when text wraps
        for btn in (
            self.buttonAddFolders,
            self.buttonAddFiles,
            self.buttonRemove,
            self.buttonClear,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Remove and Clear start disabled; enabled by presenter based on state
        self.buttonRemove.setEnabled(False)
        self.buttonClear.setEnabled(False)

        layout.addWidget(self.buttonAddFolders, 0, 0)
        layout.addWidget(self.buttonAddFiles, 0, 1)
        layout.addWidget(self.buttonRemove, 0, 2)
        layout.addWidget(self.buttonClear, 0, 3)

        # ── Tree View for statements ───────────────────────────────────────
        self.tree = StanTreeView()
        self.tree.setMinimumWidth(800)
        self.tree.setAccessibleName("Statement queue")
        layout.addWidget(self.tree, 1, 0, 1, 4)

        # ── Lock status label (hidden when queue is free) ──────────────────
        self.labelLocked = StanLabel(
            "**Queue locked \u2014 a batch is in progress or awaiting commit / abandon**"
        )
        self.labelLocked.setVisible(False)
        layout.addWidget(
            self.labelLocked, 2, 0, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft
        )

        # ── Run Import / View Results buttons ──────────────────────────────
        self.buttonRunImport = StanButton("Run Statement Import")
        self.buttonRunImport.set_themed_icon("run.svg")
        self.buttonRunImport.setDisabled(True)
        self.buttonRunImport.setToolTip(
            "Parse and import all queued statement files into the project"
        )
        layout.addWidget(
            self.buttonRunImport, 3, 3, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.buttonViewResults = StanButton("View Statement Results")
        self.buttonViewResults.set_themed_icon("download.svg")
        self.buttonViewResults.setVisible(False)
        self.buttonViewResults.setToolTip(
            "Return to the import results for the current batch"
        )
        layout.addWidget(
            self.buttonViewResults, 3, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.setLayout(layout)

    # ---------------------------------------------------------------------------
    # Drag-and-drop support — accept PDF files and folders
    # ---------------------------------------------------------------------------

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:  # noqa: N802
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is not None and mime.hasUrls():
            urls = mime.urls()
            # Accept if any dropped item is a directory or a PDF file
            if any(
                u.isLocalFile()
                and (
                    u.toLocalFile().lower().endswith(".pdf")
                    or not u.toLocalFile().lower().endswith(".")
                )
                for u in urls
            ):
                a0.acceptProposedAction()
                return
        a0.ignore()

    def dropEvent(self, a0: QDropEvent | None) -> None:  # noqa: N802
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is not None and mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            if paths:
                self.paths_dropped.emit(paths)
                a0.acceptProposedAction()
                return
        a0.ignore()
