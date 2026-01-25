from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QLineEdit, QWizard, QWizardPage

from openstan.gui.components import StanButton, StanErrorMessage, StanForm, StanInfoMessage, StanLabel, StanWidget
from openstan.gui.paths import Paths


class FolderSelectionDialog(QFileDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Project Folder Location")
        self.setDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
        self.setFileMode(QFileDialog.FileMode.Directory)


class ProjectPageBasic(QWizardPage):
    def __init__(self):
        super().__init__()
        self.newProjectID = "AUTO_GENERATED_ID"  # Will be set by project_presenter
        self.folder_path = None  # Will be set when user selects folder
        self.folder_selection_dialog = FolderSelectionDialog()
        self.setTitle("Project Details")
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
        layout.addRow("Project Name:", self.name_row)
        self.location_button = StanButton("Select Project Folder Location")
        self.location_button.setIcon(QIcon(Paths.icon("folder_add.svg")))
        self.location_label = QLineEdit()
        self.location_label.setReadOnly(True)
        self.location_label.setFixedWidth(300)
        self.location_label.hide()
        layout.addRow("Location:", self.location_button)
        layout.addRow("", self.location_label)
        self.setLayout(layout)

        # Field registrations
        self.registerField("projectName*", self.name_row)
        self.registerField("projectLocation*", self.location_label)


class ProjectWizard(QWizard):
    new_project_required = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("New Project Wizard")
        self.setAutoFillBackground(True)

        # Add pages and logic for the wizard here
        self.page_basic = ProjectPageBasic()
        self.addPage(self.page_basic)
        self.full_project_path = None  # Will be set upon folder selection
        self.project_created = False

        self.success_dialog = StanInfoMessage(parent=self)
        self.failure_dialog = StanErrorMessage(parent=self)

        self.success_dialog.setWindowTitle("Success")
        self.failure_dialog.setWindowTitle("Failure")

        self.checks_passed = False

    def reset(self):
        self.page_basic.name_row.clear()
        # self.page_basic.location_label.clear() --- IGNORE --- leave the project folder path as is
        # self.page_basic.location_label.hide() --- IGNORE --- leave the project folder path as is
        self.page_basic.location_button.setDisabled(True)
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

    def __init__(self):
        super().__init__()
        self.wizard = ProjectWizard()
        # self.sessionID = stan.sessionID
        self.label = StanLabel("Select an existing project:")
        self.label.setMaximumWidth(180)
        self.selection = QComboBox()  # model details set in ProjectPresenter
        self.selection.setMaximumWidth(250)
        self.label2 = StanLabel("... or create a new one:")
        self.label2.setMaximumWidth(180)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.button_new = StanButton("New Project")
        self.button_new.setIcon(QIcon(Paths.icon("project.svg")))
        self.button_new.setMinimumWidth(180)
        layout = QGridLayout()
        layout.addWidget(self.label, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.selection, 0, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.label2, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.button_new, 0, 3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        self.setMaximumHeight(50)

    def reset_wizard(self):
        self.wizard = ProjectWizard()
        # # signals
        # self.selection.currentIndexChanged.connect(lambda: project_controller.project_selection_changed(project=self, stan=stan))
