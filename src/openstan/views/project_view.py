"""project_view.py — Project-related view classes.

Contains the project selection panel, navigation bar, welcome view,
project information panel, and gap detail dialog.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import bank_statement_parser as bsp
import polars as pl
from PySide6.QtCore import QStandardPaths, Signal
from PySide6.QtGui import QKeySequence, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
)

from openstan.components import (
    Qt,
    StanButton,
    StanComboBox,
    StanDialog,
    StanErrorMessage,
    StanForm,
    StanHeaderLabel,
    StanInfoMessage,
    StanLabel,
    StanLineEdit,
    StanMutedLabel,
    StanPolarsModel,
    StanTableView,
    StanThemedPixmapLabel,
    StanTreeView,
    StanWidget,
    StanWizard,
    StanWizardPage,
)

if TYPE_CHECKING:
    from openstan.presenters.project_presenter import ProjectInfo

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
            self.location_button.setToolTip(
                "Select the root folder of an existing openstan project"
            )
        else:
            self.location_button = StanButton("Select Project Folder Location")
            self.location_button.setToolTip(
                "Select the parent folder where the new project folder will be created"
            )
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
    new_project_required: Signal = Signal()

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
        self.selection.setPlaceholderText("Select a project...")
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
            "Shows transaction counts, statement counts, account details, "
            "and any detected gaps between imported statements for the current project.",
        )
        self.button_import = self.__make_button(
            "Import Statements",
            "file_add.svg",
            "Add and import bank statement PDF files (Alt+I)",
            QKeySequence("Alt+I"),
            "Add folders of PDF bank statements to the import queue, then run the import to parse them into transactions.",
        )
        self.button_export = self.__make_button(
            "Export Data",
            "export.svg",
            "Export transactions to Excel, CSV or JSON (Alt+E)",
            QKeySequence("Alt+E"),
            "Export the project's transaction data to Excel, CSV, or JSON. Use the Advanced tab for filtered or custom-spec exports.",
        )
        self.button_reports = self.__make_button(
            "Run Reports",
            "run.svg",
            "Build and preview custom transaction reports (Alt+R)",
            QKeySequence("Alt+R"),
            "Build and preview custom summary reports with grouping, aggregation, date filters, and live preview.",
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
        whats_this: str = "",
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
        if whats_this:
            btn.setWhatsThis(whats_this)
        return btn


class ProjectWelcomeView(StanWidget):
    """Shown in the content stack when no project is open.

    Contains a ``Select Project`` button (visible only when projects exist),
    a ``Create New Project`` button, and an ``Import Project`` button.
    The ``clicked`` signals are wired by ``ProjectWelcomePresenter`` to the
    project presenter's wizard slots.
    """

    header: str = "Welcome"

    def __init__(self) -> None:
        super().__init__()

        icon = StanThemedPixmapLabel("project.svg", size=96)
        icon.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        heading = StanLabel("## Welcome to openstan")
        heading.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        subheading = StanLabel(
            "Select an existing project, create a new one, or import a project folder."
        )
        subheading.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self.button_select = StanButton("Select Project", min_width=200)
        self.button_select.set_themed_icon("folder_open.svg")
        self.button_select.setToolTip("Select an existing project to open")
        self.button_select.setAccessibleName("Select project")
        self.button_select.hide()

        self.button_new = StanButton("Create New Project", min_width=200)
        self.button_new.set_themed_icon("project.svg")
        self.button_new.setToolTip("Open the wizard to create a new project")
        self.button_new.setAccessibleName("Create new project")

        self.button_existing = StanButton("Add Existing Project", min_width=200)
        self.button_existing.set_themed_icon("folder_add.svg")
        self.button_existing.setToolTip("Add an existing project folder to openstan")
        self.button_existing.setAccessibleName("Add existing project")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch()
        btn_row.addWidget(self.button_select)
        btn_row.addWidget(self.button_new)
        btn_row.addWidget(self.button_existing)
        btn_row.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(heading)
        layout.addWidget(subheading)
        layout.addSpacing(24)
        layout.addLayout(btn_row)
        layout.addStretch()

        self.setLayout(layout)

    def set_select_button_visible(self, visible: bool) -> None:
        """Show/hide the Select Project button (visible when projects exist)."""
        self.button_select.setVisible(visible)


# ---------------------------------------------------------------------------
# Gap detail dialog
# ---------------------------------------------------------------------------


class GapDetailDialog(StanDialog):
    """Modal dialog showing gap-report rows as a tree grouped by account.

    Top-level nodes: one per unique (account_holder, account_type, account_number).
    Child nodes: one per GAP row — "Missing statement between <prev> and <current>".
    The tree is fully expanded on load.
    """

    def __init__(self, parent: StanWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Gap Report — Missing Statements")
        self.setMinimumWidth(640)
        self.setMinimumHeight(320)

        self._tree = StanTreeView()
        self._tree.setMinimumHeight(250)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(StanLabel("##### Detected gaps between imported statements"))
        layout.addWidget(self._tree)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def load(self, gap_rows: pl.DataFrame) -> None:
        """Populate the tree from *gap_rows*.

        Expected columns: account_holder, account_type, account_number,
        prev_statement_date, statement_date.
        """
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Gap"])

        # Group rows by (account_holder, account_type, account_number) in the
        # order they first appear — preserves natural sort from the query.
        seen: dict[tuple[str, str, str], QStandardItem] = {}
        for row in gap_rows.iter_rows(named=True):
            key = (
                row["account_holder"],
                row["account_type"],
                row["account_number"],
            )
            if key not in seen:
                holder, acc_type, acc_num = key
                node_label = f"{holder} / {acc_type} — {acc_num}"
                parent_item = QStandardItem(node_label)
                parent_item.setEditable(False)
                model.appendRow(parent_item)
                seen[key] = parent_item

            prev = row["prev_statement_date"] or "?"
            curr = row["statement_date"] or "?"
            child_label = f"Missing statement between {prev} and {curr}"
            child_item = QStandardItem(child_label)
            child_item.setEditable(False)
            seen[key].appendRow(child_item)

        self._tree.setModel(model)
        self._tree.expandAll()


# ---------------------------------------------------------------------------
# Project information panel
# ---------------------------------------------------------------------------


class ProjectInfoView(StanWidget):
    """Project Information panel.

    Layout (top-to-bottom):
    1. Headline summary strip — tx / stmt / account counts and date range
    2. Per-account ``StanTableView``
    3. Gap indicator button (hidden when gap_count == 0)

    The header label is supplied externally by ``ContentFrameView`` in
    ``main.py`` — consistent with all other panel views.

    The single public entry point is :meth:`update`.
    """

    header: str = "##### Project Information"

    # Emitted when the user clicks the gap indicator button.
    gap_clicked: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()

        # ── Placeholder page (page 0) ─────────────────────────────────────────
        placeholder_page = StanWidget()
        ph_layout = QVBoxLayout()
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_icon = StanThemedPixmapLabel("project.svg", size=64)
        ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text = StanMutedLabel(
            "No data yet — import and commit some statements to see your project summary."
        )
        ph_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text.setWordWrap(True)
        ph_layout.addWidget(ph_icon)
        ph_layout.addSpacing(8)
        ph_layout.addWidget(ph_text)
        placeholder_page.setLayout(ph_layout)

        # ── Content page (page 1) ─────────────────────────────────────────────
        content_page = StanWidget()

        # ── Summary strip ─────────────────────────────────────────────────────
        self._lbl_tx = StanLabel("")
        self._lbl_stmt = StanLabel("")
        self._lbl_acc = StanLabel("")
        self._lbl_dates = StanLabel("")

        summary_row = QHBoxLayout()
        summary_row.setSpacing(24)
        summary_row.addWidget(self._lbl_tx)
        summary_row.addWidget(self._lbl_stmt)
        summary_row.addWidget(self._lbl_acc)
        summary_row.addWidget(self._lbl_dates)
        summary_row.addStretch()

        # ── Account table ─────────────────────────────────────────────────────
        self._acc_table_header = StanHeaderLabel("Accounts")
        self._acc_table_currency_note = StanMutedLabel(
            "Monetary values are in the currency recorded in each statement."
        )
        self._acc_table = StanTableView()
        self._acc_table.horizontalHeader().setSectionResizeMode(  # type: ignore[union-attr]
            self._acc_table.horizontalHeader().ResizeMode.ResizeToContents  # type: ignore[union-attr]
        )
        self._acc_table.horizontalHeader().setStretchLastSection(True)  # type: ignore[union-attr]

        # ── Gap indicator ─────────────────────────────────────────────────────
        self._gap_button = QPushButton()
        self._gap_button.setFlat(True)
        # Use the Link colour role so the warning text adapts to the active
        # theme (including high-contrast modes) rather than a hardcoded hex.
        self._gap_button.setStyleSheet(
            "QPushButton { color: palette(link); font-weight: bold; text-align: left; border: none; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._gap_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gap_button.setToolTip(
            "A gap means there is a missing statement between two consecutive imported statements "
            "for the same account.  Click to see which accounts and date ranges are affected."
        )
        self._gap_button.setAccessibleDescription(
            "One or more statement gaps detected. Click to review."
        )
        self._gap_button.clicked.connect(self.gap_clicked)
        self._gap_button.hide()

        # ── Gap detail dialog ─────────────────────────────────────────────────
        self._gap_dialog = GapDetailDialog(self)
        self.gap_clicked.connect(self._gap_dialog.exec)

        # ── Content page layout ───────────────────────────────────────────────
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.addLayout(summary_row)
        content_layout.addWidget(self._acc_table_header)
        content_layout.addWidget(self._acc_table_currency_note)
        content_layout.addWidget(self._acc_table)
        content_layout.addWidget(self._gap_button)
        content_layout.addStretch()
        content_page.setLayout(content_layout)

        # ── Stacked widget ────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(placeholder_page)  # page 0
        self._stack.addWidget(content_page)  # page 1
        self._stack.setCurrentIndex(0)

        # ── Outer layout ──────────────────────────────────────────────────────
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)
        self.setLayout(outer)

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def show_placeholder(self, show: bool) -> None:
        """Switch between placeholder (page 0) and real content (page 1)."""
        self._stack.setCurrentIndex(0 if show else 1)

    def update(self, info: "ProjectInfo | None") -> None:  # type: ignore[override]
        """Refresh the entire panel from *info*.

        Passing ``None`` clears all data (placeholder is controlled separately
        via :meth:`show_placeholder`).
        """
        if info is None:
            self._clear()
            return

        # Summary strip
        acc_word = "account" if info.acc_count == 1 else "accounts"
        self._lbl_tx.setText(f"**{info.tx_count:,}** transactions")
        self._lbl_stmt.setText(f"**{info.stmt_count:,}** statements")
        self._lbl_acc.setText(f"**{info.acc_count:,}** {acc_word}")
        if info.earliest_date and info.latest_date:
            self._lbl_dates.setText(f"{info.earliest_date} — {info.latest_date}")
        else:
            self._lbl_dates.setText("")

        # Account table
        model = StanPolarsModel(info.account_rows)
        self._acc_table.setModel(model)

        # Gap indicator
        if info.gap_count > 0:
            gap_word = "gap" if info.gap_count == 1 else "gaps"
            self._gap_button.setText(
                f"Warning: {info.gap_count} statement {gap_word} detected — click to review"
            )
            self._gap_dialog.load(info.gap_rows)
            self._gap_button.show()
        else:
            self._gap_button.hide()

        self._acc_table_header.show()
        self._acc_table_currency_note.show()
        self._acc_table.show()

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _clear(self) -> None:
        """Reset content to empty state."""
        self._lbl_tx.setText("")
        self._lbl_stmt.setText("")
        self._lbl_acc.setText("")
        self._lbl_dates.setText("")
        self._acc_table.setModel(None)
        self._gap_button.hide()
        self._acc_table_header.hide()
        self._acc_table_currency_note.hide()
        self._acc_table.hide()
