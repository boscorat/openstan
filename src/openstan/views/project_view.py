from pathlib import Path

from PyQt6.QtCore import QStandardPaths, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QWizard,
    QWizardPage,
)

from openstan.components import (
    Qt,
    StanButton,
    StanErrorMessage,
    StanForm,
    StanInfoMessage,
    StanLabel,
    StanWidget,
)
from openstan.paths import Paths


class FolderSelectionDialog(QFileDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Project Folder Location")
        self.setDirectory(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            )
        )
        self.setFileMode(QFileDialog.FileMode.Directory)


class ProjectPageBasic(QWizardPage):
    def __init__(self, mode: str = "new") -> None:
        super().__init__()
        self.mode: str = mode
        self.newProjectID = "AUTO_GENERATED_ID"  # Will be set by project_presenter
        self.folder_path: Path | None = None  # Will be set when user selects folder
        self.folder_selection_dialog = FolderSelectionDialog()
        self.setTitle("Project Details")

        if mode == "existing":
            self.folder_selection_dialog.setWindowTitle(
                "Select Existing Project Folder"
            )
            self.setSubTitle(
                "\nThe project ID has been auto-generated."
                "\n"
                "\nSelect the existing project folder."
                "\nThe project name will be pre-populated from the folder name — you can change it if required."
            )
        else:
            self.setSubTitle(
                "\nThe project ID has been auto-generated."
                "\n"
                "\nChoose a name for your project e.g. "
                "Jason's Banking"
                ""
                "\n"
                "\nSelect a folder location where project files will be stored."
                "\nYour data export, configuration files and logs will be stored here."
                "\nA sub-folder named after your project will be created inside the selected folder."
            )

        layout = StanForm()
        self.id_row = QLineEdit()
        self.id_row.setDisabled(True)
        self.id_row.setText(self.newProjectID)
        self.id_row.setFixedWidth(300)
        layout.addRow("Project ID:", self.id_row)

        self.name_row = QLineEdit()
        self.name_row.setFixedWidth(300)
        if mode == "existing":
            self.name_row.setDisabled(True)
            self.name_row.setPlaceholderText("Populated after folder selection")
        layout.addRow("Project Name:", self.name_row)

        if mode == "existing":
            self.location_button = StanButton("Select Existing Project Folder")
        else:
            self.location_button = StanButton("Select Project Folder Location")
        self.location_button.setIcon(QIcon(Paths.icon("folder_add.svg")))
        self.location_label = QLineEdit()
        self.location_label.setReadOnly(True)
        self.location_label.setFixedWidth(300)
        self.location_label.hide()
        layout.addRow("Location:", self.location_button)
        layout.addRow("", self.location_label)
        self.setLayout(layout)

        # Field registrations — projectName is always required; projectLocation only for new projects
        # (existing mode derives location from the folder selection itself)
        self.registerField("projectName*", self.name_row)
        if mode == "new":
            self.registerField("projectLocation*", self.location_label)


class ProjectWizard(QWizard):
    new_project_required: pyqtSignal = pyqtSignal()

    def __init__(self, mode: str = "new") -> None:
        super().__init__()
        self.mode: str = mode
        self.setAutoFillBackground(True)

        if mode == "existing":
            self.setWindowTitle("Add Existing Project")
        else:
            self.setWindowTitle("New Project Wizard")

        self.page_basic = ProjectPageBasic(mode=mode)
        self.addPage(self.page_basic)
        self.full_project_path: Path | None = None  # Will be set upon folder selection
        self.project_created = False

        self.success_dialog = StanInfoMessage(parent=self)
        self.failure_dialog = StanErrorMessage(parent=self)

        self.success_dialog.setWindowTitle("Success")
        self.failure_dialog.setWindowTitle("Failure")

        self.checks_passed = False

    def reset(self) -> None:
        self.page_basic.name_row.clear()
        # leave the project folder path as-is between runs
        if self.mode == "new":
            self.page_basic.location_button.setDisabled(True)
        if self.mode == "existing":
            self.page_basic.name_row.setDisabled(True)
            self.page_basic.name_row.setPlaceholderText(
                "Populated after folder selection"
            )
        self.page_basic.newProjectID = "AUTO_GENERATED_ID"
        self.page_basic.id_row.setText(self.page_basic.newProjectID)
        self.full_project_path = None
        self.project_created = False

    def accept(self) -> None:
        if self.project_created is False:
            self.new_project_required.emit()
        else:
            self.reset()
            super().accept()


class ProjectView(StanWidget):
    header = "##### Project Selection"

    def __init__(self) -> None:
        super().__init__()
        self.wizard = ProjectWizard(mode="new")
        self.wizard_existing = ProjectWizard(mode="existing")
        self.label = StanLabel("Select an existing project:")
        self.label.setMaximumWidth(180)
        self.selection = QComboBox()  # model details set in ProjectPresenter
        self.selection.setMaximumWidth(250)
        self.label2 = StanLabel("or")
        self.label2.setMaximumWidth(60)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.button_new = StanButton("Create New Project")
        self.button_new.setIcon(QIcon(Paths.icon("project.svg")))
        self.button_new.setMinimumWidth(180)
        self.label3 = StanLabel("or")
        self.button_existing = StanButton("Add Existing Project")
        self.button_existing.setIcon(QIcon(Paths.icon("folder_add.svg")))
        self.button_existing.setMinimumWidth(180)
        layout = QGridLayout()
        layout.addWidget(
            self.label, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(
            self.selection,
            0,
            1,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.label2,
            0,
            2,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.button_new,
            0,
            3,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.label3,
            0,
            4,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.button_existing,
            0,
            5,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        self.setMaximumHeight(50)

    def reset_wizard(self) -> None:
        self.wizard = ProjectWizard(mode="new")
        self.wizard_existing = ProjectWizard(mode="existing")
