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
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
)

from openstan.components import (
    Qt,
    StanButton,
    StanFrame,
    StanHelpIcon,
    StanLabel,
    StanMutedLabel,
    StanProgressBar,
    StanRadioButton,
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

        self.group_type = QButtonGroup()
        self.group_type.addButton(self.radio_type_single)
        self.group_type.addButton(self.radio_type_multi)

        type_box = QVBoxLayout()
        type_box.setContentsMargins(0, 0, 0, 0)
        type_box.setSpacing(2)
        type_label_row = QHBoxLayout()
        type_label_row.setContentsMargins(0, 0, 0, 0)
        type_label_row.addWidget(StanLabel("**Type**"))
        type_label_row.addWidget(StanHelpIcon(_HELP_TYPE))
        type_label_row.addStretch()
        type_box.addLayout(type_label_row)
        type_radio_row = QHBoxLayout()
        type_radio_row.setContentsMargins(0, 0, 0, 0)
        type_radio_row.addWidget(self.radio_type_single)
        type_radio_row.addWidget(self.radio_type_multi)
        type_radio_row.addStretch()
        type_box.addLayout(type_radio_row)

        type_container = StanWidget()
        type_container.setLayout(type_box)

        # -- Row 0, Col 2-3: Batch ----------------------------------------
        self.radio_batch_all = StanRadioButton("All")
        self.radio_batch_latest = StanRadioButton("Latest")
        self.radio_batch_all.setChecked(True)

        self.group_batch = QButtonGroup()
        self.group_batch.addButton(self.radio_batch_all)
        self.group_batch.addButton(self.radio_batch_latest)

        batch_box = QVBoxLayout()
        batch_box.setContentsMargins(0, 0, 0, 0)
        batch_box.setSpacing(2)
        batch_label_row = QHBoxLayout()
        batch_label_row.setContentsMargins(0, 0, 0, 0)
        batch_label_row.addWidget(StanLabel("**Batch**"))
        batch_label_row.addWidget(StanHelpIcon(_HELP_BATCH))
        batch_label_row.addStretch()
        batch_box.addLayout(batch_label_row)
        batch_radio_row = QHBoxLayout()
        batch_radio_row.setContentsMargins(0, 0, 0, 0)
        batch_radio_row.addWidget(self.radio_batch_all)
        batch_radio_row.addWidget(self.radio_batch_latest)
        batch_radio_row.addStretch()
        batch_box.addLayout(batch_radio_row)

        batch_container = StanWidget()
        batch_container.setLayout(batch_box)

        # -- Row 0, Col 4-5: File naming ----------------------------------
        self.radio_ts_on = StanRadioButton("Timestamp files")
        self.radio_ts_off = StanRadioButton("Overwrite")
        self.radio_ts_on.setChecked(True)

        self.group_timestamp = QButtonGroup()
        self.group_timestamp.addButton(self.radio_ts_on)
        self.group_timestamp.addButton(self.radio_ts_off)

        ts_box = QVBoxLayout()
        ts_box.setContentsMargins(0, 0, 0, 0)
        ts_box.setSpacing(2)
        ts_label_row = QHBoxLayout()
        ts_label_row.setContentsMargins(0, 0, 0, 0)
        ts_label_row.addWidget(StanLabel("**File naming**"))
        ts_label_row.addWidget(StanHelpIcon(_HELP_TIMESTAMP))
        ts_label_row.addStretch()
        ts_box.addLayout(ts_label_row)
        ts_radio_row = QHBoxLayout()
        ts_radio_row.setContentsMargins(0, 0, 0, 0)
        ts_radio_row.addWidget(self.radio_ts_on)
        ts_radio_row.addWidget(self.radio_ts_off)
        ts_radio_row.addStretch()
        ts_box.addLayout(ts_radio_row)

        ts_container = StanWidget()
        ts_container.setLayout(ts_box)

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

        self.line_edit_folder = QLineEdit()
        self.line_edit_folder.setReadOnly(True)
        self.line_edit_folder.setPlaceholderText("(project default)")

        self.button_browse_folder = StanButton("Browse", min_width=0)
        self.button_reset_folder = StanButton("Reset", min_width=0)

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
        self.button_csv = StanButton("Export CSV")
        self.button_csv.setIcon(QIcon(Paths.themed_icon("csv.svg")))
        self.button_json = StanButton("Export JSON")
        self.button_json.setIcon(QIcon(Paths.themed_icon("json.svg")))

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
        self.tabs = QTabWidget()
        self.tabs.addTab(standard_tab, "Standard Exports")
        self.tabs.addTab(self.advanced, "Advanced Exports")

        # ── Outer layout ───────────────────────────────────────────────────
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self.tabs)

        self.setLayout(outer_layout)
