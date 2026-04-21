from pathlib import Path

import bank_statement_parser as bsp
from PyQt6.QtCore import QStandardPaths, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
)

from openstan.components import (
    Qt,
    StanButton,
    StanComboBox,
    StanErrorMessage,
    StanForm,
    StanInfoMessage,
    StanLabel,
    StanLineEdit,
    StanWidget,
    StanWizard,
    StanWizardPage,
)

# Sentinel value used as the "Skip" source key in config selections
_SKIP_SENTINEL: str = "__skip__"


def _default_config_dir() -> Path:
    """Return the BSP bundled default import config directory (``config/import/``)."""
    return bsp.ProjectPaths.resolve().config_import


def _discover_config_subfolders(config_dir: Path) -> list[str]:
    """Return sorted list of immediate subdirectory names inside *config_dir*.

    Returns an empty list if *config_dir* does not exist.
    """
    if not config_dir.is_dir():
        return []
    return sorted(p.name for p in config_dir.iterdir() if p.is_dir())


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


class ProjectPageBasic(StanWizardPage):
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
                "\n"
                "\nSelect a folder location where project files will be stored."
                "\nYour data export, configuration files and logs will be stored here."
                "\nA sub-folder named after your project will be created inside the selected folder."
            )

        layout = StanForm()
        self.id_row = StanLineEdit()
        self.id_row.setDisabled(True)
        self.id_row.setText(self.newProjectID)
        self.id_row.setFixedWidth(300)
        layout.addRow("Project ID:", self.id_row)

        self.name_row = StanLineEdit()
        self.name_row.setFixedWidth(300)
        if mode == "existing":
            self.name_row.setDisabled(True)
            self.name_row.setPlaceholderText("Populated after folder selection")
        layout.addRow("Project Name:", self.name_row)

        if mode == "existing":
            self.location_button = StanButton("Select Existing Project Folder")
        else:
            self.location_button = StanButton("Select Project Folder Location")
        self.location_button.set_themed_icon("folder_add.svg")
        self.location_label = StanLineEdit()
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


class ProjectWizard(StanWizard):
    new_project_required: pyqtSignal = pyqtSignal()

    def __init__(self, mode: str = "new", parent=None) -> None:
        super().__init__(parent)
        self.mode: str = mode

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
        # Leave the project folder path as-is between runs
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
            self.restart()
            super().accept()


class ProjectView(StanWidget):
    header = "##### Project Selection"

    def __init__(self, parent=None) -> None:
        super().__init__()
        self.wizard = ProjectWizard(mode="new", parent=parent)
        self.wizard_existing = ProjectWizard(mode="existing", parent=parent)
        self.label = StanLabel("Select an existing project:")
        self.label.setMaximumWidth(180)
        self.selection = StanComboBox()  # model details set in ProjectPresenter
        self.selection.setMaximumWidth(250)
        self.selection.setAccessibleName("Select existing project")
        self.selection.setToolTip("Select an existing project to open")
        self.label2 = StanLabel("or")
        self.label2.setMaximumWidth(60)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.button_new = StanButton("Create New Project")
        self.button_new.set_themed_icon("project.svg")
        self.button_new.setMinimumWidth(180)
        self.button_new.setToolTip("Open the wizard to create a new project")
        self.button_new.setAccessibleName("Create new project")
        self.label3 = StanLabel("or")
        self.button_existing = StanButton("Add Existing Project")
        self.button_existing.set_themed_icon("folder_add.svg")
        self.button_existing.setMinimumWidth(180)
        self.button_existing.setToolTip("Add an existing project folder to openstan")
        self.button_existing.setAccessibleName("Add existing project")
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
        self.setMaximumHeight(55)


# ---------------------------------------------------------------------------
# Navigation bar
# ---------------------------------------------------------------------------


class ProjectNavView(StanWidget):
    """Full-width horizontal action bar with checkable nav buttons.

    Button visibility is controlled externally by the presenter:
    - ``button_import`` is always visible.
    - ``button_info``, ``button_export``, ``button_reports`` are shown only
      when the current project has summary data.

    The active panel is indicated by the checked state of the corresponding
    button.  Buttons are mutually exclusive via a ``QButtonGroup``.
    """

    def __init__(self) -> None:
        super().__init__()

        self.button_info = self.__make_button(
            "Project Info",
            "project.svg",
            "View project summary, account list and gap report (Alt+P)",
            QKeySequence("Alt+P"),
        )
        self.button_import = self.__make_button(
            "Import Statements",
            "file_add.svg",
            "Add and import bank statement PDF files (Alt+I)",
            QKeySequence("Alt+I"),
        )
        self.button_export = self.__make_button(
            "Export Data",
            "export.svg",
            "Export transactions to Excel, CSV or JSON (Alt+E)",
            QKeySequence("Alt+E"),
        )
        self.button_reports = self.__make_button(
            "Run Reports",
            "run.svg",
            "Build and preview custom transaction reports (Alt+R)",
            QKeySequence("Alt+R"),
        )

        # Mutually exclusive checked state
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self.button_info)
        self._group.addButton(self.button_import)
        self._group.addButton(self.button_export)
        self._group.addButton(self.button_reports)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.addWidget(self.button_info)
        layout.addWidget(self.button_import)
        layout.addWidget(self.button_export)
        layout.addWidget(self.button_reports)
        self.setLayout(layout)
        self.setMaximumHeight(44)

    # ------------------------------------------------------------------
    # Public interface — called by the presenter
    # ------------------------------------------------------------------

    def clear_checks(self) -> None:
        """Uncheck all nav buttons (e.g. when switching project)."""
        for btn in self._group.buttons():
            btn.setChecked(False)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def __make_button(
        text: str,
        icon_filename: str,
        tooltip: str = "",
        shortcut: QKeySequence | None = None,
    ) -> StanButton:
        btn = StanButton(text)
        btn.set_themed_icon(icon_filename)
        btn.setCheckable(True)
        btn.setMinimumWidth(0)  # override StanButton default 200px minimum
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if tooltip:
            btn.setToolTip(tooltip)
        if shortcut is not None:
            btn.setShortcut(shortcut)
        return btn
