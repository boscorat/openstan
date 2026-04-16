"""run_reports_presenter.py — Presenter for the Run Reports panel.

Responsibilities:

* Wires all signals from ``RunReportsView`` to business logic.
* Builds a ``polars.LazyFrame`` query from the current builder state
  (filters, group-by, aggregations, column selection, date range).
* Runs the query in a background ``QRunnable`` and renders the result
  via StanPolarsModel into the preview pane.
* Loads and saves report definitions via ``ReportModel``.
* Receives the active ``project_path`` from ``StanPresenter`` via the
  ``load_project`` method (consistent with ``AdvancedExportPresenter``).

Architecture notes
------------------
* Zero business logic lives in the view — the presenter reads widget state
  directly and writes back when loading a report definition.
* Live-update queries are debounced via a ``QTimer`` (300 ms) so rapid
  checkbox toggles do not fire a flood of queries.
* The background worker uses the existing ``QRunnable`` pattern (see
  ``workers.py``) adapted for report queries.
"""

from __future__ import annotations

import traceback
from datetime import date as _date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import bank_statement_parser as bsp
import polars as pl
from PyQt6.QtCore import (
    QDate,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Qt,
    pyqtSignal,
    pyqtSlot,
)

from openstan.components import StanErrorMessage, StanInfoMessage
from openstan.models.report_model import (
    DERIVED_DATE_COLUMNS,
    FLAT_TRANSACTION_COLUMNS,
    ReportModel,
    _slugify,
)
from openstan.views.run_reports_view import (
    AggRowWidget,
    FilterRowWidget,
    RunReportsView,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QListWidget


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _ReportWorkerSignals(QObject):
    finished: pyqtSignal = pyqtSignal(object, int)  # (pl.DataFrame, row_count)
    error: pyqtSignal = pyqtSignal(str)


class _ReportWorker(QRunnable):
    """Runs a polars query off the main thread."""

    def __init__(self, fn: Any) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _ReportWorkerSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            df: pl.DataFrame = self.fn()
            self.signals.finished.emit(df, df.height)
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(str(e))


# ---------------------------------------------------------------------------
# Distinct-values fetcher worker
# ---------------------------------------------------------------------------


class _FetchWorkerSignals(QObject):
    finished: pyqtSignal = pyqtSignal(object)  # list[str]
    error: pyqtSignal = pyqtSignal(str)


class _FetchWorker(QRunnable):
    """Fetches distinct string values for a single column off the main thread."""

    def __init__(self, fn: Any) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _FetchWorkerSignals()
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            self.signals.finished.emit(self.fn())
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(str(e))


# ---------------------------------------------------------------------------
# Derived date extraction helpers
# ---------------------------------------------------------------------------

_DERIVED_EXTRACTORS: dict[str, Any] = {
    "year": lambda col: col.dt.year().alias("year"),
    "quarter": lambda col: col.dt.quarter().alias("quarter"),
    "month_number": lambda col: col.dt.month().alias("month_number"),
    "month_name": lambda col: col.dt.to_string("%B").alias("month_name"),
    "week": lambda col: col.dt.week().alias("week"),
    "day_of_week": lambda col: col.dt.to_string("%A").alias("day_of_week"),
}

# Map derived column name → friendly label for group-by list population
_DERIVED_LABEL: dict[str, str] = {k: v for k, v in DERIVED_DATE_COLUMNS}
_COL_LABEL: dict[str, str] = {k: v for k, v in FLAT_TRANSACTION_COLUMNS}


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class RunReportsPresenter(QObject):
    """Presenter for the Run Reports panel.

    Parameters
    ----------
    model:
        ``ReportModel`` instance for filesystem CRUD.
    view:
        ``RunReportsView`` instance.
    threadpool:
        Shared ``QThreadPool``; if ``None`` a private pool is created.
    """

    def __init__(
        self,
        model: ReportModel,
        view: RunReportsView,
        threadpool: QThreadPool | None = None,
    ) -> None:
        super().__init__()
        self.model: ReportModel = model
        self.view: RunReportsView = view
        self.threadpool: QThreadPool = threadpool or QThreadPool()

        # Active project path — set by StanPresenter.
        self.project_path: Path | None = None

        # Track the path of the currently loaded report (None = unsaved new).
        self._current_report_path: Path | None = None

        # Worker in-flight guard
        self._query_running: bool = False

        # Error dialog
        self._error_dialog = StanErrorMessage(view)

        # Debounce timer for live updates
        self._live_timer = QTimer()
        self._live_timer.setSingleShot(True)
        self._live_timer.setInterval(300)  # ms
        self._live_timer.timeout.connect(self._run_preview)

        # ── Wire signals ──────────────────────────────────────────────
        b = self.view.builder
        p = self.view.preview

        # Meta fields
        b.title_edit.textChanged.connect(self._on_change)
        b.subtitle_edit.textChanged.connect(self._on_change)

        # Column checkboxes
        b.columns_list.itemChanged.connect(self._on_columns_changed)
        b.derived_list.itemChanged.connect(self._on_columns_changed)
        b.checkbox_cols_all.clicked.connect(self._toggle_cols_all)
        b.checkbox_derived_all.clicked.connect(self._toggle_derived_all)

        # Date range
        b.date_range_enabled.toggled.connect(self._on_date_range_toggled)
        b.from_date.dateChanged.connect(self._on_change)
        b.to_date.dateChanged.connect(self._on_change)

        # Filter / agg add buttons
        b.button_add_filter.clicked.connect(self._add_filter_row)
        b.button_add_agg.clicked.connect(self._add_agg_row)

        # Group-by list
        b.groupby_list.itemChanged.connect(self._on_change)

        # Save / load / delete / new
        b.button_save.clicked.connect(self._save_report)
        b.button_load.clicked.connect(self._load_selected_report)
        b.button_delete.clicked.connect(self._delete_selected_report)
        b.button_new.clicked.connect(self._new_report)

        # Model changed (external save/delete)
        self.model.reports_changed.connect(self._refresh_saved_reports_combo)

        # Preview controls
        p.button_run.clicked.connect(self._run_preview)
        p.live_checkbox.toggled.connect(self._on_live_toggled)

    # ---------------------------------------------------------------------------
    # Project lifecycle
    # ---------------------------------------------------------------------------

    def load_project(self, project_path: Path) -> None:
        """Called by ``StanPresenter`` when the active project changes."""
        self.project_path = project_path
        self._current_report_path = None
        self._refresh_saved_reports_combo()
        self._clear_builder()
        self.view.builder.set_builder_visible(False)

    # ---------------------------------------------------------------------------
    # Live update handling
    # ---------------------------------------------------------------------------

    def _on_live_toggled(self, checked: bool) -> None:
        if checked:
            self._schedule_preview()

    def _on_change(self) -> None:
        """Called whenever any builder control changes."""
        self._schedule_preview()

    def _on_columns_changed(self) -> None:
        """Column or derived-date check state changed — refresh group-by list first."""
        self._refresh_groupby_list()
        self._update_all_checkboxes()
        self._schedule_preview()

    def _on_date_range_toggled(self, checked: bool) -> None:
        b = self.view.builder
        b.from_date.setEnabled(checked)
        b.to_date.setEnabled(checked)
        self._on_change()

    # ------------------------------------------------------------------
    # Tristate "All" checkbox helpers
    # ------------------------------------------------------------------

    def _toggle_cols_all(self) -> None:
        b = self.view.builder
        total = b.columns_list.count()
        checked = sum(
            1
            for i in range(total)
            if (item := b.columns_list.item(i))
            and item.checkState() == Qt.CheckState.Checked
        )
        new_state = (
            Qt.CheckState.Unchecked if checked == total else Qt.CheckState.Checked
        )
        self._set_list_check_all(b.columns_list, new_state)

    def _toggle_derived_all(self) -> None:
        b = self.view.builder
        total = b.derived_list.count()
        checked = sum(
            1
            for i in range(total)
            if (item := b.derived_list.item(i))
            and item.checkState() == Qt.CheckState.Checked
        )
        new_state = (
            Qt.CheckState.Unchecked if checked == total else Qt.CheckState.Checked
        )
        self._set_list_check_all(b.derived_list, new_state)

    def _update_all_checkboxes(self) -> None:
        """Sync the tristate state of checkbox_cols_all and checkbox_derived_all."""
        b = self.view.builder
        for list_widget, cb in (
            (b.columns_list, b.checkbox_cols_all),
            (b.derived_list, b.checkbox_derived_all),
        ):
            total = list_widget.count()
            n_checked = sum(
                1
                for i in range(total)
                if (item := list_widget.item(i))
                and item.checkState() == Qt.CheckState.Checked
            )
            cb.blockSignals(True)
            if total == 0 or n_checked == 0:
                cb.setCheckState(Qt.CheckState.Unchecked)
            elif n_checked == total:
                cb.setCheckState(Qt.CheckState.Checked)
            else:
                cb.setCheckState(Qt.CheckState.PartiallyChecked)
            cb.blockSignals(False)

    def _set_list_check_all(
        self, list_widget: "QListWidget", state: "Qt.CheckState"
    ) -> None:
        list_widget.blockSignals(True)
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item:
                item.setCheckState(state)
        list_widget.blockSignals(False)
        self._on_columns_changed()

    def _schedule_preview(self) -> None:
        """Trigger a preview refresh if live updates are enabled."""
        if self.view.preview.live_checkbox.isChecked():
            self._live_timer.start()  # restarts if already running

    # ---------------------------------------------------------------------------
    # Group-by list refresh
    # ---------------------------------------------------------------------------

    def _refresh_groupby_list(self) -> None:
        """Repopulate the group-by list from currently selected columns."""
        available: list[tuple[str, str]] = []
        b = self.view.builder

        for i in range(b.columns_list.count()):
            item = b.columns_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                col = item.data(Qt.ItemDataRole.UserRole)
                label = _COL_LABEL.get(col, col)
                available.append((col, label))

        for i in range(b.derived_list.count()):
            item = b.derived_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                col = item.data(Qt.ItemDataRole.UserRole)
                label = _DERIVED_LABEL.get(col, col)
                available.append((col, label))

        b.refresh_groupby_list(available)

    # ---------------------------------------------------------------------------
    # Filter and aggregation row management
    # ---------------------------------------------------------------------------

    def _add_filter_row(self) -> FilterRowWidget:
        row = self.view.builder.add_filter_row()
        row.removed.connect(self._remove_filter_row)
        row.column_combo.currentIndexChanged.connect(self._on_change)
        row.operator_combo.currentIndexChanged.connect(self._on_change)
        row.value_edit.textChanged.connect(self._on_change)
        row.multi_select.selection_changed.connect(self._on_change)
        row.values_needed.connect(self._on_filter_values_needed)
        return row

    def _remove_filter_row(self, row: FilterRowWidget) -> None:
        self.view.builder.remove_filter_row(row)
        self._schedule_preview()

    def _add_agg_row(self) -> AggRowWidget:
        row = self.view.builder.add_agg_row()
        row.removed.connect(self._remove_agg_row)
        row.column_combo.currentIndexChanged.connect(self._on_change)
        row.function_combo.currentIndexChanged.connect(self._on_change)
        row.alias_edit.textChanged.connect(self._on_change)
        return row

    def _remove_agg_row(self, row: AggRowWidget) -> None:
        self.view.builder.remove_agg_row(row)
        self._schedule_preview()

    @pyqtSlot(object, str)
    def _on_filter_values_needed(self, row: FilterRowWidget, column: str) -> None:
        """Fetch distinct values for *column* and populate the filter row's multi-select.

        Runs a background worker so the UI stays responsive.
        """
        if self.project_path is None:
            return
        project_path = self.project_path

        def _fetch() -> list[str]:
            lf = bsp.db.FlatTransaction(project_path).all
            series = (
                lf.select(pl.col(column).cast(pl.String))
                .collect()[column]
                .drop_nulls()
                .unique()
                .sort()
            )
            return series.to_list()

        worker = _FetchWorker(_fetch)
        worker.signals.finished.connect(lambda values: row.set_distinct_values(values))
        worker.signals.error.connect(
            lambda msg: print(f"[run_reports] distinct-values fetch error: {msg}")
        )
        self.threadpool.start(worker)

    # ---------------------------------------------------------------------------
    # Query building
    # ---------------------------------------------------------------------------

    def _build_query(self) -> pl.LazyFrame | None:
        """Construct a polars LazyFrame from current builder state.

        Returns ``None`` if no project is loaded.
        """
        if self.project_path is None:
            return None

        b = self.view.builder

        # ── Base frame ────────────────────────────────────────────────
        lf: pl.LazyFrame = bsp.db.FlatTransaction(self.project_path).all

        # ── Parse transaction_date to Date type ───────────────────────
        # FlatTransaction.transaction_date is stored as TEXT "YYYY-MM-DD"
        lf = lf.with_columns(pl.col("transaction_date").str.to_date("%Y-%m-%d"))

        # ── Date range filter ─────────────────────────────────────────
        if b.date_range_enabled.isChecked():
            from_date = b.from_date.date().toPyDate()
            to_date = b.to_date.date().toPyDate()
            lf = lf.filter(
                (pl.col("transaction_date") >= pl.lit(from_date))
                & (pl.col("transaction_date") <= pl.lit(to_date))
            )

        # ── Derived date columns ──────────────────────────────────────
        checked_derived: list[str] = []
        for i in range(b.derived_list.count()):
            item = b.derived_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                col = item.data(Qt.ItemDataRole.UserRole)
                checked_derived.append(col)

        if checked_derived:
            extractor_exprs = []
            for col in checked_derived:
                if col in _DERIVED_EXTRACTORS:
                    extractor_exprs.append(
                        _DERIVED_EXTRACTORS[col](pl.col("transaction_date"))
                    )
            if extractor_exprs:
                lf = lf.with_columns(extractor_exprs)

        # ── Filters ───────────────────────────────────────────────────
        for row in b.filter_rows():
            defn = row.get_definition()
            col = defn["column"]
            op = defn["operator"]
            val = defn["value"]
            if not col or not val:
                continue
            try:
                filter_expr = _build_filter_expr(col, op, val)
                lf = lf.filter(filter_expr)
            except Exception:
                # Skip malformed filter rather than crashing
                traceback.print_exc()

        # ── Aggregations / Group-by ───────────────────────────────────
        agg_defns = [row.get_definition() for row in b.agg_rows()]
        groupby_cols: list[str] = []
        for i in range(b.groupby_list.count()):
            item = b.groupby_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                groupby_cols.append(item.data(Qt.ItemDataRole.UserRole))

        if agg_defns and groupby_cols:
            agg_exprs = []
            for defn in agg_defns:
                col = defn["column"]
                fn = defn["function"]
                alias = defn.get("alias") or f"{fn}_{col}"
                if not col:
                    continue
                try:
                    agg_exprs.append(_build_agg_expr(col, fn, alias))
                except Exception:
                    traceback.print_exc()
            if agg_exprs:
                lf = lf.group_by(groupby_cols).agg(agg_exprs)
        else:
            # ── Plain column selection ────────────────────────────────
            selected_cols: list[str] = []
            for i in range(b.columns_list.count()):
                item = b.columns_list.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    selected_cols.append(item.data(Qt.ItemDataRole.UserRole))
            selected_cols.extend(checked_derived)
            if selected_cols:
                # Only select columns that actually exist in the frame
                # (derived columns are added in with_columns above)
                lf = lf.select(selected_cols)

        return lf

    # ---------------------------------------------------------------------------
    # Preview execution
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _run_preview(self) -> None:
        """Build and execute the query, render result via StanPolarsModel."""
        if self.project_path is None:
            self.view.preview.set_error("No project is currently loaded.")
            return
        if self._query_running:
            # Queue another run after current one finishes
            self._live_timer.start(300)
            return

        lf = self._build_query()
        if lf is None:
            return

        self._query_running = True

        def _execute() -> pl.DataFrame:
            return lf.collect()

        worker = _ReportWorker(_execute)
        worker.signals.finished.connect(self._on_query_finished)
        worker.signals.error.connect(self._on_query_error)
        self.threadpool.start(worker)

    @pyqtSlot(object, int)
    def _on_query_finished(self, df: pl.DataFrame, row_count: int) -> None:
        self._query_running = False
        self.view.preview.set_dataframe(df, self._read_title(), self._read_subtitle())
        self.view.preview.set_row_count(row_count)

    @pyqtSlot(str)
    def _on_query_error(self, message: str) -> None:
        self._query_running = False
        self.view.preview.set_error(message)
        self.view.preview.set_row_count(None)

    # ---------------------------------------------------------------------------
    # Read builder state
    # ---------------------------------------------------------------------------

    def _read_title(self) -> str:
        return self.view.builder.title_edit.text().strip()

    def _read_subtitle(self) -> str:
        return self.view.builder.subtitle_edit.text().strip()

    def _read_definition(self) -> dict[str, Any]:
        """Serialise the current builder state to a report definition dict."""
        b = self.view.builder

        # Selected columns
        selected_columns: list[str] = []
        for i in range(b.columns_list.count()):
            item = b.columns_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_columns.append(item.data(Qt.ItemDataRole.UserRole))

        # Derived date columns
        derived_date_columns: list[str] = []
        for i in range(b.derived_list.count()):
            item = b.derived_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                derived_date_columns.append(item.data(Qt.ItemDataRole.UserRole))

        # Filters
        filters = [row.get_definition() for row in b.filter_rows()]

        # Group by
        group_by: list[str] = []
        for i in range(b.groupby_list.count()):
            item = b.groupby_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                group_by.append(item.data(Qt.ItemDataRole.UserRole))

        # Aggregations
        aggregations = [row.get_definition() for row in b.agg_rows()]

        # Date range
        date_range: dict[str, Any] = {
            "enabled": b.date_range_enabled.isChecked(),
            "from": b.from_date.date().toPyDate().isoformat(),
            "to": b.to_date.date().toPyDate().isoformat(),
        }

        return {
            "meta": {
                "title": self._read_title(),
                "subtitle": self._read_subtitle(),
            },
            "query": {
                "columns": selected_columns,
                "derived_date_columns": derived_date_columns,
                "filters": filters,
                "group_by": group_by,
                "aggregations": aggregations,
                "date_range": date_range,
            },
        }

    # ---------------------------------------------------------------------------
    # Write builder state
    # ---------------------------------------------------------------------------

    def _apply_definition(self, defn: dict[str, Any]) -> None:
        """Populate all builder controls from a loaded report definition."""
        b = self.view.builder

        # Meta
        meta = defn.get("meta", {})
        b.title_edit.blockSignals(True)
        b.title_edit.setText(meta.get("title", ""))
        b.title_edit.blockSignals(False)
        b.subtitle_edit.blockSignals(True)
        b.subtitle_edit.setText(meta.get("subtitle", ""))
        b.subtitle_edit.blockSignals(False)

        query = defn.get("query", {})

        # Columns
        selected_columns: list[str] = query.get("columns", [])
        b.columns_list.blockSignals(True)
        for i in range(b.columns_list.count()):
            item = b.columns_list.item(i)
            if item:
                col = item.data(Qt.ItemDataRole.UserRole)
                state = (
                    Qt.CheckState.Checked
                    if (not selected_columns or col in selected_columns)
                    else Qt.CheckState.Unchecked
                )
                item.setCheckState(state)
        b.columns_list.blockSignals(False)

        # Derived date columns
        derived: list[str] = query.get("derived_date_columns", [])
        b.derived_list.blockSignals(True)
        for i in range(b.derived_list.count()):
            item = b.derived_list.item(i)
            if item:
                col = item.data(Qt.ItemDataRole.UserRole)
                item.setCheckState(
                    Qt.CheckState.Checked if col in derived else Qt.CheckState.Unchecked
                )
        b.derived_list.blockSignals(False)

        # Sync tristate checkboxes
        self._update_all_checkboxes()

        # Rebuild group-by list before setting its state
        self._refresh_groupby_list()

        # Filters — clear existing and re-add
        for row in b.filter_rows()[:]:
            b.remove_filter_row(row)
        for f_defn in query.get("filters", []):
            row = self._add_filter_row()
            row.set_definition(f_defn)

        # Group by
        group_by: list[str] = query.get("group_by", [])
        b.groupby_list.blockSignals(True)
        for i in range(b.groupby_list.count()):
            item = b.groupby_list.item(i)
            if item:
                col = item.data(Qt.ItemDataRole.UserRole)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if col in group_by
                    else Qt.CheckState.Unchecked
                )
        b.groupby_list.blockSignals(False)

        # Aggregations — clear and re-add
        for row in b.agg_rows()[:]:
            b.remove_agg_row(row)
        for a_defn in query.get("aggregations", []):
            row = self._add_agg_row()
            row.set_definition(a_defn)

        # Date range
        dr = query.get("date_range", {})
        enabled = bool(dr.get("enabled", False))
        b.date_range_enabled.blockSignals(True)
        b.date_range_enabled.setChecked(enabled)
        b.date_range_enabled.blockSignals(False)
        b.from_date.setEnabled(enabled)
        b.to_date.setEnabled(enabled)
        if "from" in dr:
            try:
                d = _date.fromisoformat(str(dr["from"]))
                b.from_date.blockSignals(True)
                b.from_date.setDate(QDate(d.year, d.month, d.day))
                b.from_date.blockSignals(False)
            except ValueError:
                pass
        if "to" in dr:
            try:
                d = _date.fromisoformat(str(dr["to"]))
                b.to_date.blockSignals(True)
                b.to_date.setDate(QDate(d.year, d.month, d.day))
                b.to_date.blockSignals(False)
            except ValueError:
                pass

    # ---------------------------------------------------------------------------
    # Save / load / delete / new
    # ---------------------------------------------------------------------------

    @pyqtSlot()
    def _save_report(self) -> None:
        if self.project_path is None:
            self._error_dialog.showMessage(
                "No project is currently loaded. Cannot save a report."
            )
            return
        title = self._read_title()
        if not title:
            self._error_dialog.showMessage("Please enter a report title before saving.")
            return
        defn = self._read_definition()
        filename = _slugify(title)
        ok, path, msg = self.model.save_report(self.project_path, filename, defn)
        if ok:
            self._current_report_path = path
            # Refresh combo and select the just-saved report
            self._refresh_saved_reports_combo()
            self._select_combo_by_path(path)
        else:
            self._error_dialog.showMessage(msg)

    @pyqtSlot()
    def _load_selected_report(self) -> None:
        combo = self.view.builder.saved_reports_combo
        path: Path | None = combo.currentData(Qt.ItemDataRole.UserRole)
        if path is None:
            return
        ok, defn, msg = self.model.load_report(path)
        if ok:
            self._current_report_path = path
            self._apply_definition(defn)
            self.view.builder.set_builder_visible(True)
            self._run_preview()
        else:
            self._error_dialog.showMessage(msg)

    @pyqtSlot()
    def _delete_selected_report(self) -> None:
        combo = self.view.builder.saved_reports_combo
        path: Path | None = combo.currentData(Qt.ItemDataRole.UserRole)
        if path is None:
            return
        dlg = StanInfoMessage(self.view)
        dlg.setText(f"Delete report '{combo.currentText()}'?")
        dlg.setStandardButtons(
            StanInfoMessage.StandardButton.Yes | StanInfoMessage.StandardButton.Cancel
        )
        dlg.setDefaultButton(StanInfoMessage.StandardButton.Cancel)
        if dlg.exec() != StanInfoMessage.StandardButton.Yes:
            return
        ok, _, msg = self.model.delete_report(path)
        if not ok:
            self._error_dialog.showMessage(msg)
        else:
            if self._current_report_path == path:
                self._current_report_path = None

    @pyqtSlot()
    def _new_report(self) -> None:
        """Clear the builder for a fresh report."""
        self._current_report_path = None
        self._clear_builder()
        self.view.builder.set_builder_visible(True)

    # ---------------------------------------------------------------------------
    # Saved-reports combo helpers
    # ---------------------------------------------------------------------------

    def _refresh_saved_reports_combo(self) -> None:
        """Reload the saved-reports combo from disk."""
        if self.project_path is None:
            self.view.builder.saved_reports_combo.clear()
            return
        combo = self.view.builder.saved_reports_combo
        combo.blockSignals(True)
        combo.clear()
        for name, path in self.model.list_reports(self.project_path):
            combo.addItem(name, path)
        combo.blockSignals(False)

    def _select_combo_by_path(self, path: Path) -> None:
        combo = self.view.builder.saved_reports_combo
        for i in range(combo.count()):
            if combo.itemData(i, Qt.ItemDataRole.UserRole) == path:
                combo.setCurrentIndex(i)
                return

    # ---------------------------------------------------------------------------
    # Builder reset
    # ---------------------------------------------------------------------------

    def _clear_builder(self) -> None:
        """Reset all builder controls to defaults."""
        b = self.view.builder

        b.title_edit.blockSignals(True)
        b.title_edit.clear()
        b.title_edit.blockSignals(False)

        b.subtitle_edit.blockSignals(True)
        b.subtitle_edit.clear()
        b.subtitle_edit.blockSignals(False)

        # Check all columns by default
        b.columns_list.blockSignals(True)
        for i in range(b.columns_list.count()):
            item = b.columns_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        b.columns_list.blockSignals(False)

        # Uncheck all derived columns
        b.derived_list.blockSignals(True)
        for i in range(b.derived_list.count()):
            item = b.derived_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        b.derived_list.blockSignals(False)

        # Sync tristate checkboxes
        self._update_all_checkboxes()

        # Remove all filter rows
        for row in b.filter_rows()[:]:
            b.remove_filter_row(row)

        # Refresh group-by then uncheck all
        self._refresh_groupby_list()
        b.groupby_list.blockSignals(True)
        for i in range(b.groupby_list.count()):
            item = b.groupby_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        b.groupby_list.blockSignals(False)

        # Remove all agg rows
        for row in b.agg_rows()[:]:
            b.remove_agg_row(row)

        # Reset date range
        b.date_range_enabled.blockSignals(True)
        b.date_range_enabled.setChecked(False)
        b.date_range_enabled.blockSignals(False)
        b.from_date.setEnabled(False)
        b.to_date.setEnabled(False)

        self.view.preview.clear()
        self.view.preview.set_row_count(None)


# ---------------------------------------------------------------------------
# Polars expression builders
# ---------------------------------------------------------------------------

# Columns that hold numeric values and should be compared as numbers
_NUMERIC_FILTER_COLS: frozenset[str] = frozenset(
    {"value_in", "value_out", "value", "transaction_number", "opening_balance"}
)


def _build_filter_expr(col: str, op: str, val: str) -> pl.Expr:
    """Build a polars filter expression from operator string and raw value.

    String column comparisons are case-insensitive (both sides lowercased).
    """
    c = pl.col(col)
    is_str_col = col not in _NUMERIC_FILTER_COLS

    if op == "eq":
        coerced = _coerce(col, val)
        if is_str_col and isinstance(coerced, str):
            return c.cast(pl.String).str.to_lowercase() == coerced.lower()
        return c == coerced
    elif op == "ne":
        coerced = _coerce(col, val)
        if is_str_col and isinstance(coerced, str):
            return c.cast(pl.String).str.to_lowercase() != coerced.lower()
        return c != coerced
    elif op == "gt":
        return c > _coerce(col, val)
    elif op == "lt":
        return c < _coerce(col, val)
    elif op == "ge":
        return c >= _coerce(col, val)
    elif op == "le":
        return c <= _coerce(col, val)
    elif op == "contains":
        return (
            c.cast(pl.String).str.to_lowercase().str.contains(val.lower(), literal=True)
        )
    elif op in ("is_in", "not_in"):
        # Value may be a list (from MultiSelectWidget) or a legacy comma string
        if isinstance(val, list):
            items = [str(v) for v in val]
        else:
            items = [v.strip() for v in str(val).split(",") if v.strip()]
        if is_str_col:
            items_lower = [v.lower() for v in items]
            expr = c.cast(pl.String).str.to_lowercase().is_in(items_lower)
        else:
            expr = c.cast(pl.String).is_in(items)
        return ~expr if op == "not_in" else expr
    else:
        raise ValueError(f"Unknown operator: {op!r}")


def _coerce(col: str, val: str) -> Any:
    """Try to coerce a string value to a numeric type for numeric-looking columns.

    Falls back to the raw string if conversion fails.
    """
    if col in _NUMERIC_FILTER_COLS:
        try:
            return float(val)
        except ValueError:
            pass
    return val


def _build_agg_expr(col: str, fn: str, alias: str) -> pl.Expr:
    """Build a polars aggregation expression."""
    c = pl.col(col)
    if fn == "sum":
        return c.sum().alias(alias)
    elif fn == "mean":
        return c.mean().alias(alias)
    elif fn == "min":
        return c.min().alias(alias)
    elif fn == "max":
        return c.max().alias(alias)
    elif fn == "count":
        return c.count().alias(alias)
    else:
        raise ValueError(f"Unknown aggregation function: {fn!r}")
