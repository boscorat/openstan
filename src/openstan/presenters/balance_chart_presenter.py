"""Balance chart presenter — worker + presenter for the balance chart panel.

Data flow
---------
1. ``BalanceChartWorker`` (background ``QRunnable``):
   - Reads ``FactBalance`` (filter ``outside_date == 0``) and ``DimAccount``
     via the ``bsp.db`` API (Polars LazyFrames).
   - Joins on ``account_id``, aggregates to month-end ``closing_balance`` per
     ``(company, id_account)`` combination.
   - Emits a Polars ``DataFrame`` via ``BalanceChartSignals.data_ready``.
   # TODO: move to bsp — the FactBalance/DimAccount join and month-end
   # aggregation should be a named query in bank_statement_parser once that
   # package exposes it.  Until then this shim lives here (see D001).

2. ``BalanceAccountModel`` (``QAbstractItemModel``):
   - Provides a two-level tree: company nodes → account leaf nodes.
   - Used by ``BalanceChartView.account_tree`` (StanTreeView).

3. ``BalanceChartPresenter``:
   - Receives the DataFrame, builds ``BalanceAccountModel``, creates
     ``QChart`` / ``QChartView`` widgets, wires axis synchronisation and
     tree-click highlighting, pushes them into ``BalanceChartView``.
"""

from __future__ import annotations

import sqlite3
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

import bank_statement_parser as bsp
import polars as pl
from PyQt6.QtCharts import (
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PyQt6.QtCore import (
    QAbstractItemModel,
    QMargins,
    QModelIndex,
    QObject,
    QRunnable,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QPen, QResizeEvent

if TYPE_CHECKING:
    from openstan.views.balance_chart_view import BalanceChartView


# ---------------------------------------------------------------------------
# Palette — distinct colours for up to 12 series (wraps if more)
# ---------------------------------------------------------------------------
_SERIES_COLOURS: list[str] = [
    "#1f77b4",  # muted blue
    "#ff7f0e",  # safety orange
    "#2ca02c",  # cooked asparagus green
    "#d62728",  # brick red
    "#9467bd",  # muted purple
    "#8c564b",  # chestnut brown
    "#e377c2",  # raspberry yoghurt pink
    "#7f7f7f",  # middle gray
    "#bcbd22",  # curry yellow-green
    "#17becf",  # blue-teal
    "#aec7e8",  # light blue
    "#ffbb78",  # light orange
]


def _colour(index: int) -> QColor:
    return QColor(_SERIES_COLOURS[index % len(_SERIES_COLOURS)])


# ---------------------------------------------------------------------------
# Responsive chart view — adjusts x-axis tick count on resize
# ---------------------------------------------------------------------------

#: Approximate pixel width of one "MMM yyyy" label (at standard font size).
_X_LABEL_PX: int = 70
_X_TICK_MIN: int = 2
_X_TICK_MAX: int = 24


class _ResponsiveChartView(QChartView):
    """``QChartView`` subclass that keeps x-axis tick density legible on resize.

    When the widget is resized the tick count is recalculated as
    ``clamp(floor(width / _X_LABEL_PX), _X_TICK_MIN, _X_TICK_MAX)`` so labels
    never overlap and the axis is not excessively sparse on wide displays.

    The view stores a reference to the ``QDateTimeAxis`` it manages; pass it
    after construction via ``set_x_axis()``.
    """

    def __init__(self, chart: QChart) -> None:
        super().__init__(chart)
        self._x_axis: QDateTimeAxis | None = None

    def set_x_axis(self, axis: QDateTimeAxis) -> None:
        """Register the axis whose tick count this view manages."""
        self._x_axis = axis

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._x_axis is not None:
            width = event.size().width()
            ticks = max(_X_TICK_MIN, min(_X_TICK_MAX, width // _X_LABEL_PX))
            self._x_axis.setTickCount(ticks)


# ---------------------------------------------------------------------------
# Background worker signals
# ---------------------------------------------------------------------------


class BalanceChartSignals(QObject):
    """Cross-thread signals for BalanceChartWorker."""

    # (project_path, DataFrame) — columns: company, id_account, year_month, closing_balance
    # year_month is a QDateTime-compatible millisecond timestamp (int64)
    data_ready: pyqtSignal = pyqtSignal(Path, object)  # object = pl.DataFrame | None


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class BalanceChartWorker(QRunnable):
    """Background worker that queries FactBalance + DimAccount and emits month-end data.

    Emits ``None`` as the DataFrame when the mart is absent, empty, or on error.
    Any exception is printed to stderr so the UI is never left in a broken state.

    # TODO: move to bsp — the join and month-end aggregation below should
    # eventually be a named query in bank_statement_parser so that the CLI
    # and API can consume the same logic (D001).
    """

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self._project_path: Path = project_path
        self.signals: BalanceChartSignals = BalanceChartSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            # -- Raw data -------------------------------------------------
            # TODO: move to bsp
            fact_lf: pl.LazyFrame = (
                bsp.db.FactBalance(self._project_path)
                .all.filter(pl.col("outside_date") == 0)
                .select(["account_id", "id_date", "closing_balance"])
            )
            dim_lf: pl.LazyFrame = bsp.db.DimAccount(self._project_path).all.select(
                [
                    "account_id",
                    "id_account",
                    "company",
                    "account_type",
                    "account_holder",
                ]
            )

            # -- Join and collect -----------------------------------------
            # TODO: move to bsp
            joined: pl.DataFrame = (
                fact_lf.join(dim_lf, on="account_id", how="left")
                .with_columns(
                    # Parse ISO date string → Date, then extract year/month
                    pl.col("id_date").str.to_date("%Y-%m-%d").alias("date"),
                )
                .with_columns(
                    pl.col("date").dt.year().alias("year"),
                    pl.col("date").dt.month().alias("month"),
                    pl.col("date").alias("sort_date"),
                )
                .collect()
            )

            if joined.is_empty():
                self.signals.data_ready.emit(self._project_path, None)
                return

            # -- Coalesce NULL dimension strings --------------------------
            # DimAccount rows with a NULL company, account_type, or
            # account_holder would produce Python "None" in labels.
            # TODO: move to bsp — ideally these coalesces live in the
            # DimAccount query so every consumer benefits.
            joined = joined.with_columns(
                pl.col("company").fill_null("(unknown)"),
                pl.col("account_type").fill_null("(unknown)"),
                pl.col("account_holder").fill_null("(unknown)"),
            )

            # -- Build display_label: account_type, suffixed with
            #    account_holder only when a company/account_type pair has
            #    more than one distinct holder (e.g. two credit cards).
            # TODO: move to bsp
            holder_counts: pl.DataFrame = (
                joined.select(["company", "account_type", "account_holder"])
                .unique()
                .group_by(["company", "account_type"])
                .agg(pl.col("account_holder").n_unique().alias("n_holders"))
            )
            joined = joined.join(
                holder_counts, on=["company", "account_type"], how="left"
            )
            joined = joined.with_columns(
                pl.when(pl.col("n_holders") > 1)
                .then(pl.col("account_type") + " (" + pl.col("account_holder") + ")")
                .otherwise(pl.col("account_type"))
                .alias("display_label")
            )

            # -- Month-end aggregation ------------------------------------
            # For each (company, display_label, year, month) take the row
            # with the latest sort_date — that is the month-end closing
            # balance.  When the same account_type spans multiple
            # account_numbers (e.g. re-issued card), we sum the closing
            # balances within the label group so they collapse into one
            # series.
            # TODO: move to bsp
            month_end: pl.DataFrame = (
                joined.sort("sort_date")
                .group_by(["company", "display_label", "year", "month"])
                .agg(
                    pl.col("closing_balance").last().alias("closing_balance"),
                    pl.col("sort_date").last().alias("period_end_date"),
                )
                .sort(["company", "display_label", "year", "month"])
            )

            # Convert period_end_date (polars Date) to milliseconds since epoch
            # so QDateTime can consume it directly.
            month_end = month_end.with_columns(
                (pl.col("period_end_date").cast(pl.Int64) * 86_400_000).alias(
                    "epoch_ms"
                )
            )

            self.signals.data_ready.emit(self._project_path, month_end)

        except sqlite3.OperationalError, bsp.StatementError:
            # Mart tables not yet built or project.db missing — emit None.
            self.signals.data_ready.emit(self._project_path, None)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.signals.data_ready.emit(self._project_path, None)


# ---------------------------------------------------------------------------
# Account tree model
# ---------------------------------------------------------------------------


class _AccountNode:
    """Internal node for BalanceAccountModel."""

    __slots__ = ("label", "parent", "children", "account_key", "company")

    def __init__(
        self,
        label: str,
        parent: "_AccountNode | None" = None,
        account_key: str | None = None,
        company: str | None = None,
    ) -> None:
        self.label: str = label
        self.parent: "_AccountNode | None" = parent
        self.children: list["_AccountNode"] = []
        self.account_key: str | None = account_key  # None for company nodes
        self.company: str | None = company  # set on both company and account nodes


class BalanceAccountModel(QAbstractItemModel):
    """Two-level tree model: company → account.

    Used by ``BalanceChartView.account_tree``.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root: _AccountNode = _AccountNode("root")

    def load(self, df: pl.DataFrame) -> None:
        """Populate the model from a month-end DataFrame.

        Args:
            df: Must contain at least ``company`` and ``display_label`` columns.
                An empty or schema-less DataFrame clears the tree.
        """
        self.beginResetModel()
        self._root.children.clear()

        if df.is_empty() or "company" not in df.columns:
            self.endResetModel()
            return

        companies: list[str] = (
            df.select("company")
            .unique()
            .sort("company")
            .get_column("company")
            .to_list()
        )
        for company in companies:
            company_node = _AccountNode(
                label=company or "(unknown)", parent=self._root, company=company
            )
            accounts: list[str] = (
                df.filter(pl.col("company") == company)
                .select("display_label")
                .unique()
                .sort("display_label")
                .get_column("display_label")
                .to_list()
            )
            for acc in accounts:
                acc_node = _AccountNode(
                    label=acc,
                    parent=company_node,
                    account_key=acc,
                    company=company,
                )
                company_node.children.append(acc_node)
            self._root.children.append(company_node)

        self.endResetModel()

    # ------------------------------------------------------------------
    # QAbstractItemModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        node = self._node(parent)
        return len(node.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._node(index).label
        return None

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = self._node(parent)
        child = parent_node.children[row]
        return self.createIndex(row, column, child)

    def parent(self, index: QModelIndex) -> QModelIndex:  # type: ignore[override]
        if not index.isValid():
            return QModelIndex()
        child_node: _AccountNode = index.internalPointer()  # type: ignore[assignment]
        parent_node = child_node.parent
        if parent_node is None or parent_node is self._root:
            return QModelIndex()
        grandparent = parent_node.parent
        if grandparent is None:
            return QModelIndex()
        row = grandparent.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and section == 0
        ):
            return "Account"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def _node(self, index: QModelIndex) -> _AccountNode:
        if index.isValid():
            return index.internalPointer()  # type: ignore[return-value]
        return self._root


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


class BalanceChartPresenter(QObject):
    """Manages the balance chart panel.

    Signals:
        exit_chart: Emitted when the user presses "← Back".
        has_data_changed: Emitted (bool) when the availability of balance data
            changes, so ``StanPresenter`` can enable/disable ``button_balance``.
    """

    exit_chart: pyqtSignal = pyqtSignal()
    has_data_changed: pyqtSignal = pyqtSignal(bool)

    def __init__(
        self,
        view: "BalanceChartView",
        threadpool: Any,
    ) -> None:
        super().__init__()
        self._view: "BalanceChartView" = view
        self._threadpool = threadpool
        self._project_path: Path | None = None
        self._project_name: str = "Account Balances"
        self._df: pl.DataFrame | None = None
        self._account_model: BalanceAccountModel = BalanceAccountModel(self)

        # Map from display_label → list of QLineSeries (multiple segments
        # per account when there are month-gaps).
        self._series_map: dict[str, list[QLineSeries]] = {}

        # Store base pen (colour + width 2) per display_label so we can
        # always reset to exactly two states: normal (2px) or selected (4px).
        self._base_pens: dict[str, QPen] = {}

        # Map company name → sorted list of display_labels for that company.
        # Used to highlight all series when a company node is clicked.
        self._company_labels: dict[str, list[str]] = {}

        # Key that is currently highlighted.
        #   - A display_label string means a leaf account is selected.
        #   - A "__company:<name>" string means a company node is selected.
        #   - None means nothing is highlighted.
        self._selected_key: str | None = None

        # Wire view signals
        self._view.back_button.clicked.connect(self._on_back)
        self._view.account_tree.setModel(self._account_model)
        self._reconnect_tree_selection()

    # ------------------------------------------------------------------
    # Public interface — called by StanPresenter
    # ------------------------------------------------------------------

    @property
    def project_path(self) -> Path | None:
        return self._project_path

    @project_path.setter
    def project_path(self, value: Path | None) -> None:
        self._project_path = value

    @property
    def project_name(self) -> str:
        return self._project_name

    @project_name.setter
    def project_name(self, value: str) -> None:
        self._project_name = value if value else "Account Balances"

    def refresh(self, *, probe: bool = False) -> None:
        """Start a background worker to fetch / re-fetch balance data.

        Args:
            probe: When ``True`` the worker runs silently — no status text or
                chart-clear side effects.  Use this when the panel is hidden
                and the goal is only to determine whether data exists so that
                ``button_balance`` can be enabled/disabled correctly.
        """
        if self._project_path is None:
            self._clear_and_notify(has_data=False, status="No project selected.")
            return
        if not probe:
            self._view.set_status("Loading balance data...")
            self._view.clear_charts()
        worker = BalanceChartWorker(self._project_path)
        worker.signals.data_ready.connect(self._on_data_ready)
        self._threadpool.start(worker)

    def clear_for_project_change(self) -> None:
        """Reset state when the selected project changes."""
        self._df = None
        self._series_map.clear()
        self._base_pens.clear()
        self._company_labels.clear()
        self._selected_key = None
        self._account_model.load(pl.DataFrame())
        self._view.clear_charts()
        self._view.set_status("No balance data available for this project.")
        self.has_data_changed.emit(False)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _reconnect_tree_selection(self) -> None:
        """(Re-)connect the tree's selection model to ``_on_tree_selection_changed``.

        ``QAbstractItemView.selectionModel()`` returns a *new* object after
        ``setModel()`` or ``beginResetModel()``/``endResetModel()``, so we
        must call this after every ``BalanceAccountModel.load()`` to keep
        the highlight logic alive.
        """
        selection_model = self._view.account_tree.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self._on_tree_selection_changed)

    @pyqtSlot()
    def _on_back(self) -> None:
        self.exit_chart.emit()

    @pyqtSlot(Path, object)
    def _on_data_ready(self, project_path: Path, df: object) -> None:
        """Receive month-end balance data from the background worker."""
        # Discard stale result if the project has changed since launch
        if self._project_path is None or project_path != self._project_path:
            return

        if df is None or not isinstance(df, pl.DataFrame) or df.is_empty():
            self._clear_and_notify(has_data=False)
            return

        self._df = df
        self._build_charts(df)
        self.has_data_changed.emit(True)

    def _clear_and_notify(
        self,
        has_data: bool,
        status: str = "No balance data available for this project.",
    ) -> None:
        self._view.clear_charts()
        self._view.set_status(status)
        self.has_data_changed.emit(has_data)

    # ------------------------------------------------------------------
    # Chart construction
    # ------------------------------------------------------------------

    def _build_charts(self, df: pl.DataFrame) -> None:
        """Build a single QChartView with all accounts on one shared axis.

        Each ``display_label`` gets one or more ``QLineSeries`` segments so
        that months without data produce a visible gap rather than an
        interpolated line.  A "Net total" dashed series is added when there
        are two or more accounts.
        """
        self._view.clear_charts()
        self._series_map.clear()
        self._base_pens.clear()
        self._company_labels.clear()
        self._selected_key = None

        # Populate account tree
        self._account_model.load(df)
        self._reconnect_tree_selection()
        self._view.account_tree.expandAll()

        # Build the complete set of month-end epoch values across ALL
        # accounts so we can detect per-account gaps.
        all_epochs: list[int] = sorted(
            df.select("epoch_ms").unique().get_column("epoch_ms").to_list()
        )

        # Gather all unique display_labels in stable order (by company, then label)
        label_company_pairs: list[tuple[str, str]] = (
            df.select(["company", "display_label"])
            .unique()
            .sort(["company", "display_label"])
            .rows()
        )
        labels: list[str] = [lbl for _, lbl in label_company_pairs]

        # Build company → [display_labels] map for company-node highlight
        for company, lbl in label_company_pairs:
            self._company_labels.setdefault(company, []).append(lbl)

        chart = QChart()
        chart.setTitle(self._project_name)
        chart.setMargins(QMargins(8, 8, 8, 8))
        legend = chart.legend()
        if legend is not None:
            legend.setVisible(True)

        all_chart_series: list[QLineSeries] = []
        net: dict[int, float] = {}  # epoch_ms → running net total

        for colour_index, label in enumerate(labels):
            label_df = df.filter(pl.col("display_label") == label).sort("epoch_ms")
            colour = _colour(colour_index)
            base_pen = QPen(colour)
            base_pen.setWidth(2)
            self._base_pens[label] = QPen(base_pen)  # store a copy

            # Build per-label epoch→value mapping
            epoch_to_val: dict[int, float] = {
                int(row["epoch_ms"]): float(row["closing_balance"])
                for row in label_df.iter_rows(named=True)
            }

            # Accumulate into net total
            for e, v in epoch_to_val.items():
                net[e] = net.get(e, 0.0) + v

            # Split into contiguous segments — a new segment starts whenever
            # consecutive months in all_epochs are missing for this account.
            segments = self._split_into_segments(all_epochs, epoch_to_val)

            first_segment = True
            for segment in segments:
                series = QLineSeries()
                # Only the first segment carries the legend name to avoid
                # duplicate legend entries.
                if first_segment:
                    series.setName(label)
                    first_segment = False
                series.setPen(QPen(base_pen))
                for epoch, value in segment:
                    series.append(epoch, value)
                chart.addSeries(series)
                all_chart_series.append(series)
                self._series_map.setdefault(label, []).append(series)

        # Net total series — bold black dashed line
        if len(labels) > 1:
            net_pen = QPen(QColor("#000000"))
            net_pen.setWidth(3)
            net_pen.setStyle(Qt.PenStyle.DashLine)
            self._base_pens["__net_total__"] = QPen(net_pen)

            net_series = QLineSeries()
            net_series.setName("Net total")
            net_series.setPen(QPen(net_pen))
            for epoch in sorted(net):
                net_series.append(epoch, net[epoch])
            chart.addSeries(net_series)
            all_chart_series.append(net_series)
            self._series_map.setdefault("__net_total__", []).append(net_series)

        # Axes
        x_axis = QDateTimeAxis()
        x_axis.setFormat("MMM yyyy")
        x_axis.setTitleText("")
        # Tick count starts at the Qt default (7); _ResponsiveChartView
        # recalculates it dynamically on every resize event.
        y_axis = QValueAxis()
        y_axis.setLabelFormat("£%.0f")
        y_axis.setTickCount(11)  # ~doubled from Qt default of 5

        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        for s in all_chart_series:
            s.attachAxis(x_axis)
            s.attachAxis(y_axis)

        # -- Explicit y-axis range ----------------------------------------
        # Qt auto-range is calculated per-series in insertion order and ends
        # up honouring only the first series.  Compute the true min/max
        # across every value (accounts + net total) and add 5 % padding.
        all_values: list[float] = df.get_column("closing_balance").to_list()
        if net:
            all_values.extend(net.values())
        raw_min = min(all_values)
        raw_max = max(all_values)
        span = raw_max - raw_min if raw_max != raw_min else 1.0
        padding = span * 0.05
        y_min = raw_min - padding
        y_max = raw_max + padding
        y_axis.setRange(y_min, y_max)

        # -- Zero reference line ------------------------------------------
        # Draw a thin solid grey line at y = 0 so it is always visible
        # regardless of the current pan/zoom.  The series is not added to
        # _series_map so it is never affected by highlight logic.
        if y_min < 0 < y_max:
            zero_series = QLineSeries()
            zero_pen = QPen(QColor("#888888"))
            zero_pen.setWidth(1)
            zero_series.setPen(zero_pen)
            if all_epochs:
                zero_series.append(all_epochs[0], 0.0)
                zero_series.append(all_epochs[-1], 0.0)
            chart.addSeries(zero_series)
            zero_series.attachAxis(x_axis)
            zero_series.attachAxis(y_axis)

        # -- Clean up legend markers --------------------------------------
        # Qt creates one legend marker per QLineSeries.  Segment series
        # beyond the first have no name, and the zero line should also be
        # invisible.  Hide any marker whose label is empty.
        _legend = chart.legend()
        if _legend is not None:
            for marker in _legend.markers():
                if not marker.label():
                    marker.setVisible(False)

        chart_view = _ResponsiveChartView(chart)
        chart_view.set_x_axis(x_axis)
        chart_view.setMinimumHeight(800)
        chart_view.setRubberBand(QChartView.RubberBand.HorizontalRubberBand)
        self._view.add_chart_view(chart_view)

    @staticmethod
    def _split_into_segments(
        all_epochs: list[int],
        epoch_to_val: dict[int, float],
    ) -> list[list[tuple[int, float]]]:
        """Split an account's data points into contiguous segments.

        A new segment is started whenever there is one or more consecutive
        month in ``all_epochs`` that is absent from ``epoch_to_val``.  This
        produces visible line breaks for months with no data.
        """
        segments: list[list[tuple[int, float]]] = []
        current: list[tuple[int, float]] = []

        for epoch in all_epochs:
            if epoch in epoch_to_val:
                current.append((epoch, epoch_to_val[epoch]))
            else:
                if current:
                    segments.append(current)
                    current = []

        if current:
            segments.append(current)

        return segments

    # ------------------------------------------------------------------
    # Tree click → series highlight
    # ------------------------------------------------------------------

    @pyqtSlot(QModelIndex, QModelIndex)
    def _on_tree_selection_changed(
        self, current: QModelIndex, previous: QModelIndex
    ) -> None:
        """Highlight the selected account or company series and reset others.

        Behaviour:
        - Leaf account node → highlight that account's series (4 px); all
          others revert to base width.  Clicking the same leaf a second time
          clears the highlight (toggle off).
        - Company node → highlight all series belonging to that company (4 px);
          all others revert to base width.  Clicking the same company again
          clears the highlight.
        - Invalid index → clear all highlights.

        Every series is always set using the stored ``_base_pens`` — no alpha
        manipulation — so repeated clicks never cause cumulative drift.
        """
        selected_node = self._account_model._node(current)  # type: ignore[attr-defined]

        if not current.isValid():
            # Selection cleared externally — reset everything
            self._selected_key = None
            self._apply_highlight(selected_keys=set())
            return

        if selected_node.account_key is not None:
            # Leaf account node
            new_key = selected_node.account_key
            if self._selected_key == new_key:
                # Toggle off — deselect by clearing the tree selection
                self._selected_key = None
                self._view.account_tree.clearSelection()
                self._apply_highlight(selected_keys=set())
            else:
                self._selected_key = new_key
                self._apply_highlight(selected_keys={new_key})
        elif selected_node.company is not None:
            # Company node — highlight all accounts for that company
            company_key = f"__company:{selected_node.company}"
            if self._selected_key == company_key:
                # Toggle off
                self._selected_key = None
                self._view.account_tree.clearSelection()
                self._apply_highlight(selected_keys=set())
            else:
                self._selected_key = company_key
                keys = set(self._company_labels.get(selected_node.company, []))
                self._apply_highlight(selected_keys=keys)

    def _apply_highlight(self, selected_keys: set[str]) -> None:
        """Set all series pens: 4 px for keys in *selected_keys*, base for others.

        Args:
            selected_keys: Set of ``display_label`` strings to highlight.
                Pass an empty set to clear all highlights.
        """
        for acc_key, series_list in self._series_map.items():
            if acc_key == "__net_total__":
                # Net total is never highlighted — always stays at its base width
                base_pen = self._base_pens.get(acc_key)
                if base_pen is None:
                    continue
                for series in series_list:
                    series.setPen(QPen(base_pen))
                continue
            base_pen = self._base_pens.get(acc_key)
            if base_pen is None:
                continue
            for series in series_list:
                pen = QPen(base_pen)
                if selected_keys and acc_key in selected_keys:
                    pen.setWidth(4)
                series.setPen(pen)
