"""run_reports_view.py — Two-pane report builder + live preview panel.

Layout (horizontal QSplitter):

    Left pane  — ReportBuilderPane:
        • Saved Reports (always visible — Load / New reveals the rest)
        • Title / Subtitle fields
        • Column selector (checkable list)
        • Date Range filter (from/to QDateEdit)
        • Filters list + Add/Remove buttons
        • Group By list (checkable)
        • Aggregations list + Add/Remove buttons

    Right pane — ReportPreviewPane:
        • StanLabel for title / subtitle
        • StanTableView backed by StanPolarsModel (with sort proxy)
        • Live-updates toggle checkbox
        • Run Now button
        • Row-count label

The view exposes all widget references as public attributes; it contains zero
business logic.  All signal connections are made by ``RunReportsPresenter``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from PyQt6.QtCore import QDate, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from openstan.components import (
    StanButton,
    StanLabel,
    StanMutedLabel,
    StanPolarsModel,
    StanTableView,
    StanWidget,
)
from openstan.models.report_model import (
    AGGREGATION_FUNCTIONS,
    DERIVED_DATE_COLUMNS,
    FILTER_OPERATORS,
    FLAT_TRANSACTION_COLUMNS,
    NUMERIC_COLUMNS,
)


# ---------------------------------------------------------------------------
# Multi-select popup widget
# ---------------------------------------------------------------------------


class MultiSelectWidget(QWidget):
    """A tool-button that opens a popup checklist of distinct values.

    Selecting / deselecting items in the popup emits ``selection_changed``.
    The popup closes automatically when the user clicks outside it.
    """

    selection_changed: pyqtSignal = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._button = QToolButton()
        self._button.setMinimumWidth(120)
        self._button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._button.clicked.connect(self._show_popup)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)
        self.setLayout(layout)

        # Popup frame — Qt.WindowType.Popup closes it when clicking outside.
        self._popup = QFrame(
            None,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self._popup.setFrameShape(QFrame.Shape.StyledPanel)
        self._popup.setFrameShadow(QFrame.Shadow.Raised)

        self._list = QListWidget()
        self._list.setMinimumWidth(180)
        self._list.itemChanged.connect(self._on_item_changed)

        # Search box — filters visible items as the user types
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_list)

        # Tristate "All" checkbox above the list
        self._all_cb = QCheckBox("All")
        self._all_cb.setTristate(True)
        self._all_cb.clicked.connect(self._toggle_all)

        popup_layout = QVBoxLayout()
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(4)
        popup_layout.addWidget(self._search)
        popup_layout.addWidget(self._all_cb)
        popup_layout.addWidget(self._list)
        self._popup.setLayout(popup_layout)

        self._update_button_text()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_values(self, values: list[str], preserve_selection: bool = False) -> None:
        """Populate the checklist.

        Parameters
        ----------
        values:
            All available distinct values (sorted).
        preserve_selection:
            If ``True``, items that were previously checked remain checked
            where present in the new value list.  When ``False`` (default)
            all items start unchecked so the user can opt-in rather than
            having to deselect a potentially huge list.
        """
        previously_checked: set[str] = set()
        if preserve_selection:
            previously_checked = set(self.get_selected())

        self._list.blockSignals(True)
        self._list.clear()
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        for v in values:
            item = QListWidgetItem(v)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            state = (
                Qt.CheckState.Checked
                if (preserve_selection and v in previously_checked)
                else Qt.CheckState.Unchecked
            )
            item.setCheckState(state)
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._update_button_text()

    def get_selected(self) -> list[str]:
        """Return the list of checked values."""
        result: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                result.append(item.text())
        return result

    def set_selected(self, values: list[str]) -> None:
        """Check exactly the items whose text is in *values*."""
        vset = set(str(v) for v in values)
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked
                    if item.text() in vset
                    else Qt.CheckState.Unchecked
                )
        self._list.blockSignals(False)
        self._update_button_text()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _filter_list(self, text: str) -> None:
        """Show only list items whose text contains *text* (case-insensitive)."""
        needle = text.strip().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item:
                item.setHidden(bool(needle) and needle not in item.text().lower())

    def _toggle_all(self) -> None:
        """If all items are checked, uncheck all; otherwise check all."""
        total = self._list.count()
        checked = sum(
            1
            for i in range(total)
            if (item := self._list.item(i))
            and item.checkState() == Qt.CheckState.Checked
        )
        new_state = (
            Qt.CheckState.Unchecked if checked == total else Qt.CheckState.Checked
        )
        self._list.blockSignals(True)
        for i in range(total):
            item = self._list.item(i)
            if item:
                item.setCheckState(new_state)
        self._list.blockSignals(False)
        self._update_button_text()
        self.selection_changed.emit()

    def _show_popup(self) -> None:
        self._search.clear()  # reset search on each open
        button_rect = self._button.rect()
        pos = self._button.mapToGlobal(button_rect.bottomLeft())
        width = max(self._button.width(), self._list.minimumWidth())
        row_h = self._list.sizeHintForRow(0) if self._list.count() else 22
        list_h = min(220, row_h * max(1, self._list.count()) + 8)
        height = list_h + 60  # list + search box + all-checkbox + margins
        self._popup.setFixedSize(width, height)
        self._popup.move(pos)
        self._popup.show()
        self._search.setFocus()

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._update_button_text()
        self.selection_changed.emit()

    def _update_button_text(self) -> None:
        total = self._list.count()
        n = len(self.get_selected())
        if total == 0:
            text = "(no values loaded)"
        elif n == 0:
            text = "(none selected)"
        elif n == total:
            text = f"all {total} selected"
        else:
            text = f"{n} of {total} selected"
        self._button.setText(text)

        # Sync tristate checkbox
        self._all_cb.blockSignals(True)
        if total == 0 or n == 0:
            self._all_cb.setCheckState(Qt.CheckState.Unchecked)
        elif n == total:
            self._all_cb.setCheckState(Qt.CheckState.Checked)
        else:
            self._all_cb.setCheckState(Qt.CheckState.PartiallyChecked)
        self._all_cb.blockSignals(False)


# ---------------------------------------------------------------------------
# Filter row widget
# ---------------------------------------------------------------------------


class FilterRowWidget(QWidget):
    """A single filter rule: column ▸ operator ▸ value  [Remove].

    When the operator is ``is_in``, the plain text field is replaced by a
    ``MultiSelectWidget`` that shows distinct values for the chosen column.
    The ``values_needed`` signal is emitted whenever the presenter should
    asynchronously fetch and supply those distinct values.
    """

    removed: pyqtSignal = pyqtSignal(object)  # emits self
    # Emitted when the 'is_in' operator is active and distinct values are
    # needed for the current column.  Carries (self, column_name).
    values_needed: pyqtSignal = pyqtSignal(object, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)

        # Pending selected values to restore after async value load
        self._pending_is_in_values: list[str] = []

        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(130)
        for col, label in FLAT_TRANSACTION_COLUMNS:
            self.column_combo.addItem(label, col)

        self.operator_combo = QComboBox()
        for op, label in FILTER_OPERATORS:
            self.operator_combo.addItem(label, op)

        # Stacked widget: page 0 = plain text, page 1 = multi-select
        self._value_stack = QStackedWidget()
        self._value_stack.setMinimumWidth(120)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("value…")
        self._value_stack.addWidget(self.value_edit)

        self.multi_select = MultiSelectWidget()
        self._value_stack.addWidget(self.multi_select)

        self._value_stack.setCurrentIndex(0)

        self.remove_button = QPushButton("✕")
        self.remove_button.setFixedWidth(28)
        self.remove_button.setToolTip("Remove this filter")
        self.remove_button.clicked.connect(lambda: self.removed.emit(self))

        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(4)
        row.addWidget(self.column_combo)
        row.addWidget(self.operator_combo)
        row.addWidget(self._value_stack, stretch=1)
        row.addWidget(self.remove_button)
        self.setLayout(row)

        # Internal connections
        self.operator_combo.currentIndexChanged.connect(self._on_operator_changed)
        self.column_combo.currentIndexChanged.connect(self._on_column_changed)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_operator_changed(self) -> None:
        op = self.operator_combo.currentData()
        if op in ("is_in", "not_in"):
            self._value_stack.setCurrentIndex(1)
            col = self.column_combo.currentData()
            if col:
                self.values_needed.emit(self, col)
        else:
            self._value_stack.setCurrentIndex(0)

    def _on_column_changed(self) -> None:
        """If is_in / not_in is active, request fresh distinct values for the new column."""
        if self.operator_combo.currentData() in ("is_in", "not_in"):
            col = self.column_combo.currentData()
            if col:
                self.multi_select.set_values([])
                self.values_needed.emit(self, col)

    # ------------------------------------------------------------------
    # Public: distinct values supply
    # ------------------------------------------------------------------

    def set_distinct_values(self, values: list[str]) -> None:
        """Called by the presenter with the distinct values for the current column."""
        self.multi_select.set_values(values)
        if self._pending_is_in_values:
            self.multi_select.set_selected(self._pending_is_in_values)
            self._pending_is_in_values = []

    # ------------------------------------------------------------------
    # Read / write helpers
    # ------------------------------------------------------------------

    def get_definition(self) -> dict:
        op = self.operator_combo.currentData()
        if op in ("is_in", "not_in"):
            value: object = self.multi_select.get_selected()
        else:
            value = self.value_edit.text().strip()
        return {
            "column": self.column_combo.currentData(),
            "operator": op,
            "value": value,
        }

    def set_definition(self, d: dict) -> None:
        col_idx = self.column_combo.findData(d.get("column", ""))
        if col_idx >= 0:
            self.column_combo.setCurrentIndex(col_idx)

        op = d.get("operator", "eq")
        raw_value = d.get("value", "")

        if op in ("is_in", "not_in"):
            # Store pending values — applied once set_distinct_values is called
            if isinstance(raw_value, list):
                self._pending_is_in_values = [str(v) for v in raw_value]
            else:
                # Backward compat: comma-separated string
                self._pending_is_in_values = [
                    v.strip() for v in str(raw_value).split(",") if v.strip()
                ]

        op_idx = self.operator_combo.findData(op)
        if op_idx >= 0:
            self.operator_combo.setCurrentIndex(op_idx)
            # ^^ triggers _on_operator_changed → emits values_needed if is_in

        if op not in ("is_in", "not_in"):
            self.value_edit.setText(str(raw_value))


# ---------------------------------------------------------------------------
# Aggregation row widget
# ---------------------------------------------------------------------------


class AggRowWidget(QWidget):
    """A single aggregation: column ▸ function ▸ alias  [Remove]."""

    removed: pyqtSignal = pyqtSignal(object)  # emits self

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)

        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(130)
        for col, label in NUMERIC_COLUMNS:
            self.column_combo.addItem(label, col)

        self.function_combo = QComboBox()
        for fn, label in AGGREGATION_FUNCTIONS:
            self.function_combo.addItem(label, fn)

        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("alias (optional)")
        self.alias_edit.setMinimumWidth(110)

        self.remove_button = QPushButton("✕")
        self.remove_button.setFixedWidth(28)
        self.remove_button.setToolTip("Remove this aggregation")
        self.remove_button.clicked.connect(lambda: self.removed.emit(self))

        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(4)
        row.addWidget(self.column_combo)
        row.addWidget(self.function_combo)
        row.addWidget(self.alias_edit, stretch=1)
        row.addWidget(self.remove_button)
        self.setLayout(row)

    def get_definition(self) -> dict:
        return {
            "column": self.column_combo.currentData(),
            "function": self.function_combo.currentData(),
            "alias": self.alias_edit.text().strip(),
        }

    def set_definition(self, d: dict) -> None:
        col_idx = self.column_combo.findData(d.get("column", ""))
        if col_idx >= 0:
            self.column_combo.setCurrentIndex(col_idx)
        fn_idx = self.function_combo.findData(d.get("function", "sum"))
        if fn_idx >= 0:
            self.function_combo.setCurrentIndex(fn_idx)
        self.alias_edit.setText(str(d.get("alias", "")))


# ---------------------------------------------------------------------------
# Left pane: builder
# ---------------------------------------------------------------------------


class ReportBuilderPane(QWidget):
    """Left pane — all configuration controls for a report.

    All widgets are public attributes; no signal connections are made here.

    On first load the builder content (everything except Saved Reports) is
    hidden.  Call ``set_builder_visible(True)`` to reveal it after the user
    clicks Load or New.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)

        outer = QVBoxLayout()
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        # ── Save / Load (always visible at the top) ───────────────────
        persist_box = QGroupBox("Saved Reports")
        persist_layout = QVBoxLayout()
        persist_layout.setSpacing(6)

        save_row = QHBoxLayout()
        self.button_save = StanButton("Save Report", min_width=110)
        self.button_delete = StanButton("Delete", min_width=80)
        save_row.addWidget(self.button_save)
        save_row.addWidget(self.button_delete)
        save_row.addStretch()

        load_row = QHBoxLayout()
        self.saved_reports_combo = QComboBox()
        self.saved_reports_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.button_load = StanButton("Load", min_width=60)
        self.button_new = StanButton("New", min_width=60)
        load_row.addWidget(self.saved_reports_combo, stretch=1)
        load_row.addWidget(self.button_load)
        load_row.addWidget(self.button_new)

        persist_layout.addLayout(save_row)
        persist_layout.addLayout(load_row)
        persist_box.setLayout(persist_layout)
        outer.addWidget(persist_box)

        # ── Builder content (hidden until Load or New) ────────────────
        self.builder_content = QWidget()
        self.builder_content.setAutoFillBackground(True)
        self.builder_content.hide()

        builder_layout = QVBoxLayout()
        builder_layout.setContentsMargins(0, 0, 0, 0)
        builder_layout.setSpacing(8)

        # ── Meta ──────────────────────────────────────────────────────
        meta_box = QGroupBox("Report Details")
        meta_form = QFormLayout()
        meta_form.setSpacing(6)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Report title…")
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Subtitle (optional)…")
        meta_form.addRow("Title:", self.title_edit)
        meta_form.addRow("Subtitle:", self.subtitle_edit)
        meta_box.setLayout(meta_form)
        builder_layout.addWidget(meta_box)

        # ── Column selector ───────────────────────────────────────────
        cols_box = QGroupBox("Columns")
        cols_layout = QVBoxLayout()
        cols_layout.setSpacing(2)

        # Tristate "All" checkbox for base columns
        self.checkbox_cols_all = QCheckBox("All")
        self.checkbox_cols_all.setTristate(True)

        self.columns_list = QListWidget()
        self.columns_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.columns_list.setMaximumHeight(160)
        for col, label in FLAT_TRANSACTION_COLUMNS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.columns_list.addItem(item)

        # Tristate "All" checkbox for derived date columns
        self.checkbox_derived_all = QCheckBox("All")
        self.checkbox_derived_all.setTristate(True)

        self.derived_label = QLabel("Derived date columns:")
        self.derived_list = QListWidget()
        self.derived_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.derived_list.setMaximumHeight(100)
        for col, label in DERIVED_DATE_COLUMNS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.derived_list.addItem(item)

        cols_layout.addWidget(self.checkbox_cols_all)
        cols_layout.addWidget(self.columns_list)
        cols_layout.addWidget(self.derived_label)
        cols_layout.addWidget(self.checkbox_derived_all)
        cols_layout.addWidget(self.derived_list)
        cols_box.setLayout(cols_layout)
        builder_layout.addWidget(cols_box)

        # ── Date Range ────────────────────────────────────────────────
        date_range_box = QGroupBox("Date Range")
        date_range_layout = QVBoxLayout()
        date_range_layout.setSpacing(6)

        self.date_range_enabled = QCheckBox("Filter by date range")

        date_row = QHBoxLayout()
        date_row.setSpacing(6)
        date_row.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setDate(QDate.currentDate().addYears(-1))
        self.from_date.setEnabled(False)
        date_row.addWidget(self.from_date)
        date_row.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setEnabled(False)
        date_row.addWidget(self.to_date)
        date_row.addStretch()

        date_range_layout.addWidget(self.date_range_enabled)
        date_range_layout.addLayout(date_row)
        date_range_box.setLayout(date_range_layout)
        builder_layout.addWidget(date_range_box)

        # ── Filters ───────────────────────────────────────────────────
        filter_box = QGroupBox("Filters")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(4)

        # Container for dynamically added FilterRowWidgets
        self._filter_container = QWidget()
        self._filter_container.setAutoFillBackground(True)
        self._filter_rows_layout = QVBoxLayout()
        self._filter_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_rows_layout.setSpacing(2)
        self._filter_container.setLayout(self._filter_rows_layout)

        self.button_add_filter = QPushButton("+ Add Filter")
        self.button_add_filter.setFixedWidth(110)

        filter_layout.addWidget(self._filter_container)
        filter_layout.addWidget(
            self.button_add_filter, alignment=Qt.AlignmentFlag.AlignLeft
        )
        filter_box.setLayout(filter_layout)
        builder_layout.addWidget(filter_box)

        # ── Group By ──────────────────────────────────────────────────
        groupby_box = QGroupBox("Group By")
        groupby_layout = QVBoxLayout()
        groupby_layout.setSpacing(2)
        self.groupby_list = QListWidget()
        self.groupby_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.groupby_list.setMaximumHeight(110)
        # Populated dynamically based on checked columns + derived columns
        groupby_layout.addWidget(self.groupby_list)
        groupby_box.setLayout(groupby_layout)
        builder_layout.addWidget(groupby_box)

        # ── Aggregations ──────────────────────────────────────────────
        agg_box = QGroupBox("Aggregations")
        agg_layout = QVBoxLayout()
        agg_layout.setSpacing(4)

        self._agg_container = QWidget()
        self._agg_container.setAutoFillBackground(True)
        self._agg_rows_layout = QVBoxLayout()
        self._agg_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._agg_rows_layout.setSpacing(2)
        self._agg_container.setLayout(self._agg_rows_layout)

        self.button_add_agg = QPushButton("+ Add Aggregation")
        self.button_add_agg.setFixedWidth(140)

        agg_layout.addWidget(self._agg_container)
        agg_layout.addWidget(self.button_add_agg, alignment=Qt.AlignmentFlag.AlignLeft)
        agg_box.setLayout(agg_layout)
        builder_layout.addWidget(agg_box)

        builder_layout.addStretch()
        self.builder_content.setLayout(builder_layout)
        outer.addWidget(self.builder_content)

        outer.addStretch()
        self.setLayout(outer)

    # ------------------------------------------------------------------
    # Builder visibility toggle
    # ------------------------------------------------------------------

    def set_builder_visible(self, visible: bool) -> None:
        """Show or hide the builder content (everything except Saved Reports)."""
        self.builder_content.setVisible(visible)

    # ------------------------------------------------------------------
    # Dynamic row management (called by presenter)
    # ------------------------------------------------------------------

    def add_filter_row(self) -> FilterRowWidget:
        """Append a new empty FilterRowWidget and return it."""
        row = FilterRowWidget(self)
        self._filter_rows_layout.addWidget(row)
        self._filter_container.adjustSize()
        self._filter_container.updateGeometry()
        return row

    def remove_filter_row(self, row: FilterRowWidget) -> None:
        """Remove and destroy a FilterRowWidget."""
        row.hide()
        self._filter_rows_layout.removeWidget(row)
        row.setParent(None)  # type: ignore[arg-type]
        row.deleteLater()
        self._filter_container.adjustSize()
        self._filter_container.updateGeometry()

    def filter_rows(self) -> list[FilterRowWidget]:
        """Return all current FilterRowWidgets in order."""
        rows: list[FilterRowWidget] = []
        for i in range(self._filter_rows_layout.count()):
            item = self._filter_rows_layout.itemAt(i)
            if item and isinstance(item.widget(), FilterRowWidget):
                rows.append(item.widget())  # type: ignore[arg-type]
        return rows

    def add_agg_row(self) -> AggRowWidget:
        """Append a new empty AggRowWidget and return it."""
        row = AggRowWidget(self)
        self._agg_rows_layout.addWidget(row)
        self._agg_container.adjustSize()
        self._agg_container.updateGeometry()
        return row

    def remove_agg_row(self, row: AggRowWidget) -> None:
        """Remove and destroy an AggRowWidget."""
        row.hide()
        self._agg_rows_layout.removeWidget(row)
        row.setParent(None)  # type: ignore[arg-type]
        row.deleteLater()
        self._agg_container.adjustSize()
        self._agg_container.updateGeometry()

    def agg_rows(self) -> list[AggRowWidget]:
        """Return all current AggRowWidgets in order."""
        rows: list[AggRowWidget] = []
        for i in range(self._agg_rows_layout.count()):
            item = self._agg_rows_layout.itemAt(i)
            if item and isinstance(item.widget(), AggRowWidget):
                rows.append(item.widget())  # type: ignore[arg-type]
        return rows

    # ------------------------------------------------------------------
    # Group-by list refresh
    # ------------------------------------------------------------------

    def refresh_groupby_list(self, available_columns: list[tuple[str, str]]) -> None:
        """Repopulate the group-by list from the given (col, label) pairs.

        Preserves checked state for items that were already present.
        """
        previously_checked: set[str] = set()
        for i in range(self.groupby_list.count()):
            item = self.groupby_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                previously_checked.add(item.data(Qt.ItemDataRole.UserRole))

        self.groupby_list.clear()
        for col, label in available_columns:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            state = (
                Qt.CheckState.Checked
                if col in previously_checked
                else Qt.CheckState.Unchecked
            )
            item.setCheckState(state)
            self.groupby_list.addItem(item)


# ---------------------------------------------------------------------------
# Right pane: preview
# ---------------------------------------------------------------------------


class ReportPreviewPane(QWidget):
    """Right pane — StanTableView + run controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.live_checkbox = QCheckBox("Live updates")
        self.live_checkbox.setChecked(True)
        self.live_checkbox.setToolTip(
            "When checked, the preview updates automatically as you make changes.\n"
            "Uncheck to defer updates and use 'Run Now' manually."
        )

        self.button_run = StanButton("Run Now", min_width=90)
        self.button_run.setToolTip("Run the report and refresh the preview")

        self.row_count_label = StanLabel("")
        self.row_count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        toolbar.addWidget(self.live_checkbox)
        toolbar.addWidget(self.button_run)
        toolbar.addStretch()
        toolbar.addWidget(self.row_count_label)

        layout.addLayout(toolbar)

        # Title / subtitle labels
        self.title_label = StanLabel("")
        self.subtitle_label = StanMutedLabel("")
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        # Table view
        self.table_view = StanTableView()
        header = self.table_view.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.table_view.hide()
        layout.addWidget(self.table_view, stretch=1)

        # Placeholder shown before any query has run
        self.placeholder_label = StanMutedLabel(
            "Configure your report on the left and press **Run Now**, "
            "or enable **Live updates** to see a preview as you make changes."
        )
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self.placeholder_label, stretch=1)

        # Error label (hidden until an error occurs)
        self.error_label = StanLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.error_label.hide()
        layout.addWidget(self.error_label, stretch=1)

        self.setLayout(layout)

    def set_dataframe(self, df: pl.DataFrame, title: str, subtitle: str) -> None:
        """Display a polars DataFrame in the table view."""
        import polars as _pl

        # Round float columns to 2 decimal places
        float_cols = [
            c for c in df.columns if df.schema[c] in (_pl.Float32, _pl.Float64)
        ]
        if float_cols:
            df = df.with_columns([_pl.col(c).round(2) for c in float_cols])

        source_model = StanPolarsModel(df)
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(source_model)
        self.table_view.setModel(proxy)
        self.title_label.setText(f"##### {title}" if title else "")
        self.subtitle_label.setText(subtitle)
        self.error_label.hide()
        self.placeholder_label.hide()
        self.table_view.show()

    def set_row_count(self, n: int | None) -> None:
        """Update the row-count label."""
        if n is None:
            self.row_count_label.setText("")
        else:
            self.row_count_label.setText(f"###### {n:,} row{'s' if n != 1 else ''}")

    def set_error(self, message: str) -> None:
        """Display an error message, hiding the table."""
        self.table_view.hide()
        self.placeholder_label.hide()
        self.error_label.setText(f"**Error:** {message}")
        self.error_label.show()
        self.row_count_label.setText("")

    def clear(self) -> None:
        """Reset to the initial placeholder state."""
        self.table_view.hide()
        self.error_label.hide()
        self.title_label.setText("")
        self.subtitle_label.setText("")
        self.row_count_label.setText("")
        self.placeholder_label.show()


# ---------------------------------------------------------------------------
# Main panel view
# ---------------------------------------------------------------------------


class RunReportsView(StanWidget):
    """Full Run Reports panel — replaces the stub.

    Contains a horizontal QSplitter with the builder pane on the left and
    the preview pane on the right.  The header attribute is read by
    ``ContentFrameView`` in ``main.py`` to set the panel title label.
    """

    header: str = "##### Run Reports"

    def __init__(self) -> None:
        super().__init__()

        self.builder = ReportBuilderPane()
        self.preview = ReportPreviewPane()

        # Wrap builder in a scroll area so it stays usable at small heights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.builder)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(320)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 700])

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setLayout(layout)
