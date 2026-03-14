"""category_view.py — View and editable table model for Transaction Categorisation.

Layout
------
The panel is split into two sections arranged vertically:

Top section (controls + table):
    [Run AI Categories]  [check: Re-run all]  [Save Manual Edits]
    Filter: [category combo]  [source combo]
    [Transaction table — editable Category column]
    [progress bar — hidden unless running]
    [counts label]

Bottom section (collapsible config):
    Ollama host / model / system prompt / categories list / [Save Config]
    [Ollama status indicator]
"""

from __future__ import annotations

import polars as pl
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
)

from openstan.components import (
    StanButton,
    StanCheckBox,
    StanLabel,
    StanPolarsModel,
    StanProgressBar,
    StanTableView,
    StanWidget,
)
from openstan.paths import Paths

# ---------------------------------------------------------------------------
# Editable table model
# ---------------------------------------------------------------------------

# Column index of the "Category" column in the display DataFrame
# (id_transaction is dropped before display, so columns are:
#  0=Date, 1=Account, 2=Description, 3=Category, 4=Source)
_COL_CATEGORY = 3


class CategoryTableModel(StanPolarsModel):
    """StanPolarsModel subclass that makes the Category column editable.

    Pending edits are stored in-memory keyed on the hidden id_transaction
    column that lives in *full_df* (the DataFrame passed at construction that
    still includes id_transaction at column 0 before display columns).

    The *display_df* passed here must NOT contain id_transaction — it is the
    already-sliced frame used for rendering.  The *id_transaction_series*
    provides the row-to-id mapping.
    """

    def __init__(
        self,
        display_df: pl.DataFrame,
        categories: list[str],
        id_transaction_series: pl.Series | None = None,
    ) -> None:
        super().__init__(display_df)
        self._categories: list[str] = categories
        # id_transaction_series maps row index → id_transaction string.
        # If absent (e.g. empty frame) pending edits are not tracked.
        self._id_series: pl.Series | None = id_transaction_series
        # pending_edits: {id_transaction: new_category}
        self._pending: dict[str, str] = {}

    # ── Qt model overrides ────────────────────────────────────────────────

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = super().flags(index)
        if index.column() == _COL_CATEGORY:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(
        self,
        index: QModelIndex,
        value: object,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole:
            return False
        if index.column() != _COL_CATEGORY:
            return False
        row = index.row()
        category = str(value).strip()
        if category not in self._categories:
            return False

        # Update the in-memory DataFrame
        self.df = self.df.with_columns(
            pl.when(pl.int_range(0, self.df.height) == row)
            .then(pl.lit(category))
            .otherwise(pl.col("Category"))
            .alias("Category")
        )

        # Track the pending edit
        if self._id_series is not None and row < len(self._id_series):
            id_tx = str(self._id_series[row])
            self._pending[id_tx] = category

        self.dataChanged.emit(index, index, [role])
        return True

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if role == Qt.ItemDataRole.UserRole and index.column() == _COL_CATEGORY:
            # Return the list of valid categories for the delegate combo
            return self._categories
        return super().data(index, role)

    # ── Pending edits API ─────────────────────────────────────────────────

    def pending_edits(self) -> dict[str, str]:
        """Return {id_transaction: category} for all unsaved manual edits."""
        return dict(self._pending)

    def clear_pending_edits(self) -> None:
        """Clear the pending edits after they have been persisted."""
        self._pending.clear()


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


class CategoryView(StanWidget):
    """Main panel for Transaction Categorisation."""

    header = "#### Transaction Categories — AI-powered categorisation via Ollama"

    def __init__(self) -> None:
        super().__init__()

        # ── Control bar (top) ─────────────────────────────────────────────
        self.button_run = StanButton("Run AI Categories")
        self.button_run.setIcon(QIcon(Paths.icon("run.svg")))
        self.button_run.setDisabled(True)

        self.button_back = StanButton("Back to Queue")
        self.button_back.setIcon(QIcon(Paths.icon("exit.svg")))

        self.check_rerun_all = StanCheckBox("Re-run all (overwrite AI)")

        self.button_save_manual = StanButton("Save Manual Edits")
        self.button_save_manual.setIcon(QIcon(Paths.icon("tick.svg")))

        # ── Filter bar ────────────────────────────────────────────────────
        self.combo_filter_category = QComboBox()
        self.combo_filter_category.addItem("All categories")
        self.combo_filter_category.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self.combo_filter_source = QComboBox()
        for item in ("All sources", "AI only", "Manual only", "Uncategorised"):
            self.combo_filter_source.addItem(item)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Filter:"))
        filter_bar.addWidget(self.combo_filter_category)
        filter_bar.addWidget(self.combo_filter_source)
        filter_bar.addStretch()

        # ── Transaction table ─────────────────────────────────────────────
        self.table = StanTableView()
        # Allow editing so the delegate can open a combo for the Category col
        self.table.setEditTriggers(
            StanTableView.EditTrigger.DoubleClicked
            | StanTableView.EditTrigger.SelectedClicked
        )

        # ── Progress + counts ─────────────────────────────────────────────
        self.progressBar = StanProgressBar()
        self.progressBar.setVisible(False)

        self.label_counts = StanLabel("No transactions loaded")

        # ── Ollama status (shown at the bottom of the table area) ─────────
        self.label_ollama_status = StanLabel("● Checking Ollama…")

        # ── Top-pane layout ───────────────────────────────────────────────
        top_widget = StanWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(4, 4, 4, 4)

        btn_bar = QHBoxLayout()
        btn_bar.addWidget(self.button_back)
        btn_bar.addWidget(self.button_run)
        btn_bar.addWidget(self.check_rerun_all)
        btn_bar.addStretch()
        btn_bar.addWidget(self.button_save_manual)

        top_layout.addLayout(btn_bar)
        top_layout.addLayout(filter_bar)
        top_layout.addWidget(self.table, stretch=1)
        top_layout.addWidget(self.progressBar)
        top_layout.addWidget(self.label_counts)
        top_layout.addWidget(self.label_ollama_status)
        top_widget.setLayout(top_layout)

        # ── Config pane (bottom) ──────────────────────────────────────────
        config_widget = StanWidget()
        config_layout = QGridLayout()
        config_layout.setContentsMargins(4, 4, 4, 4)

        config_layout.addWidget(StanLabel("**Ollama host:**"), 0, 0)
        self.edit_host = QLineEdit()
        self.edit_host.setPlaceholderText("http://localhost:11434")
        config_layout.addWidget(self.edit_host, 0, 1)

        config_layout.addWidget(StanLabel("**Model:**"), 1, 0)
        self.edit_model = QLineEdit()
        self.edit_model.setPlaceholderText("qwen2.5:1.5b")
        config_layout.addWidget(self.edit_model, 1, 1)

        config_layout.addWidget(StanLabel("**System prompt:**"), 2, 0)
        self.edit_system_prompt = QPlainTextEdit()
        self.edit_system_prompt.setMaximumHeight(80)
        config_layout.addWidget(self.edit_system_prompt, 2, 1)

        config_layout.addWidget(StanLabel("**Categories** (one per line):"), 3, 0)
        self.edit_categories = QPlainTextEdit()
        self.edit_categories.setMaximumHeight(120)
        config_layout.addWidget(self.edit_categories, 3, 1)

        self.button_save_config = StanButton("Save Config to TOML")
        self.button_save_config.setIcon(QIcon(Paths.icon("tick.svg")))
        config_layout.addWidget(self.button_save_config, 4, 1)

        config_widget.setLayout(config_layout)

        # ── Splitter: table pane (top) / config pane (bottom) ─────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(config_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)
        self.setLayout(outer)
