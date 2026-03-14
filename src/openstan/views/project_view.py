from pathlib import Path

import bank_statement_parser as bsp
from PyQt6.QtCore import QStandardPaths, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QWidget,
    QWizard,
    QWizardPage,
)

from openstan.components import (
    Qt,
    StanButton,
    StanErrorMessage,
    StanForm,
    StanHeaderLabel,
    StanInfoMessage,
    StanLabel,
    StanMutedLabel,
    StanRadioButton,
    StanWidget,
)
from openstan.paths import Paths

# Sentinel value used as the "Skip" source key in config selections
_SKIP_SENTINEL: str = "__skip__"


def _default_config_dir() -> Path:
    """Return the BSP bundled default config directory."""
    return bsp.ProjectPaths.resolve().config


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


class ProjectPageConfig(QWizardPage):
    """Second page of the New Project Wizard — bank config subfolder selection.

    Displays a grid of radio buttons.  Each row is a config subfolder name;
    each column is a source (BSP default or an existing registered project).
    A "Skip" column is always present so the user can exclude a subfolder.

    The presenter populates the page with source data before each ``exec()``
    via ``prepare_config_page()``.  Call ``get_config_selections()`` after the
    wizard finishes to obtain the mapping of subfolder names to their chosen
    source config directory (or ``None`` for "Skip").
    """

    def __init__(self) -> None:
        super().__init__()

        # Source data supplied by the presenter before each wizard run.
        # Maps source_key -> config/ Path; ordered (default first, then projects).
        self.__sources: dict[str, Path] = {}
        # All unique subfolder names (row labels), sorted
        self.__subfolders: list[str] = []
        # Ordered source keys (column labels, excluding "Skip")
        self.__source_keys: list[str] = []
        # Per-subfolder exclusive button groups
        self.__button_groups: dict[str, QButtonGroup] = {}
        # Scroll area containing the dynamic grid — rebuilt each initializePage()
        self.__scroll_area: QScrollArea | None = None

        self.setTitle("Configure Project")
        self.setSubTitle(
            "\nChoose which bank config subfolders to include in your new project.\n"
            "\nSelect 'Default' to use the standard BSP config, pick an existing project "
            "to copy its config instead, or choose 'Skip' to exclude a subfolder entirely."
        )

        # Outer layout holds the scroll area — the grid is rebuilt inside it.
        self.__outer_layout = QGridLayout()
        self.setLayout(self.__outer_layout)

    # ------------------------------------------------------------------
    # Public interface — called by the presenter
    # ------------------------------------------------------------------

    def prepare_config_page(self, sources: dict[str, Path]) -> None:
        """Supply source data from the presenter before the wizard is opened.

        *sources* is an ordered dict mapping a display key (e.g. ``"default"``
        or a project name) to the corresponding ``config/`` directory path.
        """
        self.__sources = sources
        self.__source_keys = list(sources.keys())
        all_subfolders: set[str] = set()
        for config_dir in sources.values():
            all_subfolders.update(_discover_config_subfolders(config_dir))
        self.__subfolders = sorted(all_subfolders)

    def get_config_selections(self) -> dict[str, Path | None]:
        """Return the user's current selections.

        Returns a dict mapping each subfolder name to:
        - ``Path``: the ``config/`` directory to copy the subfolder *from*
        - ``None``: the user chose "Skip" — exclude this subfolder
        """
        result: dict[str, Path | None] = {}
        for subfolder, group in self.__button_groups.items():
            checked = group.checkedButton()
            if checked is None:
                result[subfolder] = None
                continue
            key: str = checked.property("source_key")
            if key == _SKIP_SENTINEL:
                result[subfolder] = None
            else:
                result[subfolder] = self.__sources[key]
        return result

    def reset(self) -> None:
        """Tear down the dynamic grid (will be rebuilt on next initializePage)."""
        self.__tear_down_grid()

    # ------------------------------------------------------------------
    # QWizardPage overrides
    # ------------------------------------------------------------------

    def initializePage(self) -> None:
        """Rebuild the config grid each time this page is shown."""
        self.__build_grid()

    def cleanupPage(self) -> None:
        """Remove the scroll area when navigating back so it rebuilds fresh."""
        self.__tear_down_grid()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def __centred_radio(self, source_key: str, group: QButtonGroup) -> QWidget:
        """Return a centred container holding a single StanRadioButton.

        The radio button carries ``source_key`` as a Qt property and is added
        to *group*.
        """
        radio = StanRadioButton(text="")
        radio.setProperty("source_key", source_key)
        group.addButton(radio)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(radio)
        return container

    def __build_grid(self) -> None:
        """Build and insert the scroll area containing the config selection grid."""
        self.__tear_down_grid()
        self.__button_groups = {}

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(8)

        # --- Header row (row 0) ---
        # Col 0: blank; col 1: Skip; cols 2..N+1: sources (title-cased)
        grid.addWidget(StanLabel(""), 0, 0)
        col_labels = ["Skip"] + [k.title() for k in self.__source_keys]
        for col_idx, label_text in enumerate(col_labels):
            header = StanHeaderLabel(label_text)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(header, 0, col_idx + 1)

        # --- Data rows ---
        for row_idx, subfolder in enumerate(self.__subfolders, start=1):
            grid.addWidget(StanLabel(subfolder), row_idx, 0)

            group = QButtonGroup(self)
            group.setExclusive(True)
            self.__button_groups[subfolder] = group

            # Skip radio — column 1, always present
            skip_container = self.__centred_radio(_SKIP_SENTINEL, group)
            grid.addWidget(skip_container, row_idx, 1)
            # Hold a reference to the skip button for default-selection logic below
            skip_radio = group.buttons()[-1]

            default_radio = None
            for col_idx, source_key in enumerate(self.__source_keys):
                if (self.__sources[source_key] / subfolder).is_dir():
                    container = self.__centred_radio(source_key, group)
                    grid.addWidget(container, row_idx, col_idx + 2)
                    if source_key == "default":
                        default_radio = group.buttons()[-1]
                else:
                    # Subfolder absent in this source — show a muted dash
                    dash = StanMutedLabel("—")
                    dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    grid.addWidget(dash, row_idx, col_idx + 2)

            # Default selection: "Default" radio if the subfolder exists there,
            # otherwise "Skip" (subfolder only appears in other projects)
            if default_radio is not None:
                default_radio.setChecked(True)
            else:
                skip_radio.setChecked(True)

        scroll = QScrollArea()
        scroll.setWidget(grid_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.__scroll_area = scroll
        self.__outer_layout.addWidget(scroll, 0, 0)

    def __tear_down_grid(self) -> None:
        """Remove the scroll area and its children from the layout."""
        if self.__scroll_area is not None:
            self.__outer_layout.removeWidget(self.__scroll_area)
            self.__scroll_area.deleteLater()
            self.__scroll_area = None
        self.__button_groups = {}


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

        # Config selection page — new project wizard only
        self.page_config: ProjectPageConfig | None = None
        if mode == "new":
            self.page_config = ProjectPageConfig()
            self.addPage(self.page_config)

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
        if self.page_config is not None:
            self.page_config.reset()

    def accept(self) -> None:
        if self.project_created is False:
            self.new_project_required.emit()
        else:
            self.reset()
            self.restart()
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
        self.summary_label = StanLabel("")
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
        layout.addWidget(
            self.summary_label,
            1,
            0,
            1,
            6,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        self.setMaximumHeight(75)
