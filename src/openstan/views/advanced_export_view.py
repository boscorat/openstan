"""advanced_export_view.py — Advanced Export pane view.

Presents a parameter panel for configuring ``export_spec`` parameters
(account, statement, date range) and a scrollable list of spec buttons,
one per ``.toml`` file found in the current project's ``config/export/``
directory.  All wiring and business logic lives in
``AdvancedExportPresenter`` — this module contains only layout and widget
declarations.
"""

from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
)

from openstan.components import (
    Qt,
    StanButton,
    StanCheckBox,
    StanComboBox,
    StanDateEdit,
    StanFrame,
    StanHelpIcon,
    StanLabel,
    StanMutedLabel,
    StanProgressBar,
    StanScrollArea,
    StanWidget,
)

# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

_HELP_ACCOUNT = (
    "The account to export data for.  Corresponds to ``DimAccount.id_account`` "
    "in the project datamart.  Select '<all accounts>' to pass ``account_key=None`` "
    "to ``export_spec`` — note this currently requires a BSP update to function "
    "without error."
)

_HELP_STATEMENT = (
    "Optional filter to restrict the export to a single statement.  "
    "The list is filtered to statements belonging to the selected account.  "
    "Select '(all statements)' to export all statements for the account."
)

_HELP_DATE_FROM = "Optional earliest transaction date (inclusive).  Tick 'No date' to leave unset, which exports from the beginning of the data."

_HELP_DATE_TO = "Optional latest transaction date (inclusive).  Tick 'No date' to leave unset, which exports up to the most recent transaction."


class AdvancedExportView(StanWidget):
    """Advanced Export pane.

    Exposes a parameter panel for ``export_spec`` parameters and a
    scrollable list of spec ``StanButton`` instances.  All wiring lives
    in ``AdvancedExportPresenter``.

    Public attributes
    -----------------
    combo_account : QComboBox
        Account selector.  Item 0 is always ``"<all accounts>"``,
        ``userData=None``; subsequent items carry ``userData=id_account``.
    combo_statement : QComboBox
        Statement selector.  Item 0 is always ``"(all statements)"``,
        ``userData=None``; subsequent items carry ``userData=id_statement``.
    date_from : QDateEdit
        Earliest date widget.  Enabled only when ``check_date_from_none``
        is unchecked.
    check_date_from_none : QCheckBox
        "No date" toggle for ``date_from``.
    date_to : QDateEdit
        Latest date widget.  Enabled only when ``check_date_to_none``
        is unchecked.
    check_date_to_none : QCheckBox
        "No date" toggle for ``date_to``.
    spec_list_widget : QWidget
        Container widget inside the scroll area.  The presenter clears and
        repopulates its layout with ``StanButton`` instances.
    label_no_specs : StanMutedLabel
        Shown in place of the scroll area when no project is loaded or no
        ``.toml`` files are found.
    progress_bar : StanProgressBar
        Indeterminate progress bar shown while an export worker is running.
    label_status : StanLabel
        Post-export status message.
    """

    def __init__(self) -> None:
        super().__init__()

        # ── Description ───────────────────────────────────────────────────
        description = StanMutedLabel(
            "Select a spec file below to run a custom export.  Configure the parameters above to filter the output."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # ── Parameter panel ───────────────────────────────────────────────
        param_frame = StanFrame()
        param_grid = QGridLayout()
        param_grid.setSpacing(10)
        param_grid.setContentsMargins(12, 12, 12, 12)
        param_grid.setColumnStretch(1, 1)

        # -- Row 0: Account -----------------------------------------------
        account_label_row = QHBoxLayout()
        account_label_row.setContentsMargins(0, 0, 0, 0)
        account_label_row.addWidget(StanLabel("**Account**"))
        account_label_row.addWidget(StanHelpIcon(_HELP_ACCOUNT))
        account_label_row.addStretch()

        self.combo_account = StanComboBox()
        self.combo_account.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.combo_account.setAccessibleName("Account filter")

        param_grid.addLayout(account_label_row, 0, 0)
        param_grid.addWidget(self.combo_account, 0, 1)

        # -- Row 1: Statement ---------------------------------------------
        statement_label_row = QHBoxLayout()
        statement_label_row.setContentsMargins(0, 0, 0, 0)
        statement_label_row.addWidget(StanLabel("**Statement**"))
        statement_label_row.addWidget(StanHelpIcon(_HELP_STATEMENT))
        statement_label_row.addStretch()

        self.combo_statement = StanComboBox()
        self.combo_statement.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.combo_statement.setAccessibleName("Statement filter")

        param_grid.addLayout(statement_label_row, 1, 0)
        param_grid.addWidget(self.combo_statement, 1, 1)

        # -- Row 2: Date from ---------------------------------------------
        date_from_label_row = QHBoxLayout()
        date_from_label_row.setContentsMargins(0, 0, 0, 0)
        date_from_label_row.addWidget(StanLabel("**Date from**"))
        date_from_label_row.addWidget(StanHelpIcon(_HELP_DATE_FROM))
        date_from_label_row.addStretch()

        self.date_from = StanDateEdit()
        self.date_from.setEnabled(False)  # starts disabled — "No date" is default
        self.date_from.setAccessibleName("Date from")

        self.check_date_from_none = StanCheckBox("No date")
        self.check_date_from_none.setChecked(True)
        self.check_date_from_none.setAccessibleName("No start date")
        self.check_date_from_none.toggled.connect(
            lambda checked: self.date_from.setEnabled(not checked)
        )

        date_from_controls = QHBoxLayout()
        date_from_controls.setContentsMargins(0, 0, 0, 0)
        date_from_controls.addWidget(self.date_from)
        date_from_controls.addWidget(self.check_date_from_none)
        date_from_controls.addStretch()

        param_grid.addLayout(date_from_label_row, 2, 0)
        param_grid.addLayout(date_from_controls, 2, 1)

        # -- Row 3: Date to -----------------------------------------------
        date_to_label_row = QHBoxLayout()
        date_to_label_row.setContentsMargins(0, 0, 0, 0)
        date_to_label_row.addWidget(StanLabel("**Date to**"))
        date_to_label_row.addWidget(StanHelpIcon(_HELP_DATE_TO))
        date_to_label_row.addStretch()

        self.date_to = StanDateEdit()
        self.date_to.setEnabled(False)  # starts disabled — "No date" is default
        self.date_to.setAccessibleName("Date to")

        self.check_date_to_none = StanCheckBox("No date")
        self.check_date_to_none.setChecked(True)
        self.check_date_to_none.setAccessibleName("No end date")
        self.check_date_to_none.toggled.connect(
            lambda checked: self.date_to.setEnabled(not checked)
        )

        date_to_controls = QHBoxLayout()
        date_to_controls.setContentsMargins(0, 0, 0, 0)
        date_to_controls.addWidget(self.date_to)
        date_to_controls.addWidget(self.check_date_to_none)
        date_to_controls.addStretch()

        param_grid.addLayout(date_to_label_row, 3, 0)
        param_grid.addLayout(date_to_controls, 3, 1)

        param_frame.setLayout(param_grid)

        # ── Spec list section label ────────────────────────────────────────
        specs_label = StanLabel("**Export specs**")

        # ── Empty-state label (shown when no project or no .toml files) ───
        self.label_no_specs = StanMutedLabel(
            "No export specs found.  Add .toml spec files to <project>/config/export/ to see them here."
        )
        self.label_no_specs.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_no_specs.setVisible(True)

        # ── Scrollable spec button list ────────────────────────────────────
        # spec_list_widget holds a QVBoxLayout that the presenter populates
        # with one StanButton per .toml file.  The scroll area expands to
        # fill all remaining vertical space in the tab.
        self.spec_list_widget = StanWidget()
        spec_list_layout = QVBoxLayout()
        spec_list_layout.setContentsMargins(0, 0, 0, 0)
        spec_list_layout.setSpacing(4)
        spec_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.spec_list_widget.setLayout(spec_list_layout)

        self.scroll_area = StanScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.spec_list_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVisible(False)  # shown by presenter when specs are loaded

        # ── Progress / status ──────────────────────────────────────────────
        self.progress_bar = StanProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate (marquee)
        self.progress_bar.setVisible(False)

        self.label_status = StanLabel("")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # ── Outer layout ───────────────────────────────────────────────────
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.setSpacing(12)

        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addWidget(param_frame)
        layout.addSpacing(4)
        layout.addWidget(specs_label)
        layout.addWidget(self.label_no_specs)
        layout.addWidget(self.scroll_area, stretch=1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.label_status)

        self.setLayout(layout)

    def setup_tab_order(self) -> None:
        """Establish an explicit, logical Tab key traversal order."""
        self.setTabOrder(self.combo_account, self.combo_statement)
        self.setTabOrder(self.combo_statement, self.check_date_from_none)
        self.setTabOrder(self.check_date_from_none, self.date_from)
        self.setTabOrder(self.date_from, self.check_date_to_none)
        self.setTabOrder(self.check_date_to_none, self.date_to)


def make_spec_button(filename: str, description: str) -> StanButton:
    """Create a full-width spec selector button.

    The button label uses markdown to show the filename in bold on the
    first line and the spec description in a second muted line.

    Parameters
    ----------
    filename:
        The ``.toml`` filename (stem + extension), e.g. ``"quickbooks_3column.toml"``.
    description:
        The ``[meta]description`` string from the spec file.
    """
    btn = StanButton(f"{description} ({filename})", min_width=0)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn.setStyleSheet("text-align: left; padding: 8px 12px;")
    return btn
