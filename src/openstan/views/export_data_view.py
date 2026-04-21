"""export_data_view.py — Export Data panel view.

The panel is split into two tabs via a ``QTabWidget``:

* **Standard Exports** — the original parameter panel (type, batch, file
  naming, output folder) and the three format buttons (Excel, CSV, JSON).
  All wiring for this tab lives in ``ExportDataPresenter``.

* **Advanced Exports** — the ``AdvancedExportView`` widget, which presents
  ``export_spec`` parameters and a scrollable list of spec buttons.
  All wiring for this tab lives in ``AdvancedExportPresenter``.

Both presenters access their respective sub-widget trees through the
public attributes exposed by this class.
"""

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
)

from openstan.components import (
    Qt,
    StanButton,
    StanFrame,
    StanHelpIcon,
    StanLabel,
    StanLineEdit,
    StanMutedLabel,
    StanProgressBar,
    StanRadioButton,
    StanTabWidget,
    StanWidget,
)
from openstan.paths import Paths
from openstan.views.advanced_export_view import AdvancedExportView

# ---------------------------------------------------------------------------
# Help text — sourced from BSP export_csv docstring (reports_db.py)
# ---------------------------------------------------------------------------

_HELP_TYPE = (
    'Export preset \u2014 "single" produces a flat transactions table; '
    '"multi" produces separate star-schema tables (statement, account, '
    "calendar, transactions, balances, gaps) for loading into a database."
)

_HELP_BATCH = (
    "Optional batch identifier to filter report data to a single batch. "
    '"All" exports every row (batch_id=None). '
    '"Latest" filters to the most recently committed batch.'
)

_HELP_TIMESTAMP = (
    "When enabled, a human-readable timestamp (yyyymmddHHMMSS) is appended "
    "to the filename (single) or used to create a timestamped sub-folder "
    "(multi). When disabled, existing files are overwritten."
)

_HELP_FOLDER = (
    "Directory to write exported files into. When left as default the "
    "project\u2019s export/<format>/ directory is used and created "
    "automatically if absent."
)


def _make_option_group(
    label_text: str,
    help_text: str,
    *radio_buttons: "StanRadioButton",
) -> tuple["StanWidget", "QButtonGroup"]:
    """Build a labelled radio-button group container.

    Returns the container widget and the ``QButtonGroup`` so the caller can
    store the group reference for later ``isChecked()`` queries.
    """
    group = QButtonGroup()
    for btn in radio_buttons:
        group.addButton(btn)

    label_row = QHBoxLayout()
    label_row.setContentsMargins(0, 0, 0, 0)
    label_row.addWidget(StanLabel(label_text))
    label_row.addWidget(StanHelpIcon(help_text))
    label_row.addStretch()

    radio_row = QHBoxLayout()
    radio_row.setContentsMargins(0, 0, 0, 0)
    for btn in radio_buttons:
        radio_row.addWidget(btn)
    radio_row.addStretch()

    box = QVBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(2)
    box.addLayout(label_row)
    box.addLayout(radio_row)

    container = StanWidget()
    container.setLayout(box)
    return container, group


class ExportDataView(StanWidget):
    """Export Data panel.

    Contains a ``QTabWidget`` with two tabs:

    * ``TAB_STANDARD`` (index 0) — the original radio-button parameter
      panel and format export buttons.
    * ``TAB_ADVANCED`` (index 1) — the ``AdvancedExportView`` for
      spec-based exports.

    Standard-tab widgets are exposed directly on this class so that
    ``ExportDataPresenter`` can reference them without changes.  The
    advanced tab's widget tree is accessible via ``self.advanced``.
    """

    header: str = "##### Export Data"

    # Tab index constants — kept here so presenters can reference them
    # without hard-coding magic numbers.
    TAB_STANDARD = 0
    TAB_ADVANCED = 1

    def __init__(self) -> None:
        super().__init__()

        # ── Standard Exports tab ──────────────────────────────────────────
        standard_tab = StanWidget()

        # Description
        description = StanMutedLabel(
            "Export project transactions to your preferred format. "
            "Configure export options below, then click an export button."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # ── Parameter panel ───────────────────────────────────────────────
        param_frame = StanFrame()
        param_grid = QGridLayout()
        param_grid.setSpacing(10)
        param_grid.setContentsMargins(12, 12, 12, 12)

        # Row 0 has three parameter groups side-by-side.
        # Row 1 spans the full width for the folder selector.

        # -- Row 0, Col 0-1: Type ----------------------------------------
        self.radio_type_single = StanRadioButton("Single")
        self.radio_type_multi = StanRadioButton("Multi")
        self.radio_type_single.setChecked(True)
        self.radio_type_single.setAccessibleName("Export type: Single flat table")
        self.radio_type_multi.setAccessibleName("Export type: Multi star-schema tables")
        type_container, self.group_type = _make_option_group(
            "**Type**", _HELP_TYPE, self.radio_type_single, self.radio_type_multi
        )

        # -- Row 0, Col 2-3: Batch ----------------------------------------
        self.radio_batch_all = StanRadioButton("All")
        self.radio_batch_latest = StanRadioButton("Latest")
        self.radio_batch_all.setChecked(True)
        self.radio_batch_all.setAccessibleName("Batch filter: All batches")
        self.radio_batch_latest.setAccessibleName("Batch filter: Latest batch only")
        batch_container, self.group_batch = _make_option_group(
            "**Batch**", _HELP_BATCH, self.radio_batch_all, self.radio_batch_latest
        )

        # -- Row 0, Col 4-5: File naming ----------------------------------
        self.radio_ts_on = StanRadioButton("Timestamp files")
        self.radio_ts_off = StanRadioButton("Overwrite")
        self.radio_ts_on.setChecked(True)
        self.radio_ts_on.setAccessibleName("File naming: Append timestamp")
        self.radio_ts_off.setAccessibleName("File naming: Overwrite existing files")
        ts_container, self.group_timestamp = _make_option_group(
            "**File naming**", _HELP_TIMESTAMP, self.radio_ts_on, self.radio_ts_off
        )

        # Assemble Row 0 — three groups side-by-side
        param_grid.addWidget(type_container, 0, 0)
        param_grid.addWidget(batch_container, 0, 1)
        param_grid.addWidget(ts_container, 0, 2)

        # Even column stretch so they share space equally
        param_grid.setColumnStretch(0, 1)
        param_grid.setColumnStretch(1, 1)
        param_grid.setColumnStretch(2, 1)

        # -- Row 1: Export folder (spans full width) ----------------------
        folder_label_row = QHBoxLayout()
        folder_label_row.setContentsMargins(0, 0, 0, 0)
        folder_label_row.addWidget(StanLabel("**Export folder**"))
        folder_label_row.addWidget(StanHelpIcon(_HELP_FOLDER))
        folder_label_row.addStretch()

        self.line_edit_folder = StanLineEdit()
        self.line_edit_folder.setReadOnly(True)
        self.line_edit_folder.setPlaceholderText("(project default)")
        self.line_edit_folder.setAccessibleName("Export folder path")

        self.button_browse_folder = StanButton("Browse", min_width=0)
        self.button_browse_folder.setToolTip("Choose a custom export output folder")
        self.button_reset_folder = StanButton("Reset", min_width=0)
        self.button_reset_folder.setToolTip(
            "Reset export folder to the project default"
        )

        folder_controls = QHBoxLayout()
        folder_controls.setContentsMargins(0, 0, 0, 0)
        folder_controls.addWidget(self.line_edit_folder, stretch=1)
        folder_controls.addWidget(self.button_browse_folder)
        folder_controls.addWidget(self.button_reset_folder)

        folder_box = QVBoxLayout()
        folder_box.setContentsMargins(0, 0, 0, 0)
        folder_box.setSpacing(2)
        folder_box.addLayout(folder_label_row)
        folder_box.addLayout(folder_controls)

        folder_container = StanWidget()
        folder_container.setLayout(folder_box)
        param_grid.addWidget(folder_container, 1, 0, 1, 3)  # span all 3 cols

        param_frame.setLayout(param_grid)

        # ── Export buttons ─────────────────────────────────────────────────
        self.button_excel = StanButton("Export Excel")
        self.button_excel.setIcon(QIcon(Paths.themed_icon("excel.svg")))
        self.button_excel.setToolTip("Export transactions to an Excel (.xlsx) file")
        self.button_csv = StanButton("Export CSV")
        self.button_csv.setIcon(QIcon(Paths.themed_icon("csv.svg")))
        self.button_csv.setToolTip("Export transactions to a CSV file")
        self.button_json = StanButton("Export JSON")
        self.button_json.setIcon(QIcon(Paths.themed_icon("json.svg")))
        self.button_json.setToolTip("Export transactions to a JSON file")

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.button_excel)
        button_row.addWidget(self.button_csv)
        button_row.addWidget(self.button_json)

        # ── Progress / status ──────────────────────────────────────────────
        self.progress_bar = StanProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate (marquee)
        self.progress_bar.setVisible(False)

        self.label_status = StanLabel("")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # ── Standard tab layout ────────────────────────────────────────────
        standard_layout = QVBoxLayout()
        standard_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        standard_layout.setSpacing(12)
        standard_layout.setContentsMargins(0, 8, 0, 0)

        standard_layout.addWidget(description)
        standard_layout.addSpacing(4)
        standard_layout.addWidget(param_frame)
        standard_layout.addSpacing(4)
        standard_layout.addLayout(button_row)
        standard_layout.addSpacing(4)
        standard_layout.addWidget(self.progress_bar)
        standard_layout.addWidget(self.label_status)

        standard_tab.setLayout(standard_layout)

        # ── Advanced Exports tab ──────────────────────────────────────────
        self.advanced = AdvancedExportView()

        # ── Tab widget ─────────────────────────────────────────────────────
        self.tabs = StanTabWidget()
        self.tabs.addTab(standard_tab, "Standard Exports")
        self.tabs.addTab(self.advanced, "Advanced Exports")

        # ── Placeholder page (page 0) ──────────────────────────────────────
        placeholder_page = StanWidget()
        ph_layout = QVBoxLayout()
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_icon = StanLabel()
        ph_icon.setPixmap(QIcon(Paths.themed_icon("export.svg")).pixmap(64, 64))
        ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text = StanMutedLabel(
            "No data yet — import and commit some statements before exporting."
        )
        ph_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text.setWordWrap(True)
        ph_layout.addWidget(ph_icon)
        ph_layout.addSpacing(8)
        ph_layout.addWidget(ph_text)
        placeholder_page.setLayout(ph_layout)

        # Content page (page 1) wraps the tab widget
        content_page = StanWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.tabs)
        content_page.setLayout(content_layout)

        # ── Stacked widget ─────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(placeholder_page)  # page 0
        self._stack.addWidget(content_page)  # page 1
        self._stack.setCurrentIndex(0)

        # ── Outer layout ───────────────────────────────────────────────────
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self._stack)

        self.setLayout(outer_layout)

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def show_placeholder(self, show: bool) -> None:
        """Switch between placeholder (page 0) and real content (page 1)."""
        self._stack.setCurrentIndex(0 if show else 1)

    def setup_tab_order(self) -> None:
        """Establish an explicit, logical Tab key traversal order for the standard tab."""
        # Parameter group: Type → Batch → File naming → folder browse → reset
        self.setTabOrder(self.radio_type_single, self.radio_type_multi)
        self.setTabOrder(self.radio_type_multi, self.radio_batch_all)
        self.setTabOrder(self.radio_batch_all, self.radio_batch_latest)
        self.setTabOrder(self.radio_batch_latest, self.radio_ts_on)
        self.setTabOrder(self.radio_ts_on, self.radio_ts_off)
        self.setTabOrder(self.radio_ts_off, self.button_browse_folder)
        self.setTabOrder(self.button_browse_folder, self.button_reset_folder)
        # Export action buttons
        self.setTabOrder(self.button_reset_folder, self.button_excel)
        self.setTabOrder(self.button_excel, self.button_csv)
        self.setTabOrder(self.button_csv, self.button_json)
